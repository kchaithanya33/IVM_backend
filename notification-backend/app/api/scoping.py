import logging

from fastapi import APIRouter

from app.schemas.scoping import (
    ScopingDeploymentRequest,
    ScopingDeploymentResponse,
)

from app.services.scoping import (
    ScopingDeploymentService,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/scoping",
    tags=["Scoping"],
)


# ============================================================
# SERVICE
# ============================================================

scoping_service = ScopingDeploymentService()


# ============================================================
# DEPLOY SCOPING-00
# ============================================================

@router.post(
    "/deploy",
    response_model=ScopingDeploymentResponse,
)
def deploy_scoping(
    request: ScopingDeploymentRequest,
) -> ScopingDeploymentResponse:

    logger.info(
        "Received Scoping-00 deployment request."
    )

    return scoping_service.deploy_scoping(
        request
    )


# ============================================================
# HEALTH / TEST ENDPOINT
# ============================================================

@router.get(
    "/health",
)
def scoping_health():

    return {
        "status": "ok",
        "service": "scoping",
    }