"""CLAS pipeline orchestrator — wires `mrtk relay` and `mrtk cssr2rtcm3`.

Topology:

    receiver Serial#1 (SBF + L6) ──► mrtk relay ──► tcpsvr://localhost:PORT#sbf
                                                          │
                                                          ├──► mrtk cssr2rtcm3
                                                          │       │
                                                          │       ▼
                                                          │   receiver Serial#2 (RTCM3)
                                                          │
                                                          └──► SBF PVT sniffer (UI viz)

The service starts the two processes in order, waits briefly for the relay
to bind its TCP server, then attaches the SBF sniffer. If either process
exits, the other is stopped to avoid a half-running pipeline.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Awaitable, Callable

from mrtklib_web_ui.services.process_manager import process_manager, ProcessState
from mrtklib_web_ui.services.receiver_presets import get_preset
from mrtklib_web_ui.services.sbf_pvt_sniffer import (
    FlowStats,
    PvtFix,
    SbfTcpSniffer,
)

# Process IDs used in the global ProcessManager — fixed strings so the UI
# can subscribe by name instead of tracking dynamic UUIDs.
RELAY_PID = "clas-relay"
CSSR_PID = "clas-cssr2rtcm3"

# Local TCP loopback port for the SBF stream between relay and cssr2rtcm3.
DEFAULT_BRIDGE_PORT = 9870

# Wait this long after starting relay before connecting cssr2rtcm3 / sniffer.
_BIND_GRACE_S = 1.5


class PipelineState(str, Enum):
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


_WORKSPACE_ROOT = Path("/workspace")


@dataclass
class PipelineConfig:
    """User-facing config — what the Wizard form posts."""

    receiver_id: str
    input_device: str       # e.g. /dev/serial/by-id/usb-Septentrio_...
    input_baud: int
    output_device: str
    output_baud: int
    bridge_port: int = DEFAULT_BRIDGE_PORT
    # Optional: tee the raw SBF stream into a file under /workspace.
    # `mrtk relay` interprets %Y / %m / %d / %h / %M / %S in file paths.
    sbf_record_path: str | None = None


def _validate_sbf_record_path(raw: str) -> tuple[Path | None, str | None]:
    """Resolve a user-supplied record path against /workspace.

    Returns (parent_dir_to_create, error_message). The relay process is
    what actually opens the file (so it can apply mrtk's own time-format
    expansion); we only ensure the parent directory exists and that the
    target lives under /workspace.
    """
    p = Path(raw)
    if not p.is_absolute():
        p = _WORKSPACE_ROOT / p
    try:
        # Resolve symlinks in the parent — the leaf may not exist yet
        # (it's created by relay) and may contain mrtk's %Y / %h tokens.
        parent = p.parent.resolve(strict=False)
    except OSError as e:
        return None, f"Invalid SBF record path: {e}"
    if parent != _WORKSPACE_ROOT and _WORKSPACE_ROOT not in parent.parents:
        return None, (
            f"SBF record path must be under /workspace (got {raw}). "
            "Anything written outside /workspace is lost when the "
            "container restarts."
        )
    return parent, None


@dataclass
class PipelineStatus:
    state: PipelineState = PipelineState.IDLE
    relay_state: str = "idle"
    cssr_state: str = "idle"
    started_at: datetime | None = None
    error_message: str | None = None
    bridge_port: int | None = None


@dataclass
class SerialPort:
    path: str
    label: str  # human-readable; for /dev/serial/by-id/* this is the link basename


def list_serial_ports() -> list[SerialPort]:
    """Enumerate serial devices visible inside the container.

    Prefers /dev/serial/by-id/* entries because their names persist across
    reboots and surface the device descriptor (e.g. "usb-Septentrio_..."),
    which makes the receiver picker self-explanatory. Falls back to raw
    /dev/ttyUSB* and /dev/ttyACM* nodes when by-id is empty.
    """
    by_id = Path("/dev/serial/by-id")
    out: list[SerialPort] = []
    if by_id.is_dir():
        for entry in sorted(by_id.iterdir()):
            out.append(SerialPort(path=str(entry), label=entry.name))
        if out:
            return out

    for pattern in ("ttyUSB*", "ttyACM*"):
        for entry in sorted(Path("/dev").glob(pattern)):
            out.append(SerialPort(path=str(entry), label=entry.name))
    return out


def _device_accessible(path: str) -> tuple[bool, str | None]:
    """Return (ok, error_message). Distinguishes 'missing' from 'no permission'."""
    p = Path(path)
    if not p.exists():
        return False, (
            f"Device not found: {path}. "
            "Pass it through to the container with `--device={path}` "
            "(or `devices:` in docker-compose.yml)."
        )
    if not os.access(path, os.R_OK | os.W_OK):
        return False, (
            f"Device {path} is not readable/writable inside the container. "
            "Run the container with sufficient privileges or add the user "
            "to the dialout group on the host."
        )
    return True, None


@dataclass
class ClasPipelineService:
    """Single-instance orchestrator. The UI manages one CLAS pipeline at a time."""

    _config: PipelineConfig | None = None
    _status: PipelineStatus = field(default_factory=PipelineStatus)
    _sniffer: SbfTcpSniffer | None = None
    _watch_task: asyncio.Task | None = None
    _on_pvt: Callable[[PvtFix], Awaitable[None]] | None = None
    _on_flow: Callable[[FlowStats], Awaitable[None]] | None = None

    def set_callbacks(
        self,
        on_pvt: Callable[[PvtFix], Awaitable[None]],
        on_flow: Callable[[FlowStats], Awaitable[None]],
    ) -> None:
        self._on_pvt = on_pvt
        self._on_flow = on_flow

    @property
    def status(self) -> PipelineStatus:
        # Refresh sub-process states from the global ProcessManager.
        relay = self._status_for(RELAY_PID)
        cssr = self._status_for(CSSR_PID)
        self._status.relay_state = relay
        self._status.cssr_state = cssr
        if self._status.state == PipelineState.RUNNING and (
            relay in ("stopped", "error") or cssr in ("stopped", "error")
        ):
            # One side died — reflect that immediately even before _watch_task
            # has a chance to tear the other side down.
            self._status.state = PipelineState.ERROR
        return self._status

    @staticmethod
    def _status_for(pid: str) -> str:
        info = process_manager._process_info.get(pid)
        return info.state.value if info else "idle"

    async def start(self, config: PipelineConfig) -> PipelineStatus:
        if self._status.state in (PipelineState.STARTING, PipelineState.RUNNING):
            raise RuntimeError("CLAS pipeline is already running")

        preset = get_preset(config.receiver_id)
        if preset is None:
            raise ValueError(f"Unknown receiver preset: {config.receiver_id}")

        for path in (config.input_device, config.output_device):
            ok, err = _device_accessible(path)
            if not ok:
                self._status = PipelineStatus(
                    state=PipelineState.ERROR, error_message=err
                )
                return self._status

        if config.input_device == config.output_device:
            self._status = PipelineStatus(
                state=PipelineState.ERROR,
                error_message="Input and output devices must differ.",
            )
            return self._status

        self._config = config
        self._status = PipelineStatus(
            state=PipelineState.STARTING,
            started_at=datetime.now(),
            bridge_port=config.bridge_port,
        )

        relay_in = f"serial://{_dev_basename(config.input_device)}:{config.input_baud}#{preset.relay_input_format}"
        relay_out_tcp = f"tcpsvr://:{config.bridge_port}"
        relay_args: list[str] = ["-in", relay_in, "-out", relay_out_tcp]
        if config.sbf_record_path:
            parent, err = _validate_sbf_record_path(config.sbf_record_path)
            if err is not None:
                self._status = PipelineStatus(
                    state=PipelineState.ERROR, error_message=err
                )
                return self._status
            assert parent is not None
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                self._status = PipelineStatus(
                    state=PipelineState.ERROR,
                    error_message=f"Cannot create SBF record directory {parent}: {e}",
                )
                return self._status
            # `mrtk relay` expands its own time-format tokens (%Y, %h, ...).
            relay_args += ["-out", f"file://{config.sbf_record_path}"]

        try:
            await process_manager.start(
                command="str2str",
                args=relay_args,
                process_id=RELAY_PID,
            )
        except Exception as e:
            self._status.state = PipelineState.ERROR
            self._status.error_message = f"Failed to start relay: {e}"
            return self._status

        await asyncio.sleep(_BIND_GRACE_S)

        cssr_in = f"sbf://tcpcli://localhost:{config.bridge_port}"
        cssr_out = f"serial://{_dev_basename(config.output_device)}:{config.output_baud}"
        try:
            await process_manager.start(
                command="cssr2rtcm3",
                args=["-in", cssr_in, "-out", cssr_out],
                process_id=CSSR_PID,
            )
        except Exception as e:
            self._status.state = PipelineState.ERROR
            self._status.error_message = f"Failed to start cssr2rtcm3: {e}"
            await self._stop_process(RELAY_PID)
            return self._status

        if self._on_pvt is not None and self._on_flow is not None:
            self._sniffer = SbfTcpSniffer(
                host="localhost",
                port=config.bridge_port,
                on_pvt=self._on_pvt,
                on_flow=self._on_flow,
            )
            self._sniffer.start()

        self._status.state = PipelineState.RUNNING
        self._watch_task = asyncio.create_task(self._watch())
        return self._status

    async def stop(self) -> PipelineStatus:
        if self._status.state == PipelineState.IDLE:
            return self._status
        self._status.state = PipelineState.STOPPING

        if self._watch_task is not None:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None

        if self._sniffer is not None:
            await self._sniffer.stop()
            self._sniffer = None

        # cssr2rtcm3 first — it depends on the relay's TCP server, so we want
        # to give it a clean EOF rather than tearing the relay out from under it.
        await self._stop_process(CSSR_PID)
        await self._stop_process(RELAY_PID)

        self._status.state = PipelineState.STOPPED
        return self._status

    async def _watch(self) -> None:
        """If either process exits, tear the whole pipeline down."""
        try:
            while True:
                await asyncio.sleep(1.0)
                relay_alive = self._status_for(RELAY_PID) == "running"
                cssr_alive = self._status_for(CSSR_PID) == "running"
                if not (relay_alive and cssr_alive):
                    self._status.state = PipelineState.ERROR
                    self._status.error_message = (
                        "A pipeline process exited unexpectedly — "
                        "see relay/cssr2rtcm3 logs."
                    )
                    if self._sniffer is not None:
                        await self._sniffer.stop()
                        self._sniffer = None
                    if relay_alive:
                        await self._stop_process(RELAY_PID)
                    if cssr_alive:
                        await self._stop_process(CSSR_PID)
                    return
        except asyncio.CancelledError:
            return

    @staticmethod
    async def _stop_process(pid: str) -> None:
        if pid not in process_manager._processes:
            return
        try:
            await process_manager.stop(pid, timeout=3.0)
        except Exception:
            pass


def _dev_basename(path: str) -> str:
    """`mrtk relay`'s `serial://name:baud` resolves `name` against `/dev/`.

    Resolve symlinks first — `/dev/serial/by-id/usb-...` typically points at
    `/dev/ttyUSB0`. The bare name (`ttyUSB0`) is what the URI parser expects;
    a path with internal slashes confuses it.
    """
    p = Path(path)
    if p.is_symlink():
        try:
            p = p.resolve(strict=False)
        except OSError:
            pass
    name = p.name
    return name or path


# Global instance
clas_pipeline_service = ClasPipelineService()
