"""Process manager for MRTKLIB command execution with real-time log streaming."""

import asyncio
import signal
import uuid
from asyncio.subprocess import Process
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Awaitable

from mrtklib_web_ui.paths import MRTK_BIN, resolve_stream_url
from mrtklib_web_ui.services.mask_credentials import mask_log_line


class ProcessState(str, Enum):
    """Process execution state."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ProcessInfo:
    """Information about a managed process."""

    id: str
    command: str
    args: list[str]
    state: ProcessState = ProcessState.IDLE
    pid: int | None = None
    return_code: int | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    error_message: str | None = None


@dataclass
class ProcessManager:
    """Manages MRTKLIB subprocess execution with async log streaming.

    Handles starting, stopping, and monitoring of MRTKLIB processes.
    Maps legacy command names to mrtk subcommands.
    Broadcasts stderr output to connected WebSocket clients.
    """

    # Map legacy command names → mrtk subcommands
    SUBCOMMAND_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "str2str": "relay",
            "convbin": "convert",
            "rnx2rtkp": "post",
            "rtkrcv": "run",
            "cssr2rtcm3": "cssr2rtcm3",
        }
    )

    # Active processes
    _processes: dict[str, Process] = field(default_factory=dict)
    _process_info: dict[str, ProcessInfo] = field(default_factory=dict)

    # Log broadcast callback
    _log_callback: Callable[[str, str], Awaitable[None]] | None = None

    # Background tasks for log reading
    _log_tasks: dict[str, asyncio.Task] = field(default_factory=dict)

    def set_log_callback(
        self, callback: Callable[[str, str], Awaitable[None]]
    ) -> None:
        """Set callback for log broadcasting.

        Args:
            callback: Async function that receives (process_id, log_line)
        """
        self._log_callback = callback

    async def start(
        self,
        command: str,
        args: list[str] | None = None,
        process_id: str | None = None,
    ) -> ProcessInfo:
        """Start an MRTKLIB process.

        Args:
            command: Legacy command name (e.g., 'str2str') mapped to mrtk subcommand
            args: Command arguments
            process_id: Optional custom process ID

        Returns:
            ProcessInfo with process details

        Raises:
            ValueError: If command is not allowed or process already running
        """
        if command not in self.SUBCOMMAND_MAP:
            raise ValueError(f"Command not allowed: {command}")

        # Generate process ID if not provided
        proc_id = process_id or str(uuid.uuid4())[:8]

        # Check if process with same ID is already running
        if proc_id in self._processes:
            existing = self._process_info.get(proc_id)
            if existing and existing.state == ProcessState.RUNNING:
                raise ValueError(f"Process {proc_id} is already running")

        runtime_args = [resolve_stream_url(arg) for arg in (args or [])]

        # Create process info
        info = ProcessInfo(
            id=proc_id,
            command=command,
            args=runtime_args,
            state=ProcessState.STARTING,
            started_at=datetime.now(),
        )
        self._process_info[proc_id] = info

        try:
            # Map to mrtk subcommand
            subcommand = self.SUBCOMMAND_MAP[command]
            mrtk_path = str(MRTK_BIN)

            # Log the command being executed
            cmd_str = f"mrtk {subcommand} {' '.join(runtime_args)}"
            await self._broadcast_log(proc_id, f"[SYSTEM] Starting: {cmd_str}")

            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                mrtk_path,
                subcommand,
                *runtime_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )

            self._processes[proc_id] = process
            info.pid = process.pid
            info.state = ProcessState.RUNNING

            await self._broadcast_log(proc_id, f"[SYSTEM] Process started (PID: {process.pid})")

            # Start background task to read stderr
            self._log_tasks[proc_id] = asyncio.create_task(
                self._read_stderr(proc_id, process)
            )

            # Also read stdout in background
            asyncio.create_task(self._read_stdout(proc_id, process))

            return info

        except FileNotFoundError:
            info.state = ProcessState.ERROR
            info.error_message = f"Command not found: {command}"
            await self._broadcast_log(proc_id, f"[ERROR] {info.error_message}")
            raise ValueError(info.error_message)

        except Exception as e:
            info.state = ProcessState.ERROR
            info.error_message = str(e)
            await self._broadcast_log(proc_id, f"[ERROR] Failed to start: {e}")
            raise

    async def stop(self, process_id: str, timeout: float = 5.0) -> ProcessInfo:
        """Stop a running process.

        Args:
            process_id: ID of process to stop
            timeout: Seconds to wait for graceful termination

        Returns:
            Updated ProcessInfo
        """
        if process_id not in self._processes:
            raise ValueError(f"Process not found: {process_id}")

        process = self._processes[process_id]
        info = self._process_info[process_id]

        if process.returncode is not None:
            # Process already terminated
            info.state = ProcessState.STOPPED
            return info

        info.state = ProcessState.STOPPING
        await self._broadcast_log(process_id, "[SYSTEM] Stopping process...")

        try:
            # Send SIGTERM for graceful shutdown
            process.terminate()

            try:
                await asyncio.wait_for(process.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                # Force kill if not terminated
                await self._broadcast_log(
                    process_id, "[SYSTEM] Process did not terminate, killing..."
                )
                process.kill()
                await process.wait()

            info.return_code = process.returncode
            info.state = ProcessState.STOPPED
            info.stopped_at = datetime.now()

            await self._broadcast_log(
                process_id,
                f"[SYSTEM] Process stopped (exit code: {info.return_code})",
            )

        except ProcessLookupError:
            # Process already gone
            info.state = ProcessState.STOPPED

        finally:
            # Cancel log reading task
            if process_id in self._log_tasks:
                self._log_tasks[process_id].cancel()
                try:
                    await self._log_tasks[process_id]
                except asyncio.CancelledError:
                    pass
                del self._log_tasks[process_id]

            # Clean up process reference
            del self._processes[process_id]

        return info

    async def get_status(self, process_id: str) -> ProcessInfo | None:
        """Get process status.

        Args:
            process_id: ID of process to check

        Returns:
            ProcessInfo or None if not found
        """
        info = self._process_info.get(process_id)
        if not info:
            return None

        # Update state if process has terminated
        if process_id in self._processes:
            process = self._processes[process_id]
            if process.returncode is not None:
                info.state = ProcessState.STOPPED
                info.return_code = process.returncode
                info.stopped_at = datetime.now()

        return info

    def get_all_processes(self) -> list[ProcessInfo]:
        """Get all process infos."""
        return list(self._process_info.values())

    def peek_state(self, process_id: str) -> ProcessState:
        """Synchronous, lock-free read of a process's last-known state.

        Returns ProcessState.IDLE for unknown IDs. Use get_status() when
        you want the live subprocess return-code refresh; this helper is
        for callers that just need the cached state in a sync context.
        """
        info = self._process_info.get(process_id)
        return info.state if info else ProcessState.IDLE

    # Cap a single broadcast line at 8 KiB so a runaway upstream (e.g. a
    # cssr2rtcm3 dump or accidentally-printed binary buffer) cannot blow
    # up the WebSocket payload or the browser console. Beyond this we
    # truncate with a marker; the read loop itself keeps going.
    _MAX_BROADCAST_LINE = 8 * 1024
    # Hard cap on the partial-line buffer. If the upstream produces no
    # newline at all for this many bytes, we flush what we have as one
    # truncated line and reset, instead of growing without bound.
    _MAX_LINE_BUFFER = 1 * 1024 * 1024

    async def _read_stderr(self, process_id: str, process: Process) -> None:
        """Stream stderr to broadcast_log, line by line.

        Reads in chunks instead of asyncio.StreamReader.readline() so we
        do not crash with `Separator is not found, and chunk exceed the
        limit` when a single log line is longer than the default 64 KiB
        buffer (e.g. cssr2rtcm3's `=== End Dump ===` block can push past
        that). str2str / mrtk relay write their logs to stderr.
        """
        if process.stderr is None:
            return
        await self._pump_stream(process_id, process.stderr, prefix="")

    async def _read_stdout(self, process_id: str, process: Process) -> None:
        """Stream stdout to broadcast_log with an [OUT] prefix."""
        if process.stdout is None:
            return
        await self._pump_stream(process_id, process.stdout, prefix="[OUT] ")

    async def _pump_stream(
        self,
        process_id: str,
        stream: asyncio.StreamReader,
        prefix: str,
    ) -> None:
        """Chunk-based line splitter — survives lines of any length."""
        buf = bytearray()
        try:
            while True:
                chunk = await stream.read(8192)
                if not chunk:
                    if buf:
                        await self._emit_line(process_id, bytes(buf), prefix)
                        buf.clear()
                    return
                buf.extend(chunk)
                while True:
                    nl = buf.find(b"\n")
                    if nl < 0:
                        if len(buf) > self._MAX_LINE_BUFFER:
                            await self._emit_line(
                                process_id, bytes(buf), prefix, truncated=True
                            )
                            buf.clear()
                        break
                    line = bytes(buf[:nl])
                    del buf[: nl + 1]
                    await self._emit_line(process_id, line, prefix)
        except asyncio.CancelledError:
            return
        except Exception as e:
            # Unexpected I/O failure — surface once, then stop reading
            # this stream rather than spamming the same error.
            await self._broadcast_log(
                process_id, f"[ERROR] Log read error: {e}"
            )

    async def _emit_line(
        self,
        process_id: str,
        raw: bytes,
        prefix: str,
        truncated: bool = False,
    ) -> None:
        decoded = raw.decode("utf-8", errors="replace").rstrip("\r")
        if not decoded and not truncated:
            return
        if len(decoded) > self._MAX_BROADCAST_LINE:
            decoded = decoded[: self._MAX_BROADCAST_LINE] + " …[truncated]"
        elif truncated:
            decoded = decoded + " …[no newline within 1 MiB; flushed]"
        await self._broadcast_log(process_id, f"{prefix}{decoded}")

    async def _broadcast_log(self, process_id: str, message: str) -> None:
        """Broadcast a log message (with credentials masked)."""
        if self._log_callback:
            try:
                await self._log_callback(process_id, mask_log_line(message))
            except Exception:
                pass  # Don't let broadcast errors affect process


# Global process manager instance
process_manager = ProcessManager()
