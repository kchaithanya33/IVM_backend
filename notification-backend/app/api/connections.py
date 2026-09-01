
import logging

from fastapi import APIRouter, HTTPException

from app.schemas.connection import (
    ConnectionRequest,
    ConnectionResponse,
)
from app.services.connection import ConnectionService


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api",
    tags=["Connections"],
)


connection_service = ConnectionService()


# =============================================================
# CREATE AND CHECK ALL CONNECTIONS
# =============================================================

@router.post(
    "/connection",
    response_model=ConnectionResponse,
)
def create_connection(
    request: ConnectionRequest,
) -> ConnectionResponse:

    try:

        logger.info(
            "POST /api/connection received"
        )

        return connection_service.create_connections(
            request
        )

    except FileNotFoundError as exc:

        logger.error(
            "Connection ARM template not found: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "Failed to create Azure connections"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Failed to create connections: {exc}",
        )