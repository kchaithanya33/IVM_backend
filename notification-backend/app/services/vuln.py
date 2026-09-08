
import logging
from typing import Any, Dict

from app.azure.vuln import VulnAzureService
from app.schemas.vuln import (
    VulnDeploymentRequest,
    VulnDeploymentResponse,
    VulnFunctionUrls,
    VulnLogicAppUrls,
)


logger = logging.getLogger(__name__)


class VulnDeploymentService:
    """
    Orchestrates Vulnerability Scan Logic App deployment.

    Deployment flow:

      1. Resolve Azure API connections.
      2. Resolve all required existing Function URLs.
      3. Resolve all VULN03 Function URLs.
      4. Resolve Notification Logic App callback URL.
      5. Resolve explicitly selected callback Logic App URL.
      6. Resolve Vuln 1.55 completion Logic App URL.
      7. Resolve Vuln 1.55 CHG approval callback URL.
      8. Deploy LA-VulnScan-01.5.
      9. Get LA-VulnScan-01.5/manual callback URL.
      10. Deploy LA-VulnScan-01.
      11. Deploy LA-VulnScan-04.
      12. Deploy LA-VulnScan-01.55.
      13. Deploy LA-VulnScan-03.
      14. Get LA-VulnScan-03/manual callback URL.
      15. Pass Vuln-03 callback URL to Vuln-02.
      16. Deploy LA-VulnScan-02.
      17. Deploy LA-VulnScan-MeyDiageo-03.5 using the
          already resolved Qualys Integration URL.
    """

    def __init__(self) -> None:
        self.azure = VulnAzureService()

    # ============================================================
    # DEPLOY
    # ============================================================

    def deploy_vuln(
        self,
        request: VulnDeploymentRequest,
    ) -> VulnDeploymentResponse:

        logger.info(
            "Starting Vulnerability Scan deployment: "
            "vuln15=%s vuln01=%s vuln02=%s vuln04=%s "
            "vuln155=%s vuln03=%s meyDiageo=%s "
            "notification=%s callback_logic_app=%s",
            request.vuln15_logic_app_name,
            request.vuln01_logic_app_name,
            request.vuln02_logic_app_name,
            request.vuln04_logic_app_name,
            request.vuln155_logic_app_name,
            request.vuln03_logic_app_name,
            request.mey_diageo_logic_app_name,
            request.notification_logic_app_name,
            request.callback_logic_app_name,
        )

        # ========================================================
        # 1. RESOLVE API CONNECTIONS
        # ========================================================

        connections = self.azure.get_connections(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            table_connection_name=request.table_connection_name,
            queue_connection_name=request.queue_connection_name,
            sharepoint_connection_name=request.sharepoint_connection_name,
        )

        # ========================================================
        # 2. RESOLVE EXISTING FUNCTION URLS
        # ========================================================

        logger.info(
            "Resolving configuration Function URL: %s/%s",
            request.config_service_function_app_name,
            request.config_service_function_name,
        )

        config_service_url = self.azure.get_function_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            function_app_name=request.config_service_function_app_name,
            function_name=request.config_service_function_name,
        )

        logger.info(
            "Resolving Get Next Business Day Function URL: %s/%s",
            request.get_next_business_day_function_app_name,
            request.get_next_business_day_function_name,
        )

        get_next_business_day_url = self.azure.get_function_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            function_app_name=(
                request.get_next_business_day_function_app_name
            ),
            function_name=(
                request.get_next_business_day_function_name
            ),
        )

        logger.info(
            "Resolving Qualys Integration Function URL: %s/%s",
            request.qualys_integration_function_app_name,
            request.qualys_integration_function_name,
        )

        qualys_integration_url = self.azure.get_function_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            function_app_name=(
                request.qualys_integration_function_app_name
            ),
            function_name=(
                request.qualys_integration_function_name
            ),
        )

        logger.info(
            "Qualys Integration Function URL resolved successfully."
        )

        logger.info(
            "Resolving Qualys Asset Group Creation Function URL: %s/%s",
            request.qualys_asset_group_creation_function_app_name,
            request.qualys_asset_group_creation_function_name,
        )

        qualys_asset_group_creation_function_url = (
            self.azure.get_function_url(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                function_app_name=(
                    request.qualys_asset_group_creation_function_app_name
                ),
                function_name=(
                    request.qualys_asset_group_creation_function_name
                ),
            )
        )

        logger.info(
            "Resolving Business Days Service Function URL: %s/%s",
            request.business_days_service_function_app_name,
            request.business_days_service_function_name,
        )

        business_days_service_url = self.azure.get_function_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            function_app_name=(
                request.business_days_service_function_app_name
            ),
            function_name=(
                request.business_days_service_function_name
            ),
        )

        # ========================================================
        # 3. RESOLVE VULN03 FUNCTION URLS
        # ========================================================

        logger.info(
            "Resolving VULN03 Diageo IP Excel Function URL: %s/%s",
            request.excel_diageo_ip_function_app_name,
            request.excel_diageo_ip_function_name,
        )

        excel_diageo_ip_url = self.azure.get_function_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            function_app_name=(
                request.excel_diageo_ip_function_app_name
            ),
            function_name=(
                request.excel_diageo_ip_function_name
            ),
        )

        logger.info(
            "Resolving VULN03 Asset Group Batch Processor URL: %s/%s",
            request.asset_group_batch_processor_function_app_name,
            request.asset_group_batch_processor_function_name,
        )

        asset_group_batch_processor_url = self.azure.get_function_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            function_app_name=(
                request.asset_group_batch_processor_function_app_name
            ),
            function_name=(
                request.asset_group_batch_processor_function_name
            ),
        )

        logger.info(
            "Resolving VULN03 MeyDiageo IP Excel Function URL: %s/%s",
            request.excel_mey_diageo_ip_function_app_name,
            request.excel_mey_diageo_ip_function_name,
        )

        excel_mey_diageo_ip_url = self.azure.get_function_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            function_app_name=(
                request.excel_mey_diageo_ip_function_app_name
            ),
            function_name=(
                request.excel_mey_diageo_ip_function_name
            ),
        )

        logger.info(
            "Resolving VULN03 Qualys Asset Grouping Function URL: %s/%s",
            request.qualys_asset_grouping_function_app_name,
            request.qualys_asset_grouping_function_name,
        )

        qualys_asset_grouping_url = self.azure.get_function_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            function_app_name=(
                request.qualys_asset_grouping_function_app_name
            ),
            function_name=(
                request.qualys_asset_grouping_function_name
            ),
        )

        # ========================================================
        # EXISTING FUNCTION URL COLLECTION
        # ========================================================

        function_urls = {
            "config_service_url": config_service_url,
            "get_next_business_day_url": get_next_business_day_url,
            "qualys_integration_url": qualys_integration_url,
            "qualys_asset_group_creation_function_url": (
                qualys_asset_group_creation_function_url
            ),
            "business_days_service_url": business_days_service_url,

            # ----------------------------------------------------
            # VULN03
            # ----------------------------------------------------

            "excel_diageo_ip_url": excel_diageo_ip_url,
            "asset_group_batch_processor_url": (
                asset_group_batch_processor_url
            ),
            "excel_mey_diageo_ip_url": (
                excel_mey_diageo_ip_url
            ),
            "qualys_asset_grouping_url": (
                qualys_asset_grouping_url
            ),
        }

        # ========================================================
        # 4. RESOLVE NOTIFICATION LOGIC APP URL
        # ========================================================

        logger.info(
            "Resolving Notification Logic App callback URL: %s/%s",
            request.notification_logic_app_name,
            request.notification_logic_app_trigger_name,
        )

        notification_logic_app_url = (
            self.azure.get_logic_app_callback_url(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                logic_app_name=request.notification_logic_app_name,
                trigger_name=request.notification_logic_app_trigger_name,
            )
        )

        # ========================================================
        # 5. RESOLVE EXPLICIT CALLBACK LOGIC APP URL
        # ========================================================

        logger.info(
            "Resolving explicit callback Logic App URL: %s/%s",
            request.callback_logic_app_name,
            request.callback_logic_app_trigger_name,
        )

        callback_uri = self.azure.get_logic_app_callback_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            logic_app_name=request.callback_logic_app_name,
            trigger_name=request.callback_logic_app_trigger_name,
        )

        # ========================================================
        # 6. RESOLVE VULN 1.55 COMPLETION LOGIC APP URL
        # ========================================================

        logger.info(
            "Resolving Vuln 1.55 completion Logic App URL: "
            "%s/%s",
            request.completion_logic_app_name,
            request.completion_http_action_name,
        )

        completion_logic_app_url = (
            self.azure.get_logic_app_callback_url(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                logic_app_name=request.completion_logic_app_name,
                trigger_name=request.completion_http_action_name,
            )
        )

        logger.info(
            "Vuln 1.55 completion Logic App URL resolved successfully."
        )

        # ========================================================
        # 7. RESOLVE VULN 1.55 CHG APPROVAL CALLBACK URL
        # ========================================================

        logger.info(
            "Resolving Vuln 1.55 CHG approval callback URL: "
            "%s/%s",
            request.vuln_scan_chg_approval_logic_app_name,
            request.vuln_scan_chg_approval_http_action_name,
        )

        vuln_scan_chg_approval_callback_url = (
            self.azure.get_logic_app_callback_url(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                logic_app_name=(
                    request.vuln_scan_chg_approval_logic_app_name
                ),
                trigger_name=(
                    request.vuln_scan_chg_approval_http_action_name
                ),
            )
        )

        logger.info(
            "Vuln 1.55 CHG approval callback URL "
            "resolved successfully."
        )

        # ========================================================
        # COMMON ARM PARAMETERS
        # ========================================================

        base_params: Dict[str, Any] = {

            # ----------------------------------------------------
            # Logic App names
            # ----------------------------------------------------

            "Vuln1.5logicAppName": {
                "value": request.vuln15_logic_app_name
            },

            "Vuln01logicAppName": {
                "value": request.vuln01_logic_app_name
            },

            "vuln04logicAppName": {
                "value": request.vuln04_logic_app_name
            },

            # ----------------------------------------------------
            # Vuln 1.55 Logic App name
            # ----------------------------------------------------

            "Vuln155logicAppName": {
                "value": request.vuln155_logic_app_name
            },

            # ----------------------------------------------------
            # VULN03 Logic App name
            # ----------------------------------------------------

            "vuln03logicAppName": {
                "value": request.vuln03_logic_app_name
            },

            # ----------------------------------------------------
            # VULN02 Logic App name
            #
            # ARM parameter name in vuln.json is:
            # vulnScanChgApprovalLogicAppName
            # ----------------------------------------------------

            "vulnScanChgApprovalLogicAppName": {
                "value": request.vuln02_logic_app_name
            },

            # ----------------------------------------------------
            # MEYDIAGEO 03.5 LOGIC APP NAME
            #
            # ARM parameter name:
            # meyDiageoLogicAppName
            # ----------------------------------------------------

            "meyDiageoLogicAppName": {
                "value": request.mey_diageo_logic_app_name
            },

            # ----------------------------------------------------
            # Vuln 1.55 completion URL
            # ----------------------------------------------------

            "completionLogicAppUrl": {
                "value": completion_logic_app_url
            },

            # ----------------------------------------------------
            # Vuln 1.55 CHG approval callback URL
            # ----------------------------------------------------

            "vulnScanChgApprovalCallbackUrl": {
                "value": vuln_scan_chg_approval_callback_url
            },

            # ----------------------------------------------------
            # Location
            # ----------------------------------------------------

            "location": {
                "value": request.location
            },

            # ----------------------------------------------------
            # Storage
            # ----------------------------------------------------

            "storageAccountName": {
                "value": request.storage_account_name
            },

            # ----------------------------------------------------
            # Config Function URL
            # ----------------------------------------------------

            "configServiceUrl": {
                "value": config_service_url
            },

            # ----------------------------------------------------
            # Notification Logic App URL
            # ----------------------------------------------------

            "notificationLogicAppUrl": {
                "value": notification_logic_app_url
            },

            # ----------------------------------------------------
            # Existing Function URLs
            # ----------------------------------------------------

            "getNextBusinessDayUrl": {
                "value": get_next_business_day_url
            },

            # ----------------------------------------------------
            # QUALYS INTEGRATION URL
            #
            # This URL is already resolved above.
            # The new MeyDiageo 03.5 Logic App reuses
            # this exact same URL.
            # ----------------------------------------------------

            "qualysIntegrationUrl": {
                "value": qualys_integration_url
            },

            "qualysAssetGroupCreationFunctionUrl": {
                "value": (
                    qualys_asset_group_creation_function_url
                )
            },

            "businessDaysServiceUrl": {
                "value": business_days_service_url
            },

            # ----------------------------------------------------
            # Explicit callback URI
            # ----------------------------------------------------

            "callbackUri": {
                "value": callback_uri
            },

            # ----------------------------------------------------
            # HTTP endpoint
            # ----------------------------------------------------

            "httpEndpointUrl": {
                "value": ""
            },

            # ----------------------------------------------------
            # Connections
            # ----------------------------------------------------

            "$connections": {
                "value": connections["arm_connections"]
            },

            # ====================================================
            # VULN03 PARAMETERS
            # ====================================================

            "excelDiageoIpUrl": {
                "value": excel_diageo_ip_url
            },

            "assetGroupBatchProcessorUrl": {
                "value": asset_group_batch_processor_url
            },

            "excelMeyDiageoIpUrl": {
                "value": excel_mey_diageo_ip_url
            },

            "qualysAssetGroupingUrl": {
                "value": qualys_asset_grouping_url
            },

            "sharePointSiteUrl": {
                "value": request.sharepoint_site_url
            },
        }

        # ========================================================
        # 8. DEPLOY LA-VULNSCAN-01.5
        # ========================================================

        logger.info(
            "Deploying first Logic App: %s",
            request.vuln15_logic_app_name,
        )

        deployment15 = self.azure.deploy(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            location=request.location,
            template_resource_index=0,
            parameters=base_params,
            deployment_prefix="vulnscan015",
        )

        state15 = deployment15.get(
            "provisioning_state",
            "Failed",
        )

        # ========================================================
        # STOP IF FIRST LOGIC APP FAILED
        # ========================================================

        if str(state15).lower() != "succeeded":

            return VulnDeploymentResponse(
                success=False,
                message=deployment15.get(
                    "error",
                    "LA-VulnScan-01.5 deployment failed.",
                ),
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                location=request.location,
                vuln15_logic_app_name=(
                    request.vuln15_logic_app_name
                ),
                vuln01_logic_app_name=(
                    request.vuln01_logic_app_name
                ),
                vuln02_logic_app_name=(
                    request.vuln02_logic_app_name
                ),
                vuln04_logic_app_name=(
                    request.vuln04_logic_app_name
                ),
                vuln155_logic_app_name=(
                    request.vuln155_logic_app_name
                ),
                vuln03_logic_app_name=(
                    request.vuln03_logic_app_name
                ),
                mey_diageo_logic_app_name=(
                    request.mey_diageo_logic_app_name
                ),
                notification_logic_app_name=(
                    request.notification_logic_app_name
                ),
                callback_logic_app_name=(
                    request.callback_logic_app_name
                ),
                storage_account_name=(
                    request.storage_account_name
                ),
                vuln15_deployment_name=(
                    deployment15.get("deployment_name")
                ),
                vuln15_provisioning_state=state15,
                table_connection_id=(
                    connections.get("table_connection_id")
                ),
                queue_connection_id=(
                    connections.get("queue_connection_id")
                ),
                sharepoint_connection_id=(
                    connections.get("sharepoint_connection_id")
                ),
                function_urls=VulnFunctionUrls(
                    **function_urls
                ),
                notification_logic_app_url=(
                    notification_logic_app_url
                ),
                callback_uri=callback_uri,
                completion_logic_app_url=(
                    completion_logic_app_url
                ),
                vuln_scan_chg_approval_callback_url=(
                    vuln_scan_chg_approval_callback_url
                ),
                arm_connections=(
                    connections.get("arm_connections")
                ),
            )

        # ========================================================
        # 9. GET LA-VULNSCAN-01.5/MANUAL CALLBACK URL
        # ========================================================

        logger.info(
            "Getting callback URL for %s/%s",
            request.vuln15_logic_app_name,
            request.vuln15_logic_app_trigger_name,
        )

        http_endpoint_url = (
            self.azure.get_logic_app_callback_url(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                logic_app_name=request.vuln15_logic_app_name,
                trigger_name=request.vuln15_logic_app_trigger_name,
            )
        )

        logger.info(
            "Resolved httpEndpointUrl successfully."
        )

        # ========================================================
        # 10. PASS FIRST LOGIC APP URL TO SECOND LOGIC APP
        # ========================================================

        base_params["httpEndpointUrl"] = {
            "value": http_endpoint_url
        }

        # ========================================================
        # 11. DEPLOY LA-VULNSCAN-01
        # ========================================================

        logger.info(
            "Deploying second Logic App: %s",
            request.vuln01_logic_app_name,
        )

        deployment01 = self.azure.deploy(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            location=request.location,
            template_resource_index=1,
            parameters=base_params,
            deployment_prefix="vulnscan01",
        )

        state01 = deployment01.get(
            "provisioning_state",
            "Failed",
        )

        # ========================================================
        # STOP IF SECOND LOGIC APP FAILED
        # ========================================================

        if str(state01).lower() != "succeeded":

            return VulnDeploymentResponse(
                success=False,
                message=deployment01.get(
                    "error",
                    "LA-VulnScan-01 deployment failed.",
                ),
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                location=request.location,
                vuln15_logic_app_name=(
                    request.vuln15_logic_app_name
                ),
                vuln01_logic_app_name=(
                    request.vuln01_logic_app_name
                ),
                vuln02_logic_app_name=(
                    request.vuln02_logic_app_name
                ),
                vuln04_logic_app_name=(
                    request.vuln04_logic_app_name
                ),
                vuln155_logic_app_name=(
                    request.vuln155_logic_app_name
                ),
                vuln03_logic_app_name=(
                    request.vuln03_logic_app_name
                ),
                mey_diageo_logic_app_name=(
                    request.mey_diageo_logic_app_name
                ),
                notification_logic_app_name=(
                    request.notification_logic_app_name
                ),
                callback_logic_app_name=(
                    request.callback_logic_app_name
                ),
                storage_account_name=(
                    request.storage_account_name
                ),
                vuln15_deployment_name=(
                    deployment15.get("deployment_name")
                ),
                vuln01_deployment_name=(
                    deployment01.get("deployment_name")
                ),
                vuln15_provisioning_state=state15,
                vuln01_provisioning_state=state01,
                table_connection_id=(
                    connections.get("table_connection_id")
                ),
                queue_connection_id=(
                    connections.get("queue_connection_id")
                ),
                sharepoint_connection_id=(
                    connections.get("sharepoint_connection_id")
                ),
                function_urls=VulnFunctionUrls(
                    **function_urls
                ),
                logic_app_urls=VulnLogicAppUrls(
                    vuln01_5_logic_app_url=(
                        http_endpoint_url
                    ),
                    notification_logic_app_url=(
                        notification_logic_app_url
                    ),
                    callback_logic_app_url=callback_uri,
                    completion_logic_app_url=(
                        completion_logic_app_url
                    ),
                    vuln_scan_chg_approval_callback_url=(
                        vuln_scan_chg_approval_callback_url
                    ),
                ),
                http_endpoint_url=http_endpoint_url,
                notification_logic_app_url=(
                    notification_logic_app_url
                ),
                callback_uri=callback_uri,
                completion_logic_app_url=(
                    completion_logic_app_url
                ),
                vuln_scan_chg_approval_callback_url=(
                    vuln_scan_chg_approval_callback_url
                ),
                arm_connections=(
                    connections.get("arm_connections")
                ),
            )

        # ========================================================
        # 12. DEPLOY LA-VULNSCAN-04
        # ========================================================

        logger.info(
            "Deploying third Logic App: %s",
            request.vuln04_logic_app_name,
        )

        deployment04 = self.azure.deploy(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            location=request.location,
            template_resource_index=2,
            parameters=base_params,
            deployment_prefix="vulnscan04",
        )

        state04 = deployment04.get(
            "provisioning_state",
            "Failed",
        )

        # ========================================================
        # 13. DEPLOY LA-VULNSCAN-01.55
        # ========================================================

        logger.info(
            "Deploying fourth Logic App: %s",
            request.vuln155_logic_app_name,
        )

        deployment155 = self.azure.deploy(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            location=request.location,
            template_resource_index=3,
            parameters=base_params,
            deployment_prefix="vulnscan155",
        )

        state155 = deployment155.get(
            "provisioning_state",
            "Failed",
        )

        # ========================================================
        # 14. DEPLOY LA-VULNSCAN-03
        # ========================================================

        logger.info(
            "Deploying fifth Logic App: %s",
            request.vuln03_logic_app_name,
        )

        deployment03 = self.azure.deploy(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            location=request.location,
            template_resource_index=4,
            parameters=base_params,
            deployment_prefix="vulnscan03",
        )

        state03 = deployment03.get(
            "provisioning_state",
            "Failed",
        )

        # ========================================================
        # STOP IF VULN03 FAILED
        #
        # Vuln02 depends on Vuln03 callback URL.
        # Therefore Vuln02 must NOT be deployed if Vuln03 failed.
        # ========================================================

        if str(state03).lower() != "succeeded":

            return VulnDeploymentResponse(
                success=False,
                message=deployment03.get(
                    "error",
                    "LA-VulnScan-03 deployment failed.",
                ),
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                location=request.location,
                vuln15_logic_app_name=(
                    request.vuln15_logic_app_name
                ),
                vuln01_logic_app_name=(
                    request.vuln01_logic_app_name
                ),
                vuln02_logic_app_name=(
                    request.vuln02_logic_app_name
                ),
                vuln04_logic_app_name=(
                    request.vuln04_logic_app_name
                ),
                vuln155_logic_app_name=(
                    request.vuln155_logic_app_name
                ),
                vuln03_logic_app_name=(
                    request.vuln03_logic_app_name
                ),
                mey_diageo_logic_app_name=(
                    request.mey_diageo_logic_app_name
                ),
                notification_logic_app_name=(
                    request.notification_logic_app_name
                ),
                callback_logic_app_name=(
                    request.callback_logic_app_name
                ),
                storage_account_name=(
                    request.storage_account_name
                ),
                vuln15_deployment_name=(
                    deployment15.get("deployment_name")
                ),
                vuln01_deployment_name=(
                    deployment01.get("deployment_name")
                ),
                vuln04_deployment_name=(
                    deployment04.get("deployment_name")
                ),
                vuln155_deployment_name=(
                    deployment155.get("deployment_name")
                ),
                vuln03_deployment_name=(
                    deployment03.get("deployment_name")
                ),
                vuln15_provisioning_state=state15,
                vuln01_provisioning_state=state01,
                vuln04_provisioning_state=state04,
                vuln155_provisioning_state=state155,
                vuln03_provisioning_state=state03,
                table_connection_id=(
                    connections.get("table_connection_id")
                ),
                queue_connection_id=(
                    connections.get("queue_connection_id")
                ),
                sharepoint_connection_id=(
                    connections.get("sharepoint_connection_id")
                ),
                function_urls=VulnFunctionUrls(
                    **function_urls
                ),
                logic_app_urls=VulnLogicAppUrls(
                    vuln01_5_logic_app_url=(
                        http_endpoint_url
                    ),
                    notification_logic_app_url=(
                        notification_logic_app_url
                    ),
                    callback_logic_app_url=callback_uri,
                    completion_logic_app_url=(
                        completion_logic_app_url
                    ),
                    vuln_scan_chg_approval_callback_url=(
                        vuln_scan_chg_approval_callback_url
                    ),
                ),
                http_endpoint_url=http_endpoint_url,
                notification_logic_app_url=(
                    notification_logic_app_url
                ),
                callback_uri=callback_uri,
                completion_logic_app_url=(
                    completion_logic_app_url
                ),
                vuln_scan_chg_approval_callback_url=(
                    vuln_scan_chg_approval_callback_url
                ),
                arm_connections=(
                    connections.get("arm_connections")
                ),
            )

        # ========================================================
        # 15. GET VULN03 CALLBACK URL
        # ========================================================

        logger.info(
            "Getting callback URL for Vuln03: %s/%s",
            request.vuln03_logic_app_name,
            request.vuln03_logic_app_trigger_name,
        )

        vuln03_callback_url = (
            self.azure.get_logic_app_callback_url(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                logic_app_name=request.vuln03_logic_app_name,
                trigger_name=request.vuln03_logic_app_trigger_name,
            )
        )

        logger.info(
            "Vuln03 callback URL resolved successfully."
        )

        # ========================================================
        # 16. PASS VULN03 CALLBACK URL TO VULN02
        # ========================================================

        base_params["vulnScanAssetGroupManagerUrl"] = {
            "value": vuln03_callback_url
        }

        # ========================================================
        # 17. DEPLOY LA-VULNSCAN-02
        # ========================================================

        logger.info(
            "Deploying Vuln02 / Change Approval Logic App: %s",
            request.vuln02_logic_app_name,
        )

        deployment02 = self.azure.deploy(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            location=request.location,
            template_resource_index=5,
            parameters=base_params,
            deployment_prefix="vulnscan02",
        )

        state02 = deployment02.get(
            "provisioning_state",
            "Failed",
        )

        # ========================================================
        # 18. DEPLOY LA-VULNSCAN-MEYDIAGEO-03.5
        #
        # This Logic App only needs:
        #
        #   meyDiageoLogicAppName
        #   qualysIntegrationUrl
        #
        # qualysIntegrationUrl was already resolved above and is
        # already present in base_params.
        #
        # ARM defaults provide:
        #
        #   vulnScanProfile3.5 = LogicApps_Default_Scan
        #   scannerId3.5       = MeyDiageo
        #
        # Therefore no additional user input is required.
        # ========================================================

        logger.info(
            "Deploying MeyDiageo 03.5 Logic App: %s",
            request.mey_diageo_logic_app_name,
        )

        deployment_mey_diageo = self.azure.deploy(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            location=request.location,
            template_resource_index=6,
            parameters=base_params,
            deployment_prefix="vulnscan-meydiageo035",
        )

        state_mey_diageo = deployment_mey_diageo.get(
            "provisioning_state",
            "Failed",
        )

        logger.info(
            "MeyDiageo 03.5 deployment completed: "
            "state=%s deployment=%s",
            state_mey_diageo,
            deployment_mey_diageo.get("deployment_name"),
        )

        # ========================================================
        # FINAL SUCCESS
        # ========================================================

        success = (
            str(state15).lower() == "succeeded"
            and str(state01).lower() == "succeeded"
            and str(state04).lower() == "succeeded"
            and str(state155).lower() == "succeeded"
            and str(state03).lower() == "succeeded"
            and str(state02).lower() == "succeeded"
            and str(state_mey_diageo).lower() == "succeeded"
        )

        # ========================================================
        # RESPONSE
        # ========================================================

        return VulnDeploymentResponse(
            success=success,

            message=(
                "LA-VulnScan-01.5, "
                "LA-VulnScan-01, "
                "LA-VulnScan-04, "
                "LA-VulnScan-01.55, "
                "LA-VulnScan-03, "
                "LA-VulnScan-02 and "
                "LA-VulnScan-MeyDiageo-03.5 "
                "deployed successfully."
                if success
                else (
                    deployment_mey_diageo.get(
                        "error",
                        deployment02.get(
                            "error",
                            deployment03.get(
                                "error",
                                deployment155.get(
                                    "error",
                                    deployment04.get(
                                        "error",
                                        "Vulnerability Scan Logic App "
                                        "deployment failed.",
                                    ),
                                ),
                            ),
                        ),
                    )
                )
            ),

            subscription_id=request.subscription_id,

            resource_group_name=request.resource_group_name,

            location=request.location,

            vuln15_logic_app_name=(
                request.vuln15_logic_app_name
            ),

            vuln01_logic_app_name=(
                request.vuln01_logic_app_name
            ),

            vuln02_logic_app_name=(
                request.vuln02_logic_app_name
            ),

            vuln04_logic_app_name=(
                request.vuln04_logic_app_name
            ),

            vuln155_logic_app_name=(
                request.vuln155_logic_app_name
            ),

            vuln03_logic_app_name=(
                request.vuln03_logic_app_name
            ),

            mey_diageo_logic_app_name=(
                request.mey_diageo_logic_app_name
            ),

            notification_logic_app_name=(
                request.notification_logic_app_name
            ),

            callback_logic_app_name=(
                request.callback_logic_app_name
            ),

            storage_account_name=(
                request.storage_account_name
            ),

            vuln15_deployment_name=(
                deployment15.get("deployment_name")
            ),

            vuln01_deployment_name=(
                deployment01.get("deployment_name")
            ),

            vuln02_deployment_name=(
                deployment02.get("deployment_name")
            ),

            vuln04_deployment_name=(
                deployment04.get("deployment_name")
            ),

            vuln155_deployment_name=(
                deployment155.get("deployment_name")
            ),

            vuln03_deployment_name=(
                deployment03.get("deployment_name")
            ),

            mey_diageo_deployment_name=(
                deployment_mey_diageo.get(
                    "deployment_name"
                )
            ),

            vuln15_provisioning_state=state15,

            vuln01_provisioning_state=state01,

            vuln02_provisioning_state=state02,

            vuln04_provisioning_state=state04,

            vuln155_provisioning_state=state155,

            vuln03_provisioning_state=state03,

            mey_diageo_provisioning_state=(
                state_mey_diageo
            ),

            table_connection_id=(
                connections.get("table_connection_id")
            ),

            queue_connection_id=(
                connections.get("queue_connection_id")
            ),

            sharepoint_connection_id=(
                connections.get("sharepoint_connection_id")
            ),

            function_urls=VulnFunctionUrls(
                **function_urls
            ),

            logic_app_urls=VulnLogicAppUrls(
                vuln01_5_logic_app_url=(
                    http_endpoint_url
                ),

                notification_logic_app_url=(
                    notification_logic_app_url
                ),

                callback_logic_app_url=callback_uri,

                completion_logic_app_url=(
                    completion_logic_app_url
                ),

                vuln_scan_chg_approval_callback_url=(
                    vuln_scan_chg_approval_callback_url
                ),

                vuln03_callback_url=(
                    vuln03_callback_url
                ),
            ),

            http_endpoint_url=http_endpoint_url,

            notification_logic_app_url=(
                notification_logic_app_url
            ),

            callback_uri=callback_uri,

            completion_logic_app_url=(
                completion_logic_app_url
            ),

            vuln_scan_chg_approval_callback_url=(
                vuln_scan_chg_approval_callback_url
            ),

            vuln03_callback_url=(
                vuln03_callback_url
            ),

            arm_connections=(
                connections.get("arm_connections")
            ),
        )
