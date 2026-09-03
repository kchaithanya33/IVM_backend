
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
    Service responsible for Scoping deployment.

    Deployment order:

        1. Resolve API connections
        2. Resolve Function URLs
        3. Resolve Notification callback
        4. Resolve Completion callback
        5. Deploy Scoping-02
        6. Resolve Scoping-02 callback URL
        7. Deploy Scoping-00
        8. Deploy Scoping-01
        9. Pass Scoping-02 callback URL into Scoping-00/01
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
            # 3. RESOLVE NOTIFICATION CALLBACK
            # ====================================================

            notification_service_url = (
                self.azure_manager.get_logic_app_callback_url(
                    subscription_id=(
                        request.subscription_id
                    ),
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

            # ====================================================
            # 4. RESOLVE COMPLETION CALLBACK
            # ====================================================

            completion_logic_app_url = (
                self.azure_manager.get_logic_app_callback_url(
                    subscription_id=(
                        request.subscription_id
                    ),
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    logic_app_name=(
                        request.completion_logic_app_name
                    ),
                    trigger_name=(
                        request.completion_logic_app_trigger_name
                    ),
                )
            )

            # ====================================================
            # 5. DEPLOY SCOPING-02 FIRST
            # ====================================================

            logger.info(
                "================================================"
            )

            logger.info(
                "STEP 1: Deploying Scoping-02 first: %s",
                request.scoping02_logic_app_name,
            )

            logger.info(
                "================================================"
            )

            scoping02_deployment = (
                self.azure_manager.deploy(
                    request=request,
                    connections=connections,
                    function_urls=function_urls,
                    notification_service_url=(
                        notification_service_url
                    ),
                    completion_logic_app_url=(
                        completion_logic_app_url
                    ),
                    scoping02_logic_app_url=None,
                    stages={
                        "scoping02"
                    },
                )
            )

            scoping02_state = (
                scoping02_deployment.get(
                    "provisioning_state"
                )
            )

            scoping02_deployment_name = (
                scoping02_deployment.get(
                    "deployment_name"
                )
            )

            if scoping02_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = (
                    scoping02_deployment.get(
                        "error",
                        "Scoping-02 deployment failed.",
                    )
                )

                logger.error(
                    "Scoping-02 deployment failed: %s",
                    error_message,
                )

                return ScopingDeploymentResponse(
                    success=False,
                    message=str(error_message),

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
                        scoping02_deployment_name
                    ),

                    scoping02_deployment_name=(
                        scoping02_deployment_name
                    ),

                    scoping02_provisioning_state=(
                        scoping02_state or "Failed"
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
                            notification_service_url=(
                                notification_service_url
                            ),

                            completion_logic_app_url=(
                                completion_logic_app_url
                            ),

                            scoping02_logic_app_url=None,
                        )
                    ),
                )

            # ====================================================
            # 6. NOW GET SCOPING-02 CALLBACK URL
            # ====================================================

            logger.info(
                "Scoping-02 deployed successfully."
            )

            logger.info(
                "Resolving Scoping-02 callback URL..."
            )

            scoping02_logic_app_url = (
                self.azure_manager.get_logic_app_callback_url(
                    subscription_id=(
                        request.subscription_id
                    ),
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    logic_app_name=(
                        request.scoping02_logic_app_name
                    ),
                    trigger_name=(
                        request.scoping02_logic_app_trigger_name
                    ),
                )
            )

            if not scoping02_logic_app_url:

                raise ValueError(
                    "Scoping-02 callback URL could not "
                    "be resolved after deployment."
                )

            logger.info(
                "Scoping-02 callback URL resolved."
            )

            # ====================================================
            # 7. DEPLOY SCOPING-00 + SCOPING-01
            # ====================================================

            logger.info(
                "================================================"
            )

            logger.info(
                "STEP 2: Deploying Scoping-00 and Scoping-01."
            )

            logger.info(
                "Scoping-02 callback URL will be passed "
                "to the ARM template."
            )

            logger.info(
                "================================================"
            )

            remaining_deployment = (
                self.azure_manager.deploy(
                    request=request,
                    connections=connections,
                    function_urls=function_urls,
                    notification_service_url=(
                        notification_service_url
                    ),
                    completion_logic_app_url=(
                        completion_logic_app_url
                    ),
                    scoping02_logic_app_url=(
                        scoping02_logic_app_url
                    ),
                    stages={
                        "scoping00",
                        "scoping01",
                    },
                )
            )

            remaining_state = (
                remaining_deployment.get(
                    "provisioning_state"
                )
            )

            remaining_deployment_name = (
                remaining_deployment.get(
                    "deployment_name"
                )
            )

            # ====================================================
            # 8. CHECK SCOPING-00/01 DEPLOYMENT
            # ====================================================

            if remaining_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = (
                    remaining_deployment.get(
                        "error",
                        "Scoping-00/01 deployment failed.",
                    )
                )

                logger.error(
                    "Scoping-00/01 deployment failed: %s",
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
                        remaining_deployment_name
                    ),

                    scoping02_deployment_name=(
                        scoping02_deployment_name
                    ),

                    scoping00_01_deployment_name=(
                        remaining_deployment_name
                    ),

                    provisioning_state=(
                        remaining_state or "Failed"
                    ),

                    scoping02_provisioning_state=(
                        scoping02_state
                    ),

                    scoping00_01_provisioning_state=(
                        remaining_state
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
                            notification_service_url=(
                                notification_service_url
                            ),

                            completion_logic_app_url=(
                                completion_logic_app_url
                            ),

                            scoping02_logic_app_url=(
                                scoping02_logic_app_url
                            ),
                        )
                    ),
                )

            # ====================================================
            # 9. SUCCESS
            # ====================================================

            logger.info(
                "================================================"
            )

            logger.info(
                "Scoping deployment completed successfully."
            )

            logger.info(
                "Scoping-02 deployed first."
            )

            logger.info(
                "Scoping-02 callback URL resolved."
            )

            logger.info(
                "Scoping-00 and Scoping-01 deployed "
                "using Scoping-02 callback URL."
            )

            logger.info(
                "================================================"
            )

            return ScopingDeploymentResponse(
                success=True,

                message=(
                    "Scoping-02 deployed first, its callback "
                    "URL was resolved, and Scoping-00 and "
                    "Scoping-01 were deployed successfully."
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

                # Keep the final deployment as the main one.
                deployment_name=(
                    remaining_deployment_name
                ),

                scoping02_deployment_name=(
                    scoping02_deployment_name
                ),

                scoping00_01_deployment_name=(
                    remaining_deployment_name
                ),

                provisioning_state=(
                    remaining_state
                ),

                scoping02_provisioning_state=(
                    scoping02_state
                ),

                scoping00_01_provisioning_state=(
                    remaining_state
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
                        notification_service_url=(
                            notification_service_url
                        ),

                        completion_logic_app_url=(
                            completion_logic_app_url
                        ),

                        scoping02_logic_app_url=(
                            scoping02_logic_app_url
                        ),
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
