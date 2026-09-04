import logging

from fastapi import APIRouter, HTTPException

from app.schemas.vuln import (
    VulnDeploymentRequest,
    VulnDeploymentResponse,
)
from app.services.vuln import VulnDeploymentService


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/vuln",
    tags=["Vulnerability Scan"],
)


@router.post(
    "/deploy",
    response_model=VulnDeploymentResponse,
)
def deploy_vuln(
    request: VulnDeploymentRequest,
) -> VulnDeploymentResponse:

    logger.info(
        "Received Vulnerability Scan deployment request: "
        "vuln15=%s vuln01=%s notification=%s "
        "function_app=%s",
        request.vuln15_logic_app_name,
        request.vuln01_logic_app_name,
        request.notification_logic_app_name,
        request.function_app_name,
    )

    try:

        return VulnDeploymentService().deploy_vuln(
            request
        )

    except Exception as exc:

        logger.exception(
            "Vulnerability Scan deployment failed."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Vulnerability Scan deployment failed: "
                f"{exc}"
            ),
        ) from exc