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

    Deployment order:

      1. Resolve Azure API connections.
      2. Resolve Config Function URL.
      3. Resolve Notification Logic App callback URL.
      4. Deploy LA-VulnScan-01.5.
      5. Get LA-VulnScan-01.5/manual callback URL.
      6. Deploy LA-VulnScan-01 with that URL as httpEndpointUrl.
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
            "vuln15=%s vuln01=%s notification=%s "
            "function_app=%s",
            request.vuln15_logic_app_name,
            request.vuln01_logic_app_name,
            request.notification_logic_app_name,
            request.function_app_name,
        )

        # ========================================================
        # 1. RESOLVE API CONNECTIONS
        # ========================================================

        connections = self.azure.get_connections(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            table_connection_name=(
                request.table_connection_name
            ),
            queue_connection_name=(
                request.queue_connection_name
            ),
            sharepoint_connection_name=(
                request.sharepoint_connection_name
            ),
        )

        # ========================================================
        # 2. RESOLVE CONFIG FUNCTION URL
        # ========================================================

        config_service_url = (
            self.azure.get_function_url(
                subscription_id=request.subscription_id,
                resource_group_name=(
                    request.resource_group_name
                ),
                function_app_name=(
                    request.function_app_name
                ),
                function_name=(
                    request.config_service_function_name
                ),
            )
        )

        function_urls = {
            "config_service_url": config_service_url,
        }

        # ========================================================
        # 3. RESOLVE NOTIFICATION LOGIC APP URL
        # ========================================================

        notification_logic_app_url = (
            self.azure.get_logic_app_callback_url(
                subscription_id=request.subscription_id,
                resource_group_name=(
                    request.resource_group_name
                ),
                logic_app_name=(
                    request.notification_logic_app_name
                ),
                trigger_name=(
                    request.notification_logic_app_trigger_name
                ),
            )
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
            # HTTP endpoint
            #
            # This is intentionally empty for the first
            # Logic App because LA-VulnScan-01.5 does not
            # consume httpEndpointUrl.
            #
            # It will be replaced after LA-VulnScan-01.5
            # has successfully deployed.
            # ----------------------------------------------------

            "httpEndpointUrl": {
                "value": ""
            },

            # ----------------------------------------------------
            # Connections
            #
            # IMPORTANT:
            #
            # This becomes:
            #
            # "$connections": {
            #     "value": "[parameters('$connections')]"
            # }
            #
            # at the ARM deployment level.
            # ----------------------------------------------------

            "$connections": {
                "value": connections["arm_connections"]
            },
        }

        # ========================================================
        # 4. DEPLOY LA-VULNSCAN-01.5 FIRST
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
                subscription_id=(
                    request.subscription_id
                ),
                resource_group_name=(
                    request.resource_group_name
                ),
                location=request.location,
                vuln15_logic_app_name=(
                    request.vuln15_logic_app_name
                ),
                vuln01_logic_app_name=(
                    request.vuln01_logic_app_name
                ),
                notification_logic_app_name=(
                    request.notification_logic_app_name
                ),
                storage_account_name=(
                    request.storage_account_name
                ),
                vuln15_deployment_name=(
                    deployment15.get(
                        "deployment_name"
                    )
                ),
                vuln15_provisioning_state=(
                    state15
                ),
                table_connection_id=(
                    connections.get(
                        "table_connection_id"
                    )
                ),
                queue_connection_id=(
                    connections.get(
                        "queue_connection_id"
                    )
                ),
                sharepoint_connection_id=(
                    connections.get(
                        "sharepoint_connection_id"
                    )
                ),
                function_urls=(
                    VulnFunctionUrls(
                        **function_urls
                    )
                ),
                notification_logic_app_url=(
                    notification_logic_app_url
                ),
                arm_connections=(
                    connections.get(
                        "arm_connections"
                    )
                ),
            )

        # ========================================================
        # 5. GET LA-VULNSCAN-01.5/MANUAL CALLBACK URL
        # ========================================================

        logger.info(
            "Getting callback URL for %s/%s",
            request.vuln15_logic_app_name,
            request.vuln15_logic_app_trigger_name,
        )

        http_endpoint_url = (
            self.azure.get_logic_app_callback_url(
                subscription_id=request.subscription_id,
                resource_group_name=(
                    request.resource_group_name
                ),
                logic_app_name=(
                    request.vuln15_logic_app_name
                ),
                trigger_name=(
                    request.vuln15_logic_app_trigger_name
                ),
            )
        )

        logger.info(
            "Resolved httpEndpointUrl successfully."
        )

        # ========================================================
        # 6. PASS FIRST LOGIC APP URL TO SECOND LOGIC APP
        # ========================================================

        base_params["httpEndpointUrl"] = {
            "value": http_endpoint_url
        }

        # ========================================================
        # 7. DEPLOY LA-VULNSCAN-01
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

        success = (
            str(state01).lower()
            == "succeeded"
        )

        # ========================================================
        # RESPONSE
        # ========================================================

        return VulnDeploymentResponse(
            success=success,

            message=(
                "LA-VulnScan-01.5 and "
                "LA-VulnScan-01 deployed successfully."
                if success
                else deployment01.get(
                    "error",
                    "LA-VulnScan-01 deployment failed.",
                )
            ),

            subscription_id=(
                request.subscription_id
            ),

            resource_group_name=(
                request.resource_group_name
            ),

            location=request.location,

            vuln15_logic_app_name=(
                request.vuln15_logic_app_name
            ),

            vuln01_logic_app_name=(
                request.vuln01_logic_app_name
            ),

            notification_logic_app_name=(
                request.notification_logic_app_name
            ),

            storage_account_name=(
                request.storage_account_name
            ),

            vuln15_deployment_name=(
                deployment15.get(
                    "deployment_name"
                )
            ),

            vuln01_deployment_name=(
                deployment01.get(
                    "deployment_name"
                )
            ),

            vuln15_provisioning_state=(
                state15
            ),

            vuln01_provisioning_state=(
                state01
            ),

            table_connection_id=(
                connections.get(
                    "table_connection_id"
                )
            ),

            queue_connection_id=(
                connections.get(
                    "queue_connection_id"
                )
            ),

            sharepoint_connection_id=(
                connections.get(
                    "sharepoint_connection_id"
                )
            ),

            function_urls=(
                VulnFunctionUrls(
                    **function_urls
                )
            ),

            logic_app_urls=(
                VulnLogicAppUrls(
                    vuln01_5_logic_app_url=(
                        http_endpoint_url
                    ),
                    notification_logic_app_url=(
                        notification_logic_app_url
                    ),
                )
            ),

            http_endpoint_url=(
                http_endpoint_url
            ),

            notification_logic_app_url=(
                notification_logic_app_url
            ),

            arm_connections=(
                connections.get(
                    "arm_connections"
                )
            ),
        )