import logging

from fastapi import APIRouter

from app.schemas.remediation import (
    RemediationDeploymentRequest,
    RemediationDeploymentResponse,
)

from app.services.remediation import (
    RemediationDeploymentService,
)


logger = logging.getLogger(__name__)


# ============================================================
# REMEDIATION ROUTER
# ============================================================

router = APIRouter(
    prefix="/remediation",
    tags=["Remediation"],
)


# ============================================================
# DEPLOY REMEDIATION
# ============================================================

@router.post(
    "/deploy",
    response_model=RemediationDeploymentResponse,
)
def deploy_remediation(
    request: RemediationDeploymentRequest,
) -> RemediationDeploymentResponse:

    logger.info(
        "Received Remediation deployment request: "
        "logic_app=%s",
        request.logic_app_name,
    )

    service = RemediationDeploymentService()

    return service.deploy_remediation(
        request=request,
    )