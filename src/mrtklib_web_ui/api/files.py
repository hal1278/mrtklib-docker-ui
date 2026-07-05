"""File browser API for logical /workspace and /data roots."""

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from mrtklib_web_ui.paths import (
    CORRECTIONS_ALIAS,
    DATA_ALIAS,
    ROOTS,
    WORKSPACE_ALIAS,
    find_root_for_path,
    is_allowed_path as _is_allowed_path,
    path_within_root,
    resolve_path as _resolve_path,
    runtime_path_to_alias,
)

router = APIRouter()

WORKSPACE_ROOT = next(root for root in ROOTS if root.alias == WORKSPACE_ALIAS)
DATA_ROOT = next(root for root in ROOTS if root.alias == DATA_ALIAS)
CORRECTIONS_ROOT = next(root for root in ROOTS if root.alias == CORRECTIONS_ALIAS)


def _find_root(p: Path):
    """Find which allowed root a path belongs to."""
    root = find_root_for_path(p)
    if root:
        return root
    raise HTTPException(status_code=403, detail="Access denied")


class FileInfo(BaseModel):
    """File or directory information."""

    name: str
    path: str
    type: Literal["file", "directory"]
    size: int | None = None


class DirectoryListing(BaseModel):
    """Directory listing response."""

    path: str
    items: list[FileInfo]


class RootInfo(BaseModel):
    """Volume root information."""

    path: str
    label: str
    writable: bool
    mounted: bool


@router.get("/roots")
async def list_roots() -> list[RootInfo]:
    """List available volume roots."""
    root_infos: list[RootInfo] = []
    for root in ROOTS:
        try:
            mounted = root.actual.exists()
            if mounted and not root.writable:
                mounted = root.actual.is_dir() and any(root.actual.iterdir())
        except OSError:
            mounted = False
        root_infos.append(
            RootInfo(
                path=str(root.alias),
                label=root.label,
                writable=root.writable,
                mounted=mounted,
            )
        )
    return root_infos


@router.get("/corrections")
async def list_corrections() -> dict[str, list[dict[str, Any]]]:
    """List bundled MRTKLIB correction files."""
    result: dict[str, list[dict[str, Any]]] = {}
    for profile in ["clas", "madoca"]:
        profile_path = CORRECTIONS_ROOT.actual / profile
        files: list[dict[str, Any]] = []
        try:
            if profile_path.exists():
                for f in sorted(profile_path.iterdir()):
                    try:
                        if not f.is_file():
                            continue
                        files.append({
                            "filename": f.name,
                            "path": runtime_path_to_alias(f),
                            "size_bytes": f.stat().st_size,
                        })
                    except OSError:
                        continue
        except OSError:
            files = []
        result[profile] = files
    return result


@router.get("/browse", response_model=DirectoryListing)
async def browse_directory(path: str = str(WORKSPACE_ALIAS)) -> DirectoryListing:
    """Browse files and directories in workspace or data."""
    target_path = _resolve_path(path)

    if not _is_allowed_path(target_path):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target_path.exists():
        # Graceful degradation for unmounted /data
        root = _find_root(target_path)
        if root == DATA_ROOT:
            return DirectoryListing(path=str(DATA_ALIAS), items=[])
        raise HTTPException(status_code=404, detail="Path not found")

    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    root = _find_root(target_path)
    items: list[FileInfo] = []
    try:
        for item in sorted(target_path.iterdir(), key=lambda x: (x.is_file(), x.name)):
            item_type: Literal["file", "directory"] = "directory" if item.is_dir() else "file"
            relative_path = str(item.relative_to(root.actual))
            items.append(
                FileInfo(
                    name=item.name,
                    path=str(root.alias / relative_path),
                    type=item_type,
                    size=item.stat().st_size if item.is_file() else None,
                )
            )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    return DirectoryListing(
        path=runtime_path_to_alias(target_path),
        items=items,
    )


@router.get("/download")
async def download_file(path: str) -> FileResponse:
    """Download a file from workspace or data."""
    target_path = _resolve_path(path)

    if not _is_allowed_path(target_path):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not target_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    return FileResponse(
        path=target_path,
        filename=target_path.name,
        media_type="application/octet-stream",
    )


class FileReadResponse(BaseModel):
    """Response for reading file text contents."""

    path: str
    content: str
    total_lines: int
    returned_lines: int
    truncated: bool
    file_size: int


@router.get("/read", response_model=FileReadResponse)
async def read_file(path: str, max_lines: int = 5000) -> FileReadResponse:
    """Read text contents of a file in workspace or data."""
    target_path = _resolve_path(path)

    if not _is_allowed_path(target_path):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not target_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    file_size = target_path.stat().st_size
    lines = target_path.read_text(errors="replace").splitlines()
    total_lines = len(lines)
    selected = lines[:max_lines]

    return FileReadResponse(
        path=runtime_path_to_alias(target_path),
        content="\n".join(selected),
        total_lines=total_lines,
        returned_lines=len(selected),
        truncated=max_lines < total_lines,
        file_size=file_size,
    )


@router.post("/write")
async def write_file(path: str, body: dict[str, Any]) -> dict[str, str]:
    """Write text content to a file (workspace only)."""
    target_path = _resolve_path(path)

    # Only allow writes to workspace
    if not path_within_root(target_path, WORKSPACE_ROOT.actual):
        raise HTTPException(
            status_code=403,
            detail="Write access denied - only /workspace is writable",
        )

    content = body.get("content", "")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content)
    return {"status": "ok", "path": runtime_path_to_alias(target_path)}
