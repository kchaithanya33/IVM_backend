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
        "vuln03=%s vuln02=%s meyDiageo035=%s "
        "authFailure=%s vuln05=%s "
        "notification=%s",
        request.vuln15_logic_app_name,
        request.vuln01_logic_app_name,
        request.vuln04_logic_app_name,
        request.vuln155_logic_app_name,
        request.vuln03_logic_app_name,
        request.vuln02_logic_app_name,
        request.mey_diageo_logic_app_name,
        request.vuln_scan_auth_failure_logic_app_name,
        request.vuln05_logic_app_name,
        request.notification_logic_app_name,
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
        "VULN03 Function configuration: "
        "excel_diageo=%s/%s "
        "asset_group_batch=%s/%s "
        "excel_mey_diageo=%s/%s "
        "qualys_asset_grouping=%s/%s",
        request.excel_diageo_ip_function_app_name,
        request.excel_diageo_ip_function_name,
        request.asset_group_batch_processor_function_app_name,
        request.asset_group_batch_processor_function_name,
        request.excel_mey_diageo_ip_function_app_name,
        request.excel_mey_diageo_ip_function_name,
        request.qualys_asset_grouping_function_app_name,
        request.qualys_asset_grouping_function_name,
    )

    # ============================================================
    # VULN AUTH FAILURE DETECTION FUNCTION CONFIGURATION
    # ============================================================

    logger.info(
        "Vuln Auth Failure Detection configuration: "
        "logic_app=%s "
        "qualys_launch_report=%s/%s "
        "qualys_check_report=%s/%s "
        "qualys_download_report=%s/%s "
        "auth_failure_analysis=%s/%s",
        request.vuln_scan_auth_failure_logic_app_name,
        request.qualys_launch_report_function_app_name,
        request.qualys_launch_report_function_name,
        request.qualys_check_report_function_app_name,
        request.qualys_check_report_function_name,
        request.qualys_download_report_function_app_name,
        request.qualys_download_report_function_name,
        request.auth_failure_analysis_function_app_name,
        request.auth_failure_analysis_function_name,
    )

    # ============================================================
    # VULN05 FUNCTION CONFIGURATION
    # ============================================================

    logger.info(
        "Vuln05 configuration: "
        "logic_app=%s "
        "qualys_scan_function=%s/%s",
        request.vuln05_logic_app_name,
        request.qualys_scan_function_app_name,
        request.qualys_scan_function_name,
    )

    logger.info(
        "Vuln 1.55 callback configuration: "
        "vuln155_logic_app=%s "
        "completion_logic_app=%s completion_trigger=%s",
        request.vuln155_logic_app_name,
        request.completion_logic_app_name,
        request.completion_http_action_name,
    )

    logger.info(
        "Vuln 03 callback configuration: "
        "vuln03_logic_app=%s trigger=%s",
        request.vuln03_logic_app_name,
        request.vuln03_logic_app_trigger_name,
    )

    logger.info(
        "MeyDiageo 03.5 Logic App configuration: "
        "logic_app=%s",
        request.mey_diageo_logic_app_name,
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