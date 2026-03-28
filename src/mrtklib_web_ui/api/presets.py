"""Preset configuration management API."""

import json
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

WORKSPACE_ROOT = Path("/workspace")
PRESETS_DIR = WORKSPACE_ROOT / "presets"


def _slugify(name: str) -> str:
    """Convert a preset name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name.strip().lower())
    return re.sub(r"[\s-]+", "-", slug) or "preset"


def _presets_dir(mode: str) -> Path:
    """Get the presets directory for a mode, creating if needed."""
    if mode not in ("post", "realtime"):
        raise HTTPException(status_code=400, detail="Mode must be 'post' or 'realtime'")
    d = PRESETS_DIR / mode
    d.mkdir(parents=True, exist_ok=True)
    return d


def _serialize_toml(config: dict[str, Any]) -> str:
    """Serialize a config dict to TOML format."""
    # Reuse the simple TOML serializer pattern
    lines: list[str] = ["# MRTKLIB Preset Configuration (TOML v1.0.0)", ""]

    def _write_table(obj: dict[str, Any], prefix: str = "") -> None:
        scalars: list[tuple[str, Any]] = []
        tables: list[tuple[str, Any]] = []
        for k, v in obj.items():
            if isinstance(v, dict):
                tables.append((k, v))
            else:
                scalars.append((k, v))
        if prefix and scalars:
            lines.append(f"[{prefix}]")
        for k, v in scalars:
            lines.append(f"{k} = {_format_value(v)}")
        if prefix and scalars:
            lines.append("")
        for k, v in tables:
            new_prefix = f"{prefix}.{k}" if prefix else k
            _write_table(v, new_prefix)

    def _format_value(v: Any) -> str:
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int):
            return str(v)
        if isinstance(v, float):
            if v != 0 and abs(v) < 0.001:
                return f"{v:.2e}"
            return str(v)
        if isinstance(v, str):
            return f'"{v}"'
        if isinstance(v, list):
            items = ", ".join(_format_value(i) for i in v)
            return f"[{items}]"
        return json.dumps(v)

    _write_table(config)
    return "\n".join(lines)


class PresetCreateRequest(BaseModel):
    name: str
    config: dict[str, Any]


class PresetUpdateRequest(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None


@router.get("/{mode}")
async def list_presets(mode: str) -> list[dict[str, str]]:
    """List all presets for a mode."""
    d = _presets_dir(mode)
    presets = []
    for f in sorted(d.glob("*.toml")):
        stat = f.stat()
        presets.append({
            "id": f.stem,
            "name": f.stem.replace("-", " ").title(),
            "created_at": datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
            "updated_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        })
    return presets


@router.post("/{mode}")
async def create_preset(mode: str, body: PresetCreateRequest) -> dict[str, str]:
    """Create a new preset."""
    d = _presets_dir(mode)
    slug = _slugify(body.name)
    path = d / f"{slug}.toml"

    # Avoid overwriting
    if path.exists():
        i = 2
        while (d / f"{slug}-{i}.toml").exists():
            i += 1
        slug = f"{slug}-{i}"
        path = d / f"{slug}.toml"

    # Write config and name as comment
    content = f"# Preset: {body.name}\n" + _serialize_toml(body.config)
    path.write_text(content)

    return {
        "id": slug,
        "name": body.name,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }


@router.get("/{mode}/{preset_id}")
async def get_preset(mode: str, preset_id: str) -> dict[str, Any]:
    """Get a single preset with its config."""
    d = _presets_dir(mode)
    path = d / f"{preset_id}.toml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preset not found")

    try:
        config = tomllib.loads(path.read_text())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse preset: {e}")

    # Extract name from first comment line
    first_line = path.read_text().split("\n")[0]
    name = preset_id.replace("-", " ").title()
    if first_line.startswith("# Preset: "):
        name = first_line[len("# Preset: "):]

    return {
        "id": preset_id,
        "name": name,
        "config": config,
    }


@router.put("/{mode}/{preset_id}")
async def update_preset(mode: str, preset_id: str, body: PresetUpdateRequest) -> dict[str, str]:
    """Update a preset (rename or update config)."""
    d = _presets_dir(mode)
    path = d / f"{preset_id}.toml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preset not found")

    if body.name and body.config:
        # Full update with rename
        new_slug = _slugify(body.name)
        new_path = d / f"{new_slug}.toml"
        content = f"# Preset: {body.name}\n" + _serialize_toml(body.config)
        new_path.write_text(content)
        if new_path != path:
            path.unlink()
        return {"id": new_slug, "name": body.name}
    elif body.name:
        # Rename only
        new_slug = _slugify(body.name)
        new_path = d / f"{new_slug}.toml"
        old_content = path.read_text()
        # Replace first line comment
        lines = old_content.split("\n")
        if lines[0].startswith("# Preset: "):
            lines[0] = f"# Preset: {body.name}"
        new_path.write_text("\n".join(lines))
        if new_path != path:
            path.unlink()
        return {"id": new_slug, "name": body.name}
    elif body.config:
        # Update config only
        first_line = path.read_text().split("\n")[0]
        name = preset_id.replace("-", " ").title()
        if first_line.startswith("# Preset: "):
            name = first_line[len("# Preset: "):]
        content = f"# Preset: {name}\n" + _serialize_toml(body.config)
        path.write_text(content)
        return {"id": preset_id, "name": name}

    return {"id": preset_id, "name": preset_id}


@router.delete("/{mode}/{preset_id}")
async def delete_preset(mode: str, preset_id: str) -> dict[str, str]:
    """Delete a preset."""
    d = _presets_dir(mode)
    path = d / f"{preset_id}.toml"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Preset not found")
    path.unlink()
    return {"status": "deleted"}
