"""
Commander Chess AI — Health & System Routes
Aligned with docs/API_CONTRACT.md Section 3.1
"""

from datetime import datetime, timezone
import time
from fastapi import APIRouter

from ..models.common import HealthResponse, VersionResponse

router = APIRouter(tags=["System"])
START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
        uptime_seconds=round(time.time() - START_TIME, 2),
    )


@router.get("/version", response_model=VersionResponse)
def get_version() -> VersionResponse:
    return VersionResponse(
        name="commander-chess-api",
        version="1.0.0",
        contract_version="1.0",
        rules_version="1.0",
        mode="TOTAL_FORCE",
    )
