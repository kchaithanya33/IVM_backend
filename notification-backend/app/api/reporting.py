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
        "reporting_04=%s "
        "reporting_03=%s "
        "notification_logic_app=%s "
        "notification_trigger=%s "
        "completion_logic_app=%s "
        "completion_trigger=%s "
        "function_app=%s "
        "function=%s "
        "after_scoping_function_app=%s "
        "after_scoping_function=%s "
        "triaging_validator_function_app=%s "
        "triaging_validator_function=%s",
        request.reporting_logic_app_name,
        request.reporting_03_logic_app_name,
        request.notification_logic_app_name,
        request.notification_logic_app_trigger_name,
        request.completion_logic_app_name,
        request.completion_logic_app_trigger_name,
        request.function_app_name,
        request.split_vulnerabilities_function_name,
        request.after_scoping_triaging_function_app_name,
        request.after_scoping_triaging_function_name,
        request.triaging_validator_function_app_name,
        request.triaging_validator_function_name,
    )

    service = ReportingDeploymentService()

    return service.deploy_reporting(
        request=request,
    )