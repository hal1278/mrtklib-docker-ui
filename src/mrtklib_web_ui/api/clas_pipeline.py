"""API endpoints for the CLAS pipeline (mrtk relay + mrtk cssr2rtcm3)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mrtklib_web_ui.services import (
    PipelineConfig,
    PipelineState,
    clas_pipeline_service,
)
from mrtklib_web_ui.services.clas_pipeline_service import (
    DEFAULT_BRIDGE_PORT,
    list_serial_ports,
)
from mrtklib_web_ui.services.receiver_presets import list_presets

router = APIRouter()


class PipelineStartRequest(BaseModel):
    receiver_id: str = Field(examples=["septentrio-mosaic-g5"])
    input_device: str = Field(examples=["/dev/ttyUSB0"])
    input_baud: int = Field(default=115200, gt=0)
    bridge_port: int = Field(default=DEFAULT_BRIDGE_PORT, gt=1024, lt=65536)
    sbf_record_path: str | None = Field(
        default=None,
        description=(
            "Optional path under /workspace to record the raw SBF stream "
            "(useful for post-mortem analysis). mrtk relay's time tokens "
            "(%Y, %m, %d, %h, %M, %S) are expanded at write time."
        ),
        examples=["/workspace/clas/sbf_%Y%m%d_%h%M%S.sbf"],
    )


class PipelineStatusResponse(BaseModel):
    state: str
    relay_state: str
    cssr_state: str
    started_at: str | None = None
    error_message: str | None = None
    bridge_port: int | None = None


def _to_status_response(status) -> PipelineStatusResponse:
    return PipelineStatusResponse(
        state=status.state.value,
        relay_state=status.relay_state,
        cssr_state=status.cssr_state,
        started_at=status.started_at.isoformat() if status.started_at else None,
        error_message=status.error_message,
        bridge_port=status.bridge_port,
    )


@router.get("/receivers")
async def get_receivers() -> list[dict]:
    """List supported receiver presets."""
    return list_presets()


@router.get("/serial-ports")
async def get_serial_ports() -> list[dict]:
    """Enumerate serial devices visible to the container."""
    return [{"path": p.path, "label": p.label} for p in list_serial_ports()]


@router.post("/start", response_model=PipelineStatusResponse)
async def start_pipeline(req: PipelineStartRequest) -> PipelineStatusResponse:
    """Start the CLAS pipeline (relay + cssr2rtcm3 + SBF sniffer)."""
    config = PipelineConfig(
        receiver_id=req.receiver_id,
        input_device=req.input_device,
        input_baud=req.input_baud,
        bridge_port=req.bridge_port,
        sbf_record_path=req.sbf_record_path,
    )
    try:
        status = await clas_pipeline_service.start(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if status.state == PipelineState.ERROR:
        # Surface device-not-found / device-busy errors with 422 so the UI
        # can show them without treating them as a server bug.
        raise HTTPException(status_code=422, detail=status.error_message or "Failed to start pipeline")
    return _to_status_response(status)


@router.post("/stop", response_model=PipelineStatusResponse)
async def stop_pipeline() -> PipelineStatusResponse:
    """Stop the CLAS pipeline."""
    status = await clas_pipeline_service.stop()
    return _to_status_response(status)


@router.get("/status", response_model=PipelineStatusResponse)
async def get_pipeline_status() -> PipelineStatusResponse:
    """Get current pipeline status."""
    return _to_status_response(clas_pipeline_service.status)
