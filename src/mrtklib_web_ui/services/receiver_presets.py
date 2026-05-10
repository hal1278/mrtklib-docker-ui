"""Receiver presets for the CLAS pipeline.

A preset captures the receiver-specific knobs that the user otherwise has
to look up in the receiver manual: default baud rates, the SBF format tag
that `mrtk relay` needs, and the wire-format the receiver expects on the
correction-input port.

The dict is the source of truth for the UI's receiver dropdown. Adding a
new receiver = one entry here + a bundled cssr2rtcm3 TOML config under
docker/clas-presets/ (the path is set on the preset's
cssr2rtcm3_config_path field).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReceiverPreset:
    """Per-receiver constants for the CLAS pipeline."""

    id: str
    vendor: str
    model: str
    # Format tag passed to `mrtk relay` for the SBF input stream.
    relay_input_format: str
    # Default baud rates — users can override in the form.
    default_input_baud: int
    default_output_baud: int
    # Path to the bundled cssr2rtcm3 TOML config (passed via `-k`).
    # Holds the receiver-specific signal_remap plus paths to the bundled
    # CLAS grid/BLQ/ATX files. Without it cssr2rtcm3 has no grid network
    # to bootstrap against and OSR generation fails (noosr=N every epoch).
    cssr2rtcm3_config_path: str
    # Free-form notes shown under the receiver picker.
    notes: str

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "vendor": self.vendor,
            "model": self.model,
            "label": f"{self.vendor} {self.model}",
            "relay_input_format": self.relay_input_format,
            "default_input_baud": self.default_input_baud,
            "default_output_baud": self.default_output_baud,
            "cssr2rtcm3_config_path": self.cssr2rtcm3_config_path,
            "notes": self.notes,
        }


_PRESETS: dict[str, ReceiverPreset] = {
    "septentrio-mosaic-g5": ReceiverPreset(
        id="septentrio-mosaic-g5",
        vendor="Septentrio",
        model="mosaic-G5",
        relay_input_format="sbf",
        default_input_baud=115200,
        default_output_baud=115200,
        cssr2rtcm3_config_path="/opt/mrtklib/clas-presets/septentrio-mosaic-g5.toml",
        notes=(
            "Configure the receiver to output SBF (incl. GAL L6) on the "
            "input port and accept RTCM3 (MSM4/MSM5/1005/1006) on the output "
            "port. Verified end-to-end with the v0.6.5 reference setup."
        ),
    ),
}


def list_presets() -> list[dict]:
    return [p.to_json() for p in _PRESETS.values()]


def get_preset(preset_id: str) -> ReceiverPreset | None:
    return _PRESETS.get(preset_id)
