

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
    prefix="/scoping",
    tags=["Scoping"],
)


# ============================================================
# DEPLOY SCOPING
# ============================================================

@router.post(
    "/deploy",
    response_model=ScopingDeploymentResponse,
)
def deploy_scoping(
    request: ScopingDeploymentRequest,
) -> ScopingDeploymentResponse:

    logger.info(
        "Received Scoping deployment request: "
        "logic_app=%s scoping01=%s scoping02=%s",
        request.logic_app_name,
        request.scoping01_logic_app_name,
        request.scoping02_logic_app_name,
    )

    service = ScopingDeploymentService()

    return service.deploy_scoping(
        request=request,
    )
