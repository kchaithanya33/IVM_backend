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
      2. Resolve all required Function URLs.
      3. Resolve Notification Logic App callback URL.
      4. Resolve explicitly selected callback Logic App URL.
      5. Resolve Vuln 1.55 completion Logic App URL.
      6. Resolve Vuln 1.55 CHG approval callback URL.
      7. Deploy LA-VulnScan-01.5.
      8. Get LA-VulnScan-01.5/manual callback URL.
      9. Deploy LA-VulnScan-01 using that URL as httpEndpointUrl.
      10. Deploy LA-VulnScan-04 using the resolved Function URLs
          and explicitly selected callbackUri.
      11. Deploy LA-VulnScan-01.55.
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
            "vuln15=%s vuln01=%s vuln04=%s "
            "vuln155=%s notification=%s "
            "callback_logic_app=%s",
            request.vuln15_logic_app_name,
            request.vuln01_logic_app_name,
            request.vuln04_logic_app_name,
            request.vuln155_logic_app_name,
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
        # 2. RESOLVE FUNCTION URLs
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

        function_urls = {
            "config_service_url": config_service_url,
            "get_next_business_day_url": get_next_business_day_url,
            "qualys_integration_url": qualys_integration_url,
            "qualys_asset_group_creation_function_url": (
                qualys_asset_group_creation_function_url
            ),
            "business_days_service_url": business_days_service_url,
        }

        # ========================================================
        # 3. RESOLVE NOTIFICATION LOGIC APP URL
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
        # 4. RESOLVE EXPLICIT CALLBACK LOGIC APP URL
        # ========================================================
        #
        # EXISTING LOGIC - UNCHANGED
        #
        # This is completely independent of vuln04_logic_app_name.
        #
        # The user explicitly selects:
        #
        #   callback_logic_app_name
        #   callback_logic_app_trigger_name
        #
        # Backend resolves the URL and passes it to ARM as:
        #
        #   callbackUri
        #
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
        # 5. RESOLVE VULN 1.55 COMPLETION LOGIC APP URL
        # ========================================================
        #
        # NEW LOGIC
        #
        # User provides:
        #
        #   completion_logic_app_name
        #   completion_http_action_name
        #
        # Backend resolves:
        #
        #   completionLogicAppUrl
        #
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
        # 6. RESOLVE VULN 1.55 CHG APPROVAL CALLBACK URL
        # ========================================================
        #
        # NEW LOGIC
        #
        # User provides:
        #
        #   vuln_scan_chg_approval_logic_app_name
        #   vuln_scan_chg_approval_http_action_name
        #
        # Backend resolves:
        #
        #   vulnScanChgApprovalCallbackUrl
        #
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

            "Vuln1.55logicAppName": {
                "value": request.vuln155_logic_app_name
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
            # Function URLs
            # ----------------------------------------------------

            "getNextBusinessDayUrl": {
                "value": get_next_business_day_url
            },

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
            #
            # Initially empty.
            #
            # It will be replaced after LA-VulnScan-01.5
            # has successfully deployed.
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
        }

        # ========================================================
        # 7. DEPLOY LA-VULNSCAN-01.5
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
                vuln04_logic_app_name=(
                    request.vuln04_logic_app_name
                ),
                vuln155_logic_app_name=(
                    request.vuln155_logic_app_name
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
        # 8. GET LA-VULNSCAN-01.5/MANUAL CALLBACK URL
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
        # 9. PASS FIRST LOGIC APP URL TO SECOND LOGIC APP
        # ========================================================

        base_params["httpEndpointUrl"] = {
            "value": http_endpoint_url
        }

        # ========================================================
        # 10. DEPLOY LA-VULNSCAN-01
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
                vuln04_logic_app_name=(
                    request.vuln04_logic_app_name
                ),
                vuln155_logic_app_name=(
                    request.vuln155_logic_app_name
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
        # 11. DEPLOY LA-VULNSCAN-04
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
        # 12. DEPLOY LA-VULNSCAN-01.55
        # ========================================================
        #
        # NEW LOGIC
        #
        # Resource index 3 must be the Vuln 1.55 Logic App
        # in arm/vuln.json.
        #
        # The following parameters are already in base_params:
        #
        #   Vuln1.55logicAppName
        #   completionLogicAppUrl
        #   vulnScanChgApprovalCallbackUrl
        #
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
        # FINAL SUCCESS
        # ========================================================

        success = (
            str(state15).lower() == "succeeded"
            and str(state01).lower() == "succeeded"
            and str(state04).lower() == "succeeded"
            and str(state155).lower() == "succeeded"
        )

        # ========================================================
        # RESPONSE
        # ========================================================

        return VulnDeploymentResponse(
            success=success,

            message=(
                "LA-VulnScan-01.5, "
                "LA-VulnScan-01, "
                "LA-VulnScan-04 and "
                "LA-VulnScan-01.55 deployed successfully."
                if success
                else (
                    deployment155.get(
                        "error",
                        deployment04.get(
                            "error",
                            "Vulnerability Scan Logic App "
                            "deployment failed.",
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

            vuln04_logic_app_name=(
                request.vuln04_logic_app_name
            ),

            vuln155_logic_app_name=(
                request.vuln155_logic_app_name
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

            vuln15_provisioning_state=state15,

            vuln01_provisioning_state=state01,

            vuln04_provisioning_state=state04,

            vuln155_provisioning_state=state155,

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