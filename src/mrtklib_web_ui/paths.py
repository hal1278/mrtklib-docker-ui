"""Runtime path and binary configuration with Docker-compatible defaults."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RootMapping:
    """Logical UI root mapped to an actual runtime directory."""

    alias: Path
    actual: Path
    label: str
    writable: bool


WORKSPACE_ALIAS = Path("/workspace")
DATA_ALIAS = Path("/data")
SYSTEM_ALIAS = Path("/opt/mrtklib")
CORRECTIONS_ALIAS = SYSTEM_ALIAS / "corrections"

DOCKER_WORKSPACE_DIR = WORKSPACE_ALIAS
DOCKER_DATA_DIR = DATA_ALIAS
DOCKER_SYSTEM_DIR = SYSTEM_ALIAS
DOCKER_MRTK_BIN = Path("/usr/local/bin/mrtk")
DOCKER_STATIC_DIR = Path("/app/static")
DOCKER_NETRC_PATH = Path("/root/.netrc")


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    return Path(value).expanduser()


def _resolved(path: Path) -> Path:
    return path.expanduser().resolve()


def get_mrtk_bin() -> Path:
    """Resolve mrtk binary from env, PATH, then Docker fallback."""
    env_value = os.getenv("MRTKLIB_MRTK_BIN")
    if env_value:
        return Path(env_value).expanduser()

    discovered = shutil.which("mrtk")
    if discovered:
        return Path(discovered)

    return DOCKER_MRTK_BIN


WORKSPACE_DIR = _env_path("MRTKLIB_WORKSPACE_DIR", DOCKER_WORKSPACE_DIR)
DATA_DIR = _env_path("MRTKLIB_DATA_DIR", DOCKER_DATA_DIR)
SYSTEM_DIR = _env_path("MRTKLIB_SYSTEM_DIR", DOCKER_SYSTEM_DIR)
CORRECTIONS_DIR = _env_path(
    "MRTKLIB_CORRECTIONS_DIR",
    SYSTEM_DIR / "corrections",
)
CLAS_PRESETS_DIR = SYSTEM_DIR / "clas-presets"
BUNDLED_PRESETS_DIR = SYSTEM_DIR / "presets"
MRTK_BIN = get_mrtk_bin()
STATIC_DIR = _env_path("MRTKLIB_STATIC_DIR", DOCKER_STATIC_DIR)
NETRC_PATH = _env_path("MRTKLIB_NETRC_PATH", DOCKER_NETRC_PATH)
CREDENTIALS_FILE = _env_path(
    "MRTKLIB_CREDENTIALS_FILE",
    WORKSPACE_DIR / ".credentials.toml",
)

ROOTS: tuple[RootMapping, ...] = (
    RootMapping(
        alias=WORKSPACE_ALIAS,
        actual=WORKSPACE_DIR,
        label="Workspace (output)",
        writable=True,
    ),
    RootMapping(
        alias=DATA_ALIAS,
        actual=DATA_DIR,
        label="Data (read-only)",
        writable=False,
    ),
    RootMapping(
        alias=CORRECTIONS_ALIAS,
        actual=CORRECTIONS_DIR,
        label="System (read-only)",
        writable=False,
    ),
)

# Backwards-compatible names used by existing API modules.
WORKSPACE_ROOT = _resolved(WORKSPACE_DIR)
DATA_ROOT = _resolved(DATA_DIR)
CORRECTIONS_ROOT = _resolved(CORRECTIONS_DIR)
ALLOWED_ROOTS: tuple[Path, ...] = (
    WORKSPACE_ROOT,
    DATA_ROOT,
    CORRECTIONS_ROOT,
)


def path_within_root(path: Path, root: Path) -> bool:
    """Return True when path is the root itself or a descendant of it."""
    resolved_path = _resolved(path)
    resolved_root = _resolved(root)
    return resolved_path == resolved_root or resolved_root in resolved_path.parents


def get_root_by_alias(alias: str | Path) -> RootMapping | None:
    alias_path = Path(str(alias))
    for root in ROOTS:
        if root.alias == alias_path:
            return root
    return None


def find_root_for_path(path: Path) -> RootMapping | None:
    for root in ROOTS:
        if path_within_root(path, root.actual):
            return root
    return None


def resolve_runtime_path(
    path: str | Path,
    default_root: str | Path = WORKSPACE_ALIAS,
) -> Path:
    """Resolve logical /workspace, /data, or correction paths to runtime paths."""
    raw = str(path).strip()
    if not raw:
        root = get_root_by_alias(default_root) or ROOTS[0]
        return root.actual

    for root in ROOTS:
        alias_str = str(root.alias)
        if raw == alias_str:
            return root.actual
        prefix = f"{alias_str}/"
        if raw.startswith(prefix):
            return root.actual / raw[len(prefix):]

    candidate = Path(raw).expanduser()
    if candidate.is_absolute():
        return candidate

    root = get_root_by_alias(default_root) or ROOTS[0]
    return root.actual / raw.lstrip("/")


def runtime_path_to_alias(path: Path) -> str:
    """Render an actual runtime path back to its logical UI alias."""
    resolved_path = _resolved(path)
    for root in ROOTS:
        resolved_root = _resolved(root.actual)
        if resolved_path == resolved_root:
            return str(root.alias)
        if resolved_root in resolved_path.parents:
            return str(root.alias / resolved_path.relative_to(resolved_root))
    return str(path)


def resolve_config_path(path: str) -> str:
    """Resolve a path value immediately before writing an MRTK config.

    UI-facing paths keep their Docker-compatible aliases, while subprocesses
    receive the actual host or Nix-store path. Stream URLs are not filesystem
    paths and must pass through unchanged.
    """
    raw = path.strip()
    if not raw or "://" in raw:
        return raw
    return str(resolve_runtime_path(raw))


def resolve_stream_url(value: str) -> str:
    """Translate logical roots inside an MRTKLIB ``file://`` stream URL."""
    for root in ROOTS:
        prefix = f"file://{root.alias}"
        if value.startswith(prefix):
            return f"file://{root.actual}{value[len(prefix):]}"
    return value


def resolve_path(path: str | Path) -> Path:
    """Resolve a UI path to an absolute path under an allowed root.

    Logical paths such as ``/workspace/foo`` map to the configured runtime
    directory, while relative paths default to the workspace.
    """
    return _resolved(resolve_runtime_path(path))


def is_allowed_path(path: Path) -> bool:
    """Return True when a resolved path is within an allowed root."""
    return any(path_within_root(path, root) for root in ALLOWED_ROOTS)


def is_within(path: Path, root: Path) -> bool:
    """Return True when path is strictly inside root, not equal to root."""
    resolved_path = _resolved(path)
    resolved_root = _resolved(root)
    return resolved_root in resolved_path.parents
