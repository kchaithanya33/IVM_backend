
import logging

from fastapi import (
    APIRouter,
    HTTPException,
)

from app.schemas.connections import (
    ConnectionSetupRequest,
    ConnectionSetupResponse,
)

from app.services.connection_service import (
    ConnectionSetupService,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/connections",
    tags=["Connections"],
)


# ============================================================
# CHECK / CREATE / AUTHENTICATE CONNECTIONS
# ============================================================

@router.post(
    "/setup",
    response_model=ConnectionSetupResponse,
)
def setup_connections(
    request: ConnectionSetupRequest,
):

    try:

        service = (
            ConnectionSetupService()
        )

        return service.setup(
            request
        )

    except ValueError as exc:

        logger.exception(
            "Connection validation error."
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:

        logger.exception(
            "Connection setup error."
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Unexpected connection error."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unexpected error while "
                "processing API connections: "
                f"{exc}"
            ),
        ) from exc
