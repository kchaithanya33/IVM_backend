import logging

from fastapi import APIRouter

from app.schemas.reporting import (
    ReportingDeploymentRequest,
    ReportingDeploymentResponse,
)

from app.services.reporting import (
    ReportingDeploymentService,
)


logger = logging.getLogger(__name__)


# ============================================================
# REPORTING ROUTER
# ============================================================

router = APIRouter(
    prefix="/reporting",
    tags=["Reporting"],
)


# ============================================================
# DEPLOY REPORTING
# ============================================================

@router.post(
    "/deploy",
    response_model=ReportingDeploymentResponse,
)
def deploy_reporting(
    request: ReportingDeploymentRequest,
) -> ReportingDeploymentResponse:

    logger.info(
        "Received Reporting deployment request: "
        "logic_app=%s "
        "notification_logic_app=%s "
        "notification_trigger=%s "
        "function_app=%s "
        "function=%s",
        request.reporting_logic_app_name,
        request.notification_logic_app_name,
        request.notification_logic_app_trigger_name,
        request.function_app_name,
        request.split_vulnerabilities_function_name,
    )

    service = ReportingDeploymentService()

    return service.deploy_reporting(
        request=request,
    )