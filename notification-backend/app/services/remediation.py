import logging

from app.azure.remediation import RemediationAzureManager

from app.schemas.remediation import (
    RemediationDeploymentRequest,
    RemediationDeploymentResponse,
    RemediationFunctionUrls,
)


logger = logging.getLogger(__name__)


# ============================================================
# REMEDIATION DEPLOYMENT SERVICE
# ============================================================

class RemediationDeploymentService:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self) -> None:

        self.azure_manager = RemediationAzureManager()

    # ========================================================
    # DEPLOY REMEDIATION
    # ========================================================

    def deploy_remediation(
        self,
        request: RemediationDeploymentRequest,
    ) -> RemediationDeploymentResponse:

        logger.info(
            "Starting Remediation deployment: "
            "logic_app=%s",
            request.logic_app_name,
        )

        try:

            # =================================================
            # STEP 1
            # Get Azure API connections
            # =================================================

            logger.info(
                "Resolving Azure API connections"
            )

            connections = (
                self.azure_manager.get_connections(
                    subscription_id=request.subscription_id,
                    resource_group_name=
                        request.resource_group_name,
                    table_connection_name=
                        request.table_connection_name,
                    queue_connection_name=
                        request.queue_connection_name,
                )
            )

            # =================================================
            # STEP 2
            # Get Function URLs dynamically
            # =================================================

            logger.info(
                "Resolving Remediation Function URLs"
            )

            function_urls = (
                self.azure_manager.get_function_urls(
                    subscription_id=
                        request.subscription_id,
                    resource_group_name=
                        request.resource_group_name,

                    config_function_app_name=
                        request.config_function_app_name,
                    config_function_name=
                        request.config_function_name,

                    qualys_asset_group_function_app_name=
                        request.qualys_asset_group_function_app_name,
                    qualys_asset_group_function_name=
                        request.qualys_asset_group_function_name,

                    qualys_scan_function_app_name=
                        request.qualys_scan_function_app_name,
                    qualys_scan_function_name=
                        request.qualys_scan_function_name,
                )
            )

            # =================================================
            # STEP 3
            # Deploy LA-Remediation-02
            # =================================================

            logger.info(
                "Deploying Logic App: %s",
                request.logic_app_name,
            )

            deployment_result = (
                self.azure_manager.deploy(
                    request=request,
                    connections=connections,
                    function_urls=function_urls,
                )
            )

            # =================================================
            # STEP 4
            # Handle deployment failure
            # =================================================

            if not deployment_result.get("success"):

                return RemediationDeploymentResponse(
                    success=False,

                    message=(
                        "Remediation Logic App deployment failed: "
                        + deployment_result.get(
                            "error",
                            "Unknown deployment error",
                        )
                    ),

                    subscription_id=
                        request.subscription_id,

                    resource_group_name=
                        request.resource_group_name,

                    location=
                        request.location,

                    logic_app_name=
                        request.logic_app_name,

                    storage_account_name=
                        request.storage_account_name,

                    deployment_name=
                        deployment_result.get(
                            "deployment_name"
                        ),

                    provisioning_state=
                        deployment_result.get(
                            "provisioning_state"
                        ),

                    table_connection_id=
                        connections.get(
                            "table_connection_id"
                        ),

                    queue_connection_id=
                        connections.get(
                            "queue_connection_id"
                        ),

                    function_urls=
                        RemediationFunctionUrls(
                            **function_urls
                        ),
                )

            # =================================================
            # STEP 5
            # Success
            # =================================================

            return RemediationDeploymentResponse(
                success=True,

                message=(
                    "LA-Remediation-02 deployed successfully"
                ),

                subscription_id=
                    request.subscription_id,

                resource_group_name=
                    request.resource_group_name,

                location=
                    request.location,

                logic_app_name=
                    request.logic_app_name,

                storage_account_name=
                    request.storage_account_name,

                deployment_name=
                    deployment_result.get(
                        "deployment_name"
                    ),

                provisioning_state=
                    deployment_result.get(
                        "provisioning_state"
                    ),

                table_connection_id=
                    connections.get(
                        "table_connection_id"
                    ),

                queue_connection_id=
                    connections.get(
                        "queue_connection_id"
                    ),

                function_urls=
                    RemediationFunctionUrls(
                        **function_urls
                    ),
            )

        # =====================================================
        # GENERAL ERROR
        # =====================================================

        except Exception as exc:

            logger.exception(
                "Remediation deployment failed"
            )

            return RemediationDeploymentResponse(
                success=False,

                message=str(exc),

                subscription_id=
                    request.subscription_id,

                resource_group_name=
                    request.resource_group_name,

                location=
                    request.location,

                logic_app_name=
                    request.logic_app_name,

                storage_account_name=
                    request.storage_account_name,
            )