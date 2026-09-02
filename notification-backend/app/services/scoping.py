

import logging

from app.azure.scoping import ScopingAzureManager
from app.schemas.scoping import (
    ScopingDeploymentRequest,
    ScopingDeploymentResponse,
    ScopingFunctionUrls,
    ScopingLogicAppUrls,
)


logger = logging.getLogger(__name__)


class ScopingDeploymentService:
    """
    Service responsible for the complete Scoping deployment flow.

    Flow:

        Frontend
            |
            v
        ScopingDeploymentRequest
            |
            v
        Get API connection IDs
            |
            v
        Resolve Function URLs
            |
            v
        Resolve Notification callback URL
            |
            v
        Resolve Completion callback URL
            |
            v
        Deploy ARM template
            |
            v
        ScopingDeploymentResponse
    """

    def __init__(self) -> None:

        self.azure_manager = (
            ScopingAzureManager()
        )

    # ============================================================
    # DEPLOY SCOPING
    # ============================================================

    def deploy_scoping(
        self,
        request: ScopingDeploymentRequest,
    ) -> ScopingDeploymentResponse:

        try:

            logger.info(
                "Starting Scoping deployment: "
                "logic_app=%s scoping01=%s scoping02=%s",
                request.logic_app_name,
                request.scoping01_logic_app_name,
                request.scoping02_logic_app_name,
            )

            # ====================================================
            # 1. GET API CONNECTION IDS
            # ====================================================

            connections = (
                self.azure_manager.get_connections(
                    subscription_id=(
                        request.subscription_id
                    ),
                    resource_group_name=(
                        request.resource_group_name
                    ),
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
            )

            table_connection_id = (
                connections.get(
                    "table_connection_id"
                )
            )

            queue_connection_id = (
                connections.get(
                    "queue_connection_id"
                )
            )

            sharepoint_connection_id = (
                connections.get(
                    "sharepoint_connection_id"
                )
            )

            # ====================================================
            # 2. RESOLVE FUNCTION URLS
            #
            # Function App name + function names are supplied
            # by frontend.
            #
            # Backend discovers:
            #
            #   hostname
            #   route
            #   function key
            #
            # and constructs the complete URL.
            # ====================================================

            function_urls = (
                self.azure_manager.get_function_urls(
                    subscription_id=(
                        request.subscription_id
                    ),
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    function_app_name=(
                        request.function_app_name
                    ),

                    # Existing functions
                    config_function_name=(
                        request.config_function_name
                    ),
                    business_day_hour_status_function_name=(
                        request.business_day_hour_status_function_name
                    ),
                    get_next_business_day_function_name=(
                        request.get_next_business_day_function_name
                    ),
                    call_azure_function_name=(
                        request.call_azure_function_name
                    ),

                    # Scoping-02 functions
                    process_asset_data_function_name=(
                        request.process_asset_data_function_name
                    ),
                    create_asset_groups_function_name=(
                        request.create_asset_groups_function_name
                    ),
                    error_processor_function_name=(
                        request.error_processor_function_name
                    ),
                    check_working_hours_function_name=(
                        request.check_working_hours_function_name
                    ),
                )
            )

            # ====================================================
            # 3. RESOLVE LOGIC APP CALLBACK URLS
            # ====================================================

            logic_app_urls = (
                self.azure_manager.get_logic_app_urls(
                    subscription_id=(
                        request.subscription_id
                    ),
                    resource_group_name=(
                        request.resource_group_name
                    ),

                    notification_logic_app_name=(
                        request.notification_logic_app_name
                    ),

                    notification_logic_app_action_name=(
                        request.notification_logic_app_trigger_name
                    ),

                    completion_logic_app_name=(
                        request.completion_logic_app_name
                    ),

                    completion_logic_app_action_name=(
                        request.completion_logic_app_trigger_name
                    ),
                )
            )

            # ====================================================
            # 4. DEPLOY ARM TEMPLATE
            # ====================================================

            deployment_result = (
                self.azure_manager.deploy(
                    request=request,
                    connections=connections,
                    function_urls=function_urls,
                    logic_app_urls=logic_app_urls,
                )
            )

            deployment_name = (
                deployment_result.get(
                    "deployment_name"
                )
            )

            provisioning_state = (
                deployment_result.get(
                    "provisioning_state"
                )
            )

            # ====================================================
            # 5. DEPLOYMENT FAILED
            # ====================================================

            if provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = (
                    deployment_result.get(
                        "error",
                        "Scoping ARM deployment failed.",
                    )
                )

                logger.error(
                    "Scoping deployment failed: %s",
                    error_message,
                )

                return ScopingDeploymentResponse(
                    success=False,
                    message=str(
                        error_message
                    ),

                    subscription_id=(
                        request.subscription_id
                    ),

                    resource_group_name=(
                        request.resource_group_name
                    ),

                    location=request.location,

                    logic_app_name=(
                        request.logic_app_name
                    ),

                    scoping01_logic_app_name=(
                        request.scoping01_logic_app_name
                    ),

                    scoping02_logic_app_name=(
                        request.scoping02_logic_app_name
                    ),

                    storage_account_name=(
                        request.storage_account_name
                    ),

                    deployment_name=(
                        deployment_name
                    ),

                    provisioning_state=(
                        provisioning_state
                        or "Failed"
                    ),

                    table_connection_id=(
                        table_connection_id
                    ),

                    queue_connection_id=(
                        queue_connection_id
                    ),

                    sharepoint_connection_id=(
                        sharepoint_connection_id
                    ),

                    function_urls=(
                        ScopingFunctionUrls(
                            **function_urls
                        )
                    ),

                    logic_app_urls=(
                        ScopingLogicAppUrls(
                            **logic_app_urls
                        )
                    ),
                )

            # ====================================================
            # 6. SUCCESS
            # ====================================================

            logger.info(
                "Scoping deployment completed successfully: "
                "deployment=%s",
                deployment_name,
            )

            return ScopingDeploymentResponse(
                success=True,

                message=(
                    "Scoping-00, Scoping-01 and "
                    "Scoping-02 deployed successfully."
                ),

                subscription_id=(
                    request.subscription_id
                ),

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                logic_app_name=(
                    request.logic_app_name
                ),

                scoping01_logic_app_name=(
                    request.scoping01_logic_app_name
                ),

                scoping02_logic_app_name=(
                    request.scoping02_logic_app_name
                ),

                storage_account_name=(
                    request.storage_account_name
                ),

                deployment_name=(
                    deployment_name
                ),

                provisioning_state=(
                    provisioning_state
                ),

                table_connection_id=(
                    table_connection_id
                ),

                queue_connection_id=(
                    queue_connection_id
                ),

                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),

                function_urls=(
                    ScopingFunctionUrls(
                        **function_urls
                    )
                ),

                logic_app_urls=(
                    ScopingLogicAppUrls(
                        **logic_app_urls
                    )
                ),
            )

        except Exception as exc:

            logger.exception(
                "Scoping deployment failed."
            )

            return ScopingDeploymentResponse(
                success=False,

                message=(
                    f"Scoping deployment failed: "
                    f"{str(exc)}"
                ),

                subscription_id=(
                    request.subscription_id
                ),

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                logic_app_name=(
                    request.logic_app_name
                ),

                scoping01_logic_app_name=(
                    request.scoping01_logic_app_name
                ),

                scoping02_logic_app_name=(
                    request.scoping02_logic_app_name
                ),

                storage_account_name=(
                    request.storage_account_name
                ),
            )
