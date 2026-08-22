"""
G2 Audio Neuromodulation Lab API
Auditory-only neuromodulation: binaural/isochronic synthesis with Zoom G2NU-style effects.
Dry-run mode only - no audio generation or hardware output.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from enum import Enum

from fastapi import FastAPI, Header, HTTPException, Body
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="G2 Audio Neuromod Lab",
    description="Auditory-only neuromodulation lab API",
    version="1.0.0"
)

# ==================== Models ====================

class SynthesisMode(str, Enum):
    BINAURAL = "binaural"
    ISOCHRONIC = "isochronic"
    COMBINED = "combined"


class SynthesisParams(BaseModel):
    type: SynthesisMode = SynthesisMode.BINAURAL
    carrier_frequency_hz: float = Field(ge=20, le=20000)
    modulation_frequency_hz: float = Field(ge=0.5, le=200)
    duration_seconds: float = Field(ge=1, le=3600)
    amplitude: float = Field(ge=0, le=1)


class EffectsConfig(BaseModel):
    zoom_g2nu_style: bool = True
    edison: dict = Field(default_factory=dict)
    parametric_eq2: dict = Field(default_factory=dict)


class MIDIConfig(BaseModel):
    cc_mapping_enabled: bool = True
    controllers: list = Field(default_factory=list)


class HUDConfig(BaseModel):
    in_ear_display: bool = False
    telemetry: bool = True


class SafetyConfig(BaseModel):
    hardware_output_enabled: bool = False
    current_limit_ma: float = 0
    intensity_limit_percent: float = 0
    emergency_stop: bool = True


class SetupRequest(BaseModel):
    project: str
    mode: str = "dry-run"
    synthesis: SynthesisParams = Field(default_factory=SynthesisParams)
    effects: EffectsConfig = Field(default_factory=EffectsConfig)
    midi: MIDIConfig = Field(default_factory=MIDIConfig)
    hud: HUDConfig = Field(default_factory=HUDConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)


class ValidationResult(BaseModel):
    valid: bool
    timestamp: str
    errors: list = Field(default_factory=list)
    warnings: list = Field(default_factory=list)


class StatusResponse(BaseModel):
    status: str
    running: bool
    timestamp: str
    uptime_seconds: Optional[float] = None
    config: Optional[SetupRequest] = None


# ==================== State ====================

app_state = {
    "running": False,
    "current_config": None,
    "start_time": None,
}


# ==================== Endpoints ====================

@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "g2-audio-neuromod-lab-api"
    }


@app.post("/validate", response_model=ValidationResult, tags=["Setup"])
async def validate_setup(
    setup: SetupRequest,
    authorization: str = Header(None)
):
    """Validate setup configuration without starting"""
    if not _check_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    errors = []
    warnings = []

    # Validate synthesis parameters
    if setup.synthesis.carrier_frequency_hz < 20:
        errors.append("Carrier frequency too low (minimum 20 Hz)")
    if setup.synthesis.modulation_frequency_hz > 200:
        warnings.append("Modulation frequency very high (>200 Hz)")

    # Validate safety config
    if setup.safety.hardware_output_enabled and setup.safety.current_limit_ma == 0:
        errors.append("Hardware output enabled but current limit is 0")

    # Validate dry-run mode
    if setup.mode != "dry-run":
        warnings.append(f"Non-dry-run mode '{setup.mode}' detected - ensure safety reviews complete")

    is_valid = len(errors) == 0

    logger.info(f"Validation: valid={is_valid}, errors={len(errors)}, warnings={len(warnings)}")

    return ValidationResult(
        valid=is_valid,
        timestamp=datetime.utcnow().isoformat(),
        errors=errors,
        warnings=warnings
    )


@app.post("/start", response_model=StatusResponse, tags=["Control"])
async def start_session(
    setup: SetupRequest,
    authorization: str = Header(None),
    x_manual_approval: str = Header(None)
):
    """Start neuromodulation session after validation and approval"""
    if not _check_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if x_manual_approval != "approved":
        raise HTTPException(status_code=403, detail="Manual approval required")

    # Validate before starting
    validation = await validate_setup(setup, authorization)
    if not validation.valid:
        raise HTTPException(status_code=400, detail=f"Validation failed: {validation.errors}")

    app_state["running"] = True
    app_state["current_config"] = setup
    app_state["start_time"] = datetime.utcnow()

    logger.info(f"Session started: {setup.project} in {setup.mode} mode")

    return StatusResponse(
        status="started",
        running=True,
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=0,
        config=setup
    )


@app.get("/status", response_model=StatusResponse, tags=["Control"])
async def get_status(authorization: str = Header(None)):
    """Get current session status"""
    if not _check_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    uptime = None
    if app_state["start_time"]:
        uptime = (datetime.utcnow() - app_state["start_time"]).total_seconds()

    return StatusResponse(
        status="running" if app_state["running"] else "idle",
        running=app_state["running"],
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime,
        config=app_state["current_config"]
    )


@app.post("/stop", tags=["Control"])
async def stop_session(authorization: str = Header(None)):
    """Stop current session"""
    if not _check_auth(authorization):
        raise HTTPException(status_code=401, detail="Unauthorized")

    was_running = app_state["running"]
    app_state["running"] = False

    logger.info(f"Session stopped (was running: {was_running})")

    return {
        "status": "stopped",
        "was_running": was_running,
        "timestamp": datetime.utcnow().isoformat()
    }


# ==================== Helpers ====================

def _check_auth(authorization: Optional[str]) -> bool:
    """Check authorization header"""
    import os
    expected_token = os.getenv("API_TOKEN", "change-this-token")
    if not authorization:
        return False
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    return parts[1] == expected_token


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
