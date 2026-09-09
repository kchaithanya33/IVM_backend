import logging

from app.azure.reporting import ReportingAzureManager

from app.schemas.reporting import (
    ReportingDeploymentRequest,
    ReportingDeploymentResponse,
    ReportingFunctionUrls,
    ReportingLogicAppUrls,
)


logger = logging.getLogger(__name__)


class ReportingDeploymentService:
    """
    Service responsible for Reporting deployment.

    Deployment order:

        1. Resolve Azure Tables connection
        2. Resolve SharePoint connection
        3. Resolve Split Vulnerabilities Function URL
        4. Resolve Notification Logic App callback URL
        5. Deploy Reporting Logic App
    """

    def __init__(self) -> None:

        self.azure_manager = (
            ReportingAzureManager()
        )

    # ============================================================
    # DEPLOY REPORTING
    # ============================================================

    def deploy_reporting(
        self,
        request: ReportingDeploymentRequest,
    ) -> ReportingDeploymentResponse:

        # --------------------------------------------------------
        # Variables used for response/error handling
        # --------------------------------------------------------

        table_connection_id = None

        sharepoint_connection_id = None

        split_vulnerabilities_function_url = None

        notification_service_url = None

        deployment_name = None

        provisioning_state = None

        try:

            logger.info(
                "================================================"
            )

            logger.info(
                "Starting Reporting deployment."
            )

            logger.info(
                "Reporting Logic App: %s",
                request.reporting_logic_app_name,
            )

            logger.info(
                "================================================"
            )

            # ====================================================
            # 1. GET API CONNECTION IDS
            # ====================================================

            logger.info(
                "STEP 1: Resolving API connections."
            )

            connections = (
                self.azure_manager.get_connections(
                    subscription_id=(
                        request.subscription_id
                    ),
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    azure_tables_connection_name=(
                        request.azure_tables_connection_name
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

            sharepoint_connection_id = (
                connections.get(
                    "sharepoint_connection_id"
                )
            )

            logger.info(
                "Azure Tables connection resolved."
            )

            logger.info(
                "SharePoint connection resolved."
            )

            # ====================================================
            # 2. RESOLVE SPLIT VULNERABILITIES FUNCTION URL
            # ====================================================

            logger.info(
                "STEP 2: Resolving Split Vulnerabilities "
                "Function URL."
            )

            split_vulnerabilities_function_url = (
                self.azure_manager.get_function_url(
                    subscription_id=(
                        request.subscription_id
                    ),
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    function_app_name=(
                        request.function_app_name
                    ),
                    function_name=(
                        request.split_vulnerabilities_function_name
                    ),
                )
            )

            if not split_vulnerabilities_function_url:

                raise ValueError(
                    "Split Vulnerabilities Function URL "
                    "could not be resolved."
                )

            logger.info(
                "Split Vulnerabilities Function URL "
                "resolved successfully."
            )

            # ====================================================
            # 3. RESOLVE NOTIFICATION LOGIC APP CALLBACK
            # ====================================================

            logger.info(
                "STEP 3: Resolving Notification Logic App "
                "callback URL."
            )

            notification_service_url = (
                self.azure_manager
                .get_logic_app_callback_url(
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

            if not notification_service_url:

                raise ValueError(
                    "Notification Service callback URL "
                    "could not be resolved."
                )

            logger.info(
                "Notification Service callback URL "
                "resolved successfully."
            )

            # ====================================================
            # 4. DEPLOY REPORTING ARM TEMPLATE
            # ====================================================

            logger.info(
                "STEP 4: Deploying Reporting ARM template."
            )

            deployment = (
                self.azure_manager.deploy(
                    request=request,
                    connections=connections,
                    notification_service_url=(
                        notification_service_url
                    ),
                    split_vulnerabilities_function_url=(
                        split_vulnerabilities_function_url
                    ),
                )
            )

            deployment_name = (
                deployment.get(
                    "deployment_name"
                )
            )

            provisioning_state = (
                deployment.get(
                    "provisioning_state"
                )
            )

            # ====================================================
            # 5. CHECK DEPLOYMENT
            # ====================================================

            if provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = (
                    deployment.get(
                        "error",
                        "Reporting ARM deployment failed.",
                    )
                )

                logger.error(
                    "Reporting deployment failed: %s",
                    error_message,
                )

                return ReportingDeploymentResponse(
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

                    reporting_logic_app_name=(
                        request.reporting_logic_app_name
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

                    sharepoint_connection_id=(
                        sharepoint_connection_id
                    ),

                    function_urls=(
                        ReportingFunctionUrls(
                            split_vulnerabilities_function_url=(
                                split_vulnerabilities_function_url
                            )
                        )
                    ),

                    logic_app_urls=(
                        ReportingLogicAppUrls(
                            notification_service_url=(
                                notification_service_url
                            )
                        )
                    ),
                )

            # ====================================================
            # 6. SUCCESS
            # ====================================================

            logger.info(
                "================================================"
            )

            logger.info(
                "Reporting deployment completed successfully."
            )

            logger.info(
                "Reporting Logic App: %s",
                request.reporting_logic_app_name,
            )

            logger.info(
                "================================================"
            )

            return ReportingDeploymentResponse(
                success=True,

                message=(
                    "Reporting Logic App deployed "
                    "successfully."
                ),

                subscription_id=(
                    request.subscription_id
                ),

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                reporting_logic_app_name=(
                    request.reporting_logic_app_name
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

                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),

                function_urls=(
                    ReportingFunctionUrls(
                        split_vulnerabilities_function_url=(
                            split_vulnerabilities_function_url
                        )
                    )
                ),

                logic_app_urls=(
                    ReportingLogicAppUrls(
                        notification_service_url=(
                            notification_service_url
                        )
                    )
                ),
            )

        except Exception as exc:

            logger.exception(
                "Reporting deployment failed."
            )

            return ReportingDeploymentResponse(
                success=False,

                message=(
                    f"Reporting deployment failed: "
                    f"{str(exc)}"
                ),

                subscription_id=(
                    request.subscription_id
                ),

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                reporting_logic_app_name=(
                    request.reporting_logic_app_name
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

                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),

                function_urls=(
                    ReportingFunctionUrls(
                        split_vulnerabilities_function_url=(
                            split_vulnerabilities_function_url
                        )
                    )
                    if split_vulnerabilities_function_url
                    else None
                ),

                logic_app_urls=(
                    ReportingLogicAppUrls(
                        notification_service_url=(
                            notification_service_url
                        )
                    )
                    if notification_service_url
                    else None
                ),
            )