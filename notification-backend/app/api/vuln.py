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
        "vuln15=%s vuln01=%s vuln04=%s vuln155=%s "
        "notification=%s callback=%s",
        request.vuln15_logic_app_name,
        request.vuln01_logic_app_name,
        request.vuln04_logic_app_name,
        request.vuln155_logic_app_name,
        request.notification_logic_app_name,
        request.callback_logic_app_name,
    )

    logger.info(
        "Function configuration: "
        "config=%s/%s "
        "get_next_business_day=%s/%s "
        "qualys_integration=%s/%s "
        "qualys_asset_group=%s/%s "
        "business_days=%s/%s",
        request.config_service_function_app_name,
        request.config_service_function_name,
        request.get_next_business_day_function_app_name,
        request.get_next_business_day_function_name,
        request.qualys_integration_function_app_name,
        request.qualys_integration_function_name,
        request.qualys_asset_group_creation_function_app_name,
        request.qualys_asset_group_creation_function_name,
        request.business_days_service_function_app_name,
        request.business_days_service_function_name,
    )

    logger.info(
        "Callback configuration: "
        "logic_app=%s trigger=%s",
        request.callback_logic_app_name,
        request.callback_logic_app_trigger_name,
    )

    logger.info(
        "Vuln 1.55 callback configuration: "
        "vuln155_logic_app=%s "
        "completion_logic_app=%s completion_trigger=%s "
        "chg_approval_logic_app=%s chg_approval_trigger=%s",
        request.vuln155_logic_app_name,
        request.completion_logic_app_name,
        request.completion_http_action_name,
        request.vuln_scan_chg_approval_logic_app_name,
        request.vuln_scan_chg_approval_http_action_name,
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