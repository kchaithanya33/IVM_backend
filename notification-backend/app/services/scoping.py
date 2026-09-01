import logging

from app.schemas.scoping import (
    ScopingDeploymentRequest,
    ScopingDeploymentResponse,
)

from app.azure.scoping import ScopingAzureManager


logger = logging.getLogger(__name__)


class ScopingDeploymentService:
    """
    Service layer for Scoping-00 deployment.

    Flow:

        API Request
             |
             v
        Resolve API connections
             |
             v
        Resolve Function URLs
             |
             v
        Build ARM parameters
             |
             v
        Deploy Logic App
             |
             v
        API Response
    """

    def __init__(self) -> None:

        self.azure_manager = ScopingAzureManager()

    # ========================================================
    # DEPLOY SCOPING
    # ========================================================

    def deploy_scoping(
        self,
        request: ScopingDeploymentRequest,
    ) -> ScopingDeploymentResponse:

        logger.info(
            "Starting Scoping-00 deployment: "
            "logic_app=%s resource_group=%s",
            request.logic_app_name,
            request.resource_group_name,
        )

        try:

            # ==================================================
            # STEP 1
            # Resolve Azure API connections
            # ==================================================

            connections = (
                self.azure_manager.get_connections(
                    subscription_id=request.subscription_id,
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    table_connection_name=(
                        request.table_connection_name
                    ),
                    queue_connection_name=(
                        request.queue_connection_name
                    ),
                )
            )

            table_connection_id = (
                connections.get("table_connection_id")
            )

            queue_connection_id = (
                connections.get("queue_connection_id")
            )

            logger.info(
                "Resolved connections: "
                "table=%s queue=%s",
                table_connection_id,
                queue_connection_id,
            )

            # ==================================================
            # STEP 2
            # Resolve Function URLs dynamically
            # ==================================================

            function_urls = (
                self.azure_manager.get_function_urls(
                    subscription_id=request.subscription_id,
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    function_app_name=(
                        request.function_app_name
                    ),
                    config_function_name=(
                        request.config_function_name
                    ),
                    business_day_hour_status_function_name=(
                        request.business_day_hour_status_function_name
                    ),
                    get_next_business_day_function_name=(
                        request.get_next_business_day_function_name
                    ),
                )
            )

            config_service_url = (
                function_urls["config_service_url"]
            )

            business_day_hour_status_url = (
                function_urls[
                    "business_day_hour_status_url"
                ]
            )

            get_next_business_day_url = (
                function_urls[
                    "get_next_business_day_url"
                ]
            )

            logger.info(
                "Function URLs resolved successfully."
            )

            # ==================================================
            # STEP 3
            # Deploy ARM template
            # ==================================================

            deployment_result = (
                self.azure_manager.deploy(
                    request=request,
                    connections=connections,
                    function_urls=function_urls,
                )
            )

            provisioning_state = (
                deployment_result.get(
                    "provisioning_state"
                )
            )

            deployment_name = (
                deployment_result.get(
                    "deployment_name"
                )
            )

            # ==================================================
            # STEP 4
            # Successful deployment
            # ==================================================

            if provisioning_state in {
                "Succeeded",
                "succeeded",
            }:

                logger.info(
                    "Scoping-00 deployment succeeded: %s",
                    deployment_name,
                )

                return ScopingDeploymentResponse(

                    success=True,

                    message=(
                        f"{request.logic_app_name} deployment "
                        f"completed successfully."
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

                    storage_account_name=(
                        request.storage_account_name
                    ),

                    table_connection_id=(
                        table_connection_id
                    ),

                    queue_connection_id=(
                        queue_connection_id
                    ),

                    config_service_url=(
                        config_service_url
                    ),

                    business_day_hour_status_url=(
                        business_day_hour_status_url
                    ),

                    get_next_business_day_url=(
                        get_next_business_day_url
                    ),

                    deployment_name=(
                        deployment_name
                    ),

                    provisioning_state=(
                        provisioning_state
                    ),
                )

            # ==================================================
            # STEP 5
            # ARM deployment failed
            # ==================================================

            error_message = (
                deployment_result.get(
                    "error",
                    "Unknown ARM deployment error.",
                )
            )

            logger.error(
                "Scoping-00 deployment failed: %s",
                error_message,
            )

            return ScopingDeploymentResponse(

                success=False,

                message=(
                    f"{request.logic_app_name} deployment failed: "
                    f"{error_message}"
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

                storage_account_name=(
                    request.storage_account_name
                ),

                table_connection_id=(
                    table_connection_id
                ),

                queue_connection_id=(
                    queue_connection_id
                ),

                config_service_url=(
                    config_service_url
                ),

                business_day_hour_status_url=(
                    business_day_hour_status_url
                ),

                get_next_business_day_url=(
                    get_next_business_day_url
                ),

                deployment_name=(
                    deployment_name
                ),

                provisioning_state=(
                    provisioning_state
                ),
            )

        except Exception as exc:

            logger.exception(
                "Scoping-00 deployment failed unexpectedly."
            )

            return ScopingDeploymentResponse(

                success=False,

                message=(
                    f"{request.logic_app_name} deployment failed: "
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

                storage_account_name=(
                    request.storage_account_name
                ),
            )