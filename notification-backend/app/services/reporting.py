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
        3. Resolve Azure Queue connection
        4. Resolve Split Vulnerabilities Function URL
        5. Resolve After Scoping Triaging Function URL
        6. Resolve Triaging Validator Function URL
        7. Resolve Notification Logic App callback URL
        8. Resolve Completion Logic App callback URL
        9. Extract completionUrl and completionSasToken
       10. Deploy Reporting 04 ONLY
       11. Resolve Reporting 04 callback URL
       12. Deploy Reporting 03 ONLY
       13. Resolve Reporting 03 callback URL
       14. Resolve Reporting 02 Function URLs
       15. Resolve Completion Notification Logic App callback URL
       16. Deploy Reporting 02 ONLY
       17. Resolve Reporting 02 callback URL
       18. Resolve Reporting 1.5 Function URLs
       19. Deploy Reporting 1.5 ONLY
       20. Resolve Reporting 1.5 callback URL
       21. Resolve Reporting 01 Function URLs
       22. Deploy Reporting 01 ONLY
       23. Return all dynamically resolved values

    IMPORTANT:

        callbackUrl:
            Reporting 04 callback URL.
            Used by Reporting 03.

        callbackUri02:
            Reporting 03 callback URL.
            Used by Reporting 02.

        callbackUri1.5:
            Reporting 02 callback URL.
            Used by Reporting 1.5.

        reportingPart2LogicAppUrl:
            Reporting 1.5 callback URL.
            Used by Reporting 01.

        completionUrl:
            Existing Completion Logic App callback URL
            without query parameters.

        completionSasToken:
            'sig' value extracted from Existing Completion
            Logic App callback.

        completion_notification_LogicAppUrl:
            Separate Completion Notification Logic App
            callback URL.
    """

    def __init__(self) -> None:
        self.azure_manager = ReportingAzureManager()

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
        queue_connection_id = None

        # Reporting 04 / Reporting 03 Function URLs
        split_vulnerabilities_function_url = None
        after_scoping_triaging_url = None
        triaging_validator_url = None

        # Reporting 02 Function URLs
        data_merging_function_url = None
        new_vulnerabilities_function_url = None
        servicenow_api_url = None
        config_service_url = None

        # Reporting 1.5 Function URLs
        check_qualys_report_url = None
        download_qualys_report_url = None
        get_dfn_report_url = None

        # Reporting 01 Function URLs
        cmdb_reporting_ip_function_url = None
        qualys_launch_report_function_url = None

        # Logic App URLs
        notification_service_url = None

        completion_url = None
        completion_sas_token = None
        completion_notification_logic_app_url = None

        # Callback URLs
        callback_url = None
        callback_uri_02 = None
        reporting_02_callback_url = None

        # Reporting 1.5 callback.
        # This becomes reportingPart2LogicAppUrl for Reporting 01.
        reporting_1_5_callback_url = None

        # Deployment information
        deployment_name = None
        provisioning_state = None

        reporting_03_deployment_name = None
        reporting_03_provisioning_state = None

        reporting_02_deployment_name = None
        reporting_02_provisioning_state = None

        reporting_1_5_deployment_name = None
        reporting_1_5_provisioning_state = None

        reporting_01_deployment_name = None
        reporting_01_provisioning_state = None

        try:

            logger.info(
                "================================================"
            )

            logger.info(
                "Starting Reporting deployment."
            )

            logger.info(
                "Reporting 04 Logic App: %s",
                request.reporting_logic_app_name,
            )

            logger.info(
                "Reporting 03 Logic App: %s",
                request.reporting_03_logic_app_name,
            )

            logger.info(
                "Reporting 02 Logic App: %s",
                request.reporting_02_logic_app_name,
            )

            logger.info(
                "Reporting 1.5 Logic App: %s",
                request.reporting_1_5_logic_app_name,
            )

            logger.info(
                "Reporting 01 Logic App: %s",
                request.reporting_01_logic_app_name,
            )

            logger.info(
                "Reporting deployment flow: "
                "04 -> 03 -> 02 -> 1.5 -> 01"
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

            connections = self.azure_manager.get_connections(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                azure_tables_connection_name=(
                    request.azure_tables_connection_name
                ),
                sharepoint_connection_name=(
                    request.sharepoint_connection_name
                ),
                azure_queue_connection_name=(
                    request.azure_queue_connection_name
                ),
            )

            table_connection_id = connections.get(
                "table_connection_id"
            )

            sharepoint_connection_id = connections.get(
                "sharepoint_connection_id"
            )

            queue_connection_id = connections.get(
                "queue_connection_id"
            )

            logger.info(
                "Azure Tables connection resolved."
            )

            logger.info(
                "SharePoint connection resolved."
            )

            logger.info(
                "Azure Queue connection resolved."
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
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=request.function_app_name,
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
            # 3. RESOLVE AFTER SCOPING TRIAGING FUNCTION URL
            # ====================================================

            if (
                request.after_scoping_triaging_function_app_name
                and request.after_scoping_triaging_function_name
            ):

                logger.info(
                    "STEP 3: Resolving After Scoping Triaging "
                    "Function URL."
                )

                after_scoping_triaging_url = (
                    self.azure_manager.get_function_url(
                        subscription_id=request.subscription_id,
                        resource_group_name=request.resource_group_name,
                        function_app_name=(
                            request.after_scoping_triaging_function_app_name
                        ),
                        function_name=(
                            request.after_scoping_triaging_function_name
                        ),
                    )
                )

                if not after_scoping_triaging_url:
                    raise ValueError(
                        "After Scoping Triaging Function URL "
                        "could not be resolved."
                    )

                logger.info(
                    "After Scoping Triaging Function URL "
                    "resolved successfully."
                )

            else:
                raise ValueError(
                    "After Scoping Triaging Function App "
                    "name and function name are required."
                )

            # ====================================================
            # 4. RESOLVE TRIAGING VALIDATOR FUNCTION URL
            # ====================================================

            if (
                request.triaging_validator_function_app_name
                and request.triaging_validator_function_name
            ):

                logger.info(
                    "STEP 4: Resolving Triaging Validator "
                    "Function URL."
                )

                triaging_validator_url = (
                    self.azure_manager.get_function_url(
                        subscription_id=request.subscription_id,
                        resource_group_name=request.resource_group_name,
                        function_app_name=(
                            request.triaging_validator_function_app_name
                        ),
                        function_name=(
                            request.triaging_validator_function_name
                        ),
                    )
                )

                if not triaging_validator_url:
                    raise ValueError(
                        "Triaging Validator Function URL "
                        "could not be resolved."
                    )

                logger.info(
                    "Triaging Validator Function URL "
                    "resolved successfully."
                )

            else:
                raise ValueError(
                    "Triaging Validator Function App "
                    "name and function name are required."
                )

            # ====================================================
            # 5. RESOLVE NOTIFICATION LOGIC APP CALLBACK
            # ====================================================

            logger.info(
                "STEP 5: Resolving Notification Logic App "
                "callback URL."
            )

            notification_service_url = (
                self.azure_manager.get_logic_app_callback_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
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
            # 6. RESOLVE COMPLETION LOGIC APP CALLBACK
            # ====================================================

            logger.info(
                "STEP 6: Resolving Completion Logic App "
                "callback URL and SAS token."
            )

            completion_details = (
                self.azure_manager.get_logic_app_callback_details(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    logic_app_name=(
                        request.completion_logic_app_name
                    ),
                    trigger_name=(
                        request.completion_logic_app_trigger_name
                    ),
                )
            )

            completion_url = completion_details.get(
                "completion_url"
            )

            completion_sas_token = completion_details.get(
                "completion_sas_token"
            )

            if not completion_url:
                raise ValueError(
                    "Completion Logic App URL "
                    "could not be resolved."
                )

            if not completion_sas_token:
                raise ValueError(
                    "Completion Logic App SAS token "
                    "could not be resolved."
                )

            logger.info(
                "Completion Logic App URL "
                "resolved successfully."
            )

            logger.info(
                "Completion Logic App SAS token "
                "resolved successfully."
            )

            # ====================================================
            # 7. DEPLOY REPORTING 04 ONLY
            # ====================================================

            logger.info(
                "STEP 7: Deploying Reporting 04 ONLY."
            )

            deployment = self.azure_manager.deploy(
                request=request,
                connections=connections,
                notification_service_url=(
                    notification_service_url
                ),
                split_vulnerabilities_function_url=(
                    split_vulnerabilities_function_url
                ),
            )

            deployment_name = deployment.get(
                "deployment_name"
            )

            provisioning_state = deployment.get(
                "provisioning_state"
            )

            # ====================================================
            # 8. CHECK REPORTING 04 DEPLOYMENT
            # ====================================================

            if provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = deployment.get(
                    "error",
                    "Reporting 04 ARM deployment failed.",
                )

                logger.error(
                    "Reporting 04 deployment failed: %s",
                    error_message,
                )

                return ReportingDeploymentResponse(
                    success=False,
                    message=str(error_message),
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    location=request.location,
                    reporting_logic_app_name=(
                        request.reporting_logic_app_name
                    ),
                    reporting_03_logic_app_name=(
                        request.reporting_03_logic_app_name
                    ),
                    reporting_02_logic_app_name=(
                        request.reporting_02_logic_app_name
                    ),
                    reporting_1_5_logic_app_name=(
                        request.reporting_1_5_logic_app_name
                    ),
                    reporting_01_logic_app_name=(
                        request.reporting_01_logic_app_name
                    ),
                    storage_account_name=(
                        request.storage_account_name
                    ),
                    deployment_name=deployment_name,
                    provisioning_state=(
                        provisioning_state or "Failed"
                    ),
                    reporting_03_deployment_name=None,
                    reporting_03_provisioning_state=None,
                    reporting_02_deployment_name=None,
                    reporting_02_provisioning_state=None,
                    reporting_1_5_deployment_name=None,
                    reporting_1_5_provisioning_state=None,
                    reporting_01_deployment_name=None,
                    reporting_01_provisioning_state=None,
                    table_connection_id=table_connection_id,
                    sharepoint_connection_id=(
                        sharepoint_connection_id
                    ),
                    queue_connection_id=queue_connection_id,
                    callback_url=None,
                    reporting_03_callback_url=None,
                    reporting_02_callback_url=None,
                    callback_uri_1_5=None,
                    function_urls=ReportingFunctionUrls(
                        split_vulnerabilities_function_url=(
                            split_vulnerabilities_function_url
                        ),
                        after_scoping_triaging_url=(
                            after_scoping_triaging_url
                        ),
                        triaging_validator_url=(
                            triaging_validator_url
                        ),
                        data_merging_function_url=(
                            data_merging_function_url
                        ),
                        new_vulnerabilities_function_url=(
                            new_vulnerabilities_function_url
                        ),
                        servicenow_api_url=servicenow_api_url,
                        config_service_url=config_service_url,
                        check_qualys_report_url=(
                            check_qualys_report_url
                        ),
                        download_qualys_report_url=(
                            download_qualys_report_url
                        ),
                        get_dfn_report_url=get_dfn_report_url,
                        cmdb_reporting_ip_function_url=(
                            cmdb_reporting_ip_function_url
                        ),
                        qualys_launch_report_function_url=(
                            qualys_launch_report_function_url
                        ),
                    ),
                    logic_app_urls=ReportingLogicAppUrls(
                        notification_service_url=(
                            notification_service_url
                        ),
                        completion_url=completion_url,
                        completion_sas_token=(
                            completion_sas_token
                        ),
                        completion_notification_logic_app_url=(
                            completion_notification_logic_app_url
                        ),
                        callback_uri_1_5=None,
                    ),
                    completion_url=completion_url,
                    completion_sas_token=completion_sas_token,
                    completion_notification_logic_app_url=(
                        completion_notification_logic_app_url
                    ),
                )

            # ====================================================
            # 9. RESOLVE REPORTING 04 CALLBACK URL
            # ====================================================

            logger.info(
                "STEP 9: Resolving Reporting 04 "
                "callback URL."
            )

            callback_url = (
                self.azure_manager.get_reporting_callback_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    reporting_logic_app_name=(
                        request.reporting_logic_app_name
                    ),
                )
            )

            if not callback_url:
                raise ValueError(
                    "Reporting 04 callback URL "
                    "could not be resolved."
                )

            logger.info(
                "Reporting 04 callback URL "
                "resolved successfully."
            )

            # ====================================================
            # 10. DEPLOY REPORTING 03 ONLY
            # ====================================================

            logger.info(
                "STEP 10: Deploying Reporting 03 ONLY."
            )

            reporting_03_deployment = (
                self.azure_manager.deploy_reporting_03(
                    request=request,
                    connections=connections,
                    notification_service_url=(
                        notification_service_url
                    ),
                    callback_url=callback_url,
                    completion_url=completion_url,
                    completion_sas_token=(
                        completion_sas_token
                    ),
                    after_scoping_triaging_url=(
                        after_scoping_triaging_url
                    ),
                    triaging_validator_url=(
                        triaging_validator_url
                    ),
                )
            )

            reporting_03_deployment_name = (
                reporting_03_deployment.get(
                    "deployment_name"
                )
            )

            reporting_03_provisioning_state = (
                reporting_03_deployment.get(
                    "provisioning_state"
                )
            )

            # ====================================================
            # 11. CHECK REPORTING 03 DEPLOYMENT
            # ====================================================

            if reporting_03_provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = (
                    reporting_03_deployment.get(
                        "error",
                        "Reporting 03 ARM deployment failed.",
                    )
                )

                logger.error(
                    "Reporting 03 deployment failed: %s",
                    error_message,
                )

                return ReportingDeploymentResponse(
                    success=False,
                    message=(
                        "Reporting 04 deployed successfully, "
                        "but Reporting 03 deployment failed: "
                        f"{error_message}"
                    ),
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    location=request.location,
                    reporting_logic_app_name=(
                        request.reporting_logic_app_name
                    ),
                    reporting_03_logic_app_name=(
                        request.reporting_03_logic_app_name
                    ),
                    reporting_02_logic_app_name=(
                        request.reporting_02_logic_app_name
                    ),
                    reporting_1_5_logic_app_name=(
                        request.reporting_1_5_logic_app_name
                    ),
                    reporting_01_logic_app_name=(
                        request.reporting_01_logic_app_name
                    ),
                    storage_account_name=(
                        request.storage_account_name
                    ),
                    deployment_name=deployment_name,
                    provisioning_state=provisioning_state,
                    reporting_03_deployment_name=(
                        reporting_03_deployment_name
                    ),
                    reporting_03_provisioning_state=(
                        reporting_03_provisioning_state
                    ),
                    reporting_02_deployment_name=None,
                    reporting_02_provisioning_state=None,
                    reporting_1_5_deployment_name=None,
                    reporting_1_5_provisioning_state=None,
                    reporting_01_deployment_name=None,
                    reporting_01_provisioning_state=None,
                    table_connection_id=table_connection_id,
                    sharepoint_connection_id=(
                        sharepoint_connection_id
                    ),
                    queue_connection_id=queue_connection_id,
                    callback_url=callback_url,
                    reporting_03_callback_url=None,
                    reporting_02_callback_url=None,
                    callback_uri_1_5=None,
                    function_urls=ReportingFunctionUrls(
                        split_vulnerabilities_function_url=(
                            split_vulnerabilities_function_url
                        ),
                        after_scoping_triaging_url=(
                            after_scoping_triaging_url
                        ),
                        triaging_validator_url=(
                            triaging_validator_url
                        ),
                        data_merging_function_url=(
                            data_merging_function_url
                        ),
                        new_vulnerabilities_function_url=(
                            new_vulnerabilities_function_url
                        ),
                        servicenow_api_url=servicenow_api_url,
                        config_service_url=config_service_url,
                        check_qualys_report_url=(
                            check_qualys_report_url
                        ),
                        download_qualys_report_url=(
                            download_qualys_report_url
                        ),
                        get_dfn_report_url=get_dfn_report_url,
                        cmdb_reporting_ip_function_url=(
                            cmdb_reporting_ip_function_url
                        ),
                        qualys_launch_report_function_url=(
                            qualys_launch_report_function_url
                        ),
                    ),
                    logic_app_urls=ReportingLogicAppUrls(
                        notification_service_url=(
                            notification_service_url
                        ),
                        completion_url=completion_url,
                        completion_sas_token=(
                            completion_sas_token
                        ),
                        completion_notification_logic_app_url=(
                            completion_notification_logic_app_url
                        ),
                        callback_uri_1_5=None,
                    ),
                    completion_url=completion_url,
                    completion_sas_token=completion_sas_token,
                    completion_notification_logic_app_url=(
                        completion_notification_logic_app_url
                    ),
                )

            # ====================================================
            # 12. RESOLVE REPORTING 03 CALLBACK URL
            #
            # This URL becomes callbackUri02 for Reporting 02.
            # ====================================================

            logger.info(
                "STEP 12: Resolving Reporting 03 "
                "callback URL for Reporting 02."
            )

            callback_uri_02 = (
                self.azure_manager.get_reporting_callback_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    reporting_logic_app_name=(
                        request.reporting_03_logic_app_name
                    ),
                )
            )

            if not callback_uri_02:
                raise ValueError(
                    "Reporting 03 callback URL "
                    "could not be resolved for Reporting 02."
                )

            logger.info(
                "Reporting 03 callback URL resolved "
                "successfully for Reporting 02."
            )

            # ====================================================
            # 13. RESOLVE REPORTING 02 FUNCTION URLS
            # ====================================================

            logger.info(
                "STEP 13: Resolving Reporting 02 "
                "Function URLs."
            )

            # ----------------------------------------------------
            # Data Merging Function
            # ----------------------------------------------------

            logger.info(
                "Resolving Data Merging Function URL."
            )

            data_merging_function_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.data_merging_function_app_name
                    ),
                    function_name=(
                        request.data_merging_function_name
                    ),
                )
            )

            if not data_merging_function_url:
                raise ValueError(
                    "Data Merging Function URL "
                    "could not be resolved."
                )

            logger.info(
                "Data Merging Function URL "
                "resolved successfully."
            )

            # ----------------------------------------------------
            # New Vulnerabilities Function
            # ----------------------------------------------------

            logger.info(
                "Resolving New Vulnerabilities Function URL."
            )

            new_vulnerabilities_function_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.new_vulnerabilities_function_app_name
                    ),
                    function_name=(
                        request.new_vulnerabilities_function_name
                    ),
                )
            )

            if not new_vulnerabilities_function_url:
                raise ValueError(
                    "New Vulnerabilities Function URL "
                    "could not be resolved."
                )

            logger.info(
                "New Vulnerabilities Function URL "
                "resolved successfully."
            )

            # ----------------------------------------------------
            # ServiceNow Function
            # ----------------------------------------------------

            logger.info(
                "Resolving ServiceNow Function URL."
            )

            servicenow_api_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.servicenow_function_app_name
                    ),
                    function_name=(
                        request.servicenow_function_name
                    ),
                )
            )

            if not servicenow_api_url:
                raise ValueError(
                    "ServiceNow Function URL "
                    "could not be resolved."
                )

            logger.info(
                "ServiceNow Function URL "
                "resolved successfully."
            )

            # ----------------------------------------------------
            # Config Service Function
            # ----------------------------------------------------

            logger.info(
                "Resolving Config Service Function URL."
            )

            config_service_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.config_service_function_app_name
                    ),
                    function_name=(
                        request.config_service_function_name
                    ),
                )
            )

            if not config_service_url:
                raise ValueError(
                    "Config Service Function URL "
                    "could not be resolved."
                )

            logger.info(
                "Config Service Function URL "
                "resolved successfully."
            )

            # ====================================================
            # 14. RESOLVE COMPLETION NOTIFICATION
            #     LOGIC APP CALLBACK URL
            # ====================================================

            logger.info(
                "STEP 14: Resolving Completion Notification "
                "Logic App callback URL."
            )

            completion_notification_logic_app_url = (
                self.azure_manager.get_logic_app_callback_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    logic_app_name=(
                        request.completion_notification_logic_app_name
                    ),
                    trigger_name=(
                        request.completion_notification_logic_app_trigger_name
                    ),
                )
            )

            if not completion_notification_logic_app_url:
                raise ValueError(
                    "Completion Notification Logic App "
                    "callback URL could not be resolved."
                )

            logger.info(
                "Completion Notification Logic App "
                "callback URL resolved successfully."
            )

            # ====================================================
            # 15. DEPLOY REPORTING 02 ONLY
            # ====================================================

            logger.info(
                "STEP 15: Deploying Reporting 02 ONLY."
            )

            reporting_02_deployment = (
                self.azure_manager.deploy_reporting_02(
                    request=request,
                    connections=connections,

                    data_merging_function_url=(
                        data_merging_function_url
                    ),

                    new_vulnerabilities_function_url=(
                        new_vulnerabilities_function_url
                    ),

                    servicenow_api_url=(
                        servicenow_api_url
                    ),

                    notification_service_url=(
                        notification_service_url
                    ),

                    config_service_url=(
                        config_service_url
                    ),

                    completion_notification_logic_app_url=(
                        completion_notification_logic_app_url
                    ),

                    callback_uri02=(
                        callback_uri_02
                    ),

                    completion_url=(
                        completion_url
                    ),
                )
            )

            reporting_02_deployment_name = (
                reporting_02_deployment.get(
                    "deployment_name"
                )
            )

            reporting_02_provisioning_state = (
                reporting_02_deployment.get(
                    "provisioning_state"
                )
            )

            # ====================================================
            # 16. CHECK REPORTING 02 DEPLOYMENT
            # ====================================================

            if reporting_02_provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = (
                    reporting_02_deployment.get(
                        "error",
                        "Reporting 02 ARM deployment failed.",
                    )
                )

                logger.error(
                    "Reporting 02 deployment failed: %s",
                    error_message,
                )

                return ReportingDeploymentResponse(
                    success=False,
                    message=(
                        "Reporting 04 and Reporting 03 deployed "
                        "successfully, but Reporting 02 deployment "
                        f"failed: {error_message}"
                    ),
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    location=request.location,
                    reporting_logic_app_name=(
                        request.reporting_logic_app_name
                    ),
                    reporting_03_logic_app_name=(
                        request.reporting_03_logic_app_name
                    ),
                    reporting_02_logic_app_name=(
                        request.reporting_02_logic_app_name
                    ),
                    reporting_1_5_logic_app_name=(
                        request.reporting_1_5_logic_app_name
                    ),
                    reporting_01_logic_app_name=(
                        request.reporting_01_logic_app_name
                    ),
                    storage_account_name=(
                        request.storage_account_name
                    ),
                    deployment_name=deployment_name,
                    provisioning_state=provisioning_state,
                    reporting_03_deployment_name=(
                        reporting_03_deployment_name
                    ),
                    reporting_03_provisioning_state=(
                        reporting_03_provisioning_state
                    ),
                    reporting_02_deployment_name=(
                        reporting_02_deployment_name
                    ),
                    reporting_02_provisioning_state=(
                        reporting_02_provisioning_state
                    ),
                    reporting_1_5_deployment_name=None,
                    reporting_1_5_provisioning_state=None,
                    reporting_01_deployment_name=None,
                    reporting_01_provisioning_state=None,
                    table_connection_id=table_connection_id,
                    sharepoint_connection_id=(
                        sharepoint_connection_id
                    ),
                    queue_connection_id=queue_connection_id,
                    callback_url=callback_url,
                    reporting_03_callback_url=callback_uri_02,
                    reporting_02_callback_url=None,
                    callback_uri_1_5=None,
                    function_urls=ReportingFunctionUrls(
                        split_vulnerabilities_function_url=(
                            split_vulnerabilities_function_url
                        ),
                        after_scoping_triaging_url=(
                            after_scoping_triaging_url
                        ),
                        triaging_validator_url=(
                            triaging_validator_url
                        ),
                        data_merging_function_url=(
                            data_merging_function_url
                        ),
                        new_vulnerabilities_function_url=(
                            new_vulnerabilities_function_url
                        ),
                        servicenow_api_url=servicenow_api_url,
                        config_service_url=config_service_url,
                        check_qualys_report_url=(
                            check_qualys_report_url
                        ),
                        download_qualys_report_url=(
                            download_qualys_report_url
                        ),
                        get_dfn_report_url=get_dfn_report_url,
                        cmdb_reporting_ip_function_url=(
                            cmdb_reporting_ip_function_url
                        ),
                        qualys_launch_report_function_url=(
                            qualys_launch_report_function_url
                        ),
                    ),
                    logic_app_urls=ReportingLogicAppUrls(
                        notification_service_url=(
                            notification_service_url
                        ),
                        completion_url=completion_url,
                        completion_sas_token=(
                            completion_sas_token
                        ),
                        completion_notification_logic_app_url=(
                            completion_notification_logic_app_url
                        ),
                        callback_uri_1_5=None,
                    ),
                    completion_url=completion_url,
                    completion_sas_token=completion_sas_token,
                    completion_notification_logic_app_url=(
                        completion_notification_logic_app_url
                    ),
                )

            # ====================================================
            # 17. RESOLVE REPORTING 02 CALLBACK URL
            #
            # This URL becomes callbackUri1.5 for Reporting 1.5.
            # ====================================================

            logger.info(
                "STEP 17: Resolving Reporting 02 "
                "callback URL for Reporting 1.5."
            )

            reporting_02_callback_url = (
                self.azure_manager.get_reporting_02_callback_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    reporting_02_logic_app_name=(
                        request.reporting_02_logic_app_name
                    ),
                )
            )

            if not reporting_02_callback_url:
                raise ValueError(
                    "Reporting 02 callback URL "
                    "could not be resolved for Reporting 1.5."
                )

            logger.info(
                "Reporting 02 callback URL resolved "
                "successfully for Reporting 1.5."
            )

            # ====================================================
            # 18. RESOLVE REPORTING 1.5 FUNCTION URLS
            # ====================================================

            logger.info(
                "STEP 18: Resolving Reporting 1.5 "
                "Function URLs."
            )

            # ----------------------------------------------------
            # Check Qualys Report Function
            # ----------------------------------------------------

            logger.info(
                "Resolving Check Qualys Report Function URL."
            )

            check_qualys_report_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.check_qualys_report_function_app_name
                    ),
                    function_name=(
                        request.check_qualys_report_function_name
                    ),
                )
            )

            if not check_qualys_report_url:
                raise ValueError(
                    "Check Qualys Report Function URL "
                    "could not be resolved."
                )

            logger.info(
                "Check Qualys Report Function URL "
                "resolved successfully."
            )

            # ----------------------------------------------------
            # Download Qualys Report Function
            # ----------------------------------------------------

            logger.info(
                "Resolving Download Qualys Report Function URL."
            )

            download_qualys_report_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.download_qualys_report_function_app_name
                    ),
                    function_name=(
                        request.download_qualys_report_function_name
                    ),
                )
            )

            if not download_qualys_report_url:
                raise ValueError(
                    "Download Qualys Report Function URL "
                    "could not be resolved."
                )

            logger.info(
                "Download Qualys Report Function URL "
                "resolved successfully."
            )

            # ----------------------------------------------------
            # Get DFN Report Function
            # ----------------------------------------------------

            logger.info(
                "Resolving Get DFN Report Function URL."
            )

            get_dfn_report_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.get_dfn_report_function_app_name
                    ),
                    function_name=(
                        request.get_dfn_report_function_name
                    ),
                )
            )

            if not get_dfn_report_url:
                raise ValueError(
                    "Get DFN Report Function URL "
                    "could not be resolved."
                )

            logger.info(
                "Get DFN Report Function URL "
                "resolved successfully."
            )

            # ====================================================
            # 19. DEPLOY REPORTING 1.5 ONLY
            # ====================================================

            logger.info(
                "STEP 19: Deploying Reporting 1.5 ONLY."
            )

            reporting_1_5_deployment = (
                self.azure_manager.deploy_reporting_1_5(
                    request=request,
                    connections=connections,

                    check_qualys_report_url=(
                        check_qualys_report_url
                    ),

                    download_qualys_report_url=(
                        download_qualys_report_url
                    ),

                    get_dfn_report_url=(
                        get_dfn_report_url
                    ),

                    callback_uri_1_5=(
                        reporting_02_callback_url
                    ),

                    notification_service_url=(
                        notification_service_url
                    ),

                    config_service_url=(
                        config_service_url
                    ),

                    completion_notification_logic_app_url=(
                        completion_notification_logic_app_url
                    ),
                )
            )

            reporting_1_5_deployment_name = (
                reporting_1_5_deployment.get(
                    "deployment_name"
                )
            )

            reporting_1_5_provisioning_state = (
                reporting_1_5_deployment.get(
                    "provisioning_state"
                )
            )

            # ====================================================
            # 20. CHECK REPORTING 1.5 DEPLOYMENT
            # ====================================================

            if reporting_1_5_provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = (
                    reporting_1_5_deployment.get(
                        "error",
                        "Reporting 1.5 ARM deployment failed.",
                    )
                )

                logger.error(
                    "Reporting 1.5 deployment failed: %s",
                    error_message,
                )

                return ReportingDeploymentResponse(
                    success=False,
                    message=(
                        "Reporting 04, Reporting 03 and Reporting 02 "
                        "deployed successfully, but Reporting 1.5 "
                        f"deployment failed: {error_message}"
                    ),
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    location=request.location,
                    reporting_logic_app_name=(
                        request.reporting_logic_app_name
                    ),
                    reporting_03_logic_app_name=(
                        request.reporting_03_logic_app_name
                    ),
                    reporting_02_logic_app_name=(
                        request.reporting_02_logic_app_name
                    ),
                    reporting_1_5_logic_app_name=(
                        request.reporting_1_5_logic_app_name
                    ),
                    reporting_01_logic_app_name=(
                        request.reporting_01_logic_app_name
                    ),
                    storage_account_name=(
                        request.storage_account_name
                    ),
                    deployment_name=deployment_name,
                    provisioning_state=provisioning_state,
                    reporting_03_deployment_name=(
                        reporting_03_deployment_name
                    ),
                    reporting_03_provisioning_state=(
                        reporting_03_provisioning_state
                    ),
                    reporting_02_deployment_name=(
                        reporting_02_deployment_name
                    ),
                    reporting_02_provisioning_state=(
                        reporting_02_provisioning_state
                    ),
                    reporting_1_5_deployment_name=(
                        reporting_1_5_deployment_name
                    ),
                    reporting_1_5_provisioning_state=(
                        reporting_1_5_provisioning_state
                    ),
                    reporting_01_deployment_name=None,
                    reporting_01_provisioning_state=None,
                    table_connection_id=table_connection_id,
                    sharepoint_connection_id=(
                        sharepoint_connection_id
                    ),
                    queue_connection_id=queue_connection_id,
                    callback_url=callback_url,
                    reporting_03_callback_url=callback_uri_02,
                    reporting_02_callback_url=(
                        reporting_02_callback_url
                    ),
                    callback_uri_1_5=None,
                    function_urls=ReportingFunctionUrls(
                        split_vulnerabilities_function_url=(
                            split_vulnerabilities_function_url
                        ),
                        after_scoping_triaging_url=(
                            after_scoping_triaging_url
                        ),
                        triaging_validator_url=(
                            triaging_validator_url
                        ),
                        data_merging_function_url=(
                            data_merging_function_url
                        ),
                        new_vulnerabilities_function_url=(
                            new_vulnerabilities_function_url
                        ),
                        servicenow_api_url=servicenow_api_url,
                        config_service_url=config_service_url,
                        check_qualys_report_url=(
                            check_qualys_report_url
                        ),
                        download_qualys_report_url=(
                            download_qualys_report_url
                        ),
                        get_dfn_report_url=get_dfn_report_url,
                        cmdb_reporting_ip_function_url=(
                            cmdb_reporting_ip_function_url
                        ),
                        qualys_launch_report_function_url=(
                            qualys_launch_report_function_url
                        ),
                    ),
                    logic_app_urls=ReportingLogicAppUrls(
                        notification_service_url=(
                            notification_service_url
                        ),
                        completion_url=completion_url,
                        completion_sas_token=(
                            completion_sas_token
                        ),
                        completion_notification_logic_app_url=(
                            completion_notification_logic_app_url
                        ),
                        callback_uri_1_5=None,
                    ),
                    completion_url=completion_url,
                    completion_sas_token=completion_sas_token,
                    completion_notification_logic_app_url=(
                        completion_notification_logic_app_url
                    ),
                )

            # ====================================================
            # 21. RESOLVE REPORTING 1.5 CALLBACK URL
            #
            # IMPORTANT:
            #
            # This is the callback URL of LA-reporting-1.5.
            # It is NOT the Reporting 02 callback URL.
            #
            # This value becomes:
            #
            #     reportingPart2LogicAppUrl
            #
            # for Reporting 01.
            # ====================================================

            logger.info(
                "STEP 21: Resolving Reporting 1.5 "
                "callback URL for Reporting 01."
            )

            reporting_1_5_callback_url = (
                self.azure_manager.get_reporting_1_5_callback_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    reporting_1_5_logic_app_name=(
                        request.reporting_1_5_logic_app_name
                    ),
                )
            )

            if not reporting_1_5_callback_url:
                raise ValueError(
                    "Reporting 1.5 callback URL "
                    "could not be resolved for Reporting 01."
                )

            logger.info(
                "Reporting 1.5 callback URL resolved "
                "successfully for Reporting 01."
            )

            # ====================================================
            # 22. RESOLVE REPORTING 01 FUNCTION URLS
            # ====================================================

            logger.info(
                "STEP 22: Resolving Reporting 01 "
                "Function URLs."
            )

            # ----------------------------------------------------
            # CMDB Reporting IP Function
            # ----------------------------------------------------

            if (
                not request.cmdb_reporting_ip_function_app_name
                or not request.cmdb_reporting_ip_function_name
            ):
                raise ValueError(
                    "CMDB Reporting IP Function App name and "
                    "function name are required."
                )

            logger.info(
                "Resolving CMDB Reporting IP Function URL."
            )

            cmdb_reporting_ip_function_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.cmdb_reporting_ip_function_app_name
                    ),
                    function_name=(
                        request.cmdb_reporting_ip_function_name
                    ),
                )
            )

            if not cmdb_reporting_ip_function_url:
                raise ValueError(
                    "CMDB Reporting IP Function URL "
                    "could not be resolved."
                )

            logger.info(
                "CMDB Reporting IP Function URL "
                "resolved successfully."
            )

            # ----------------------------------------------------
            # Qualys Launch Report Function
            # ----------------------------------------------------

            if (
                not request.qualys_launch_report_function_app_name
                or not request.qualys_launch_report_function_name
            ):
                raise ValueError(
                    "Qualys Launch Report Function App name and "
                    "function name are required."
                )

            logger.info(
                "Resolving Qualys Launch Report Function URL."
            )

            qualys_launch_report_function_url = (
                self.azure_manager.get_function_url(
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    function_app_name=(
                        request.qualys_launch_report_function_app_name
                    ),
                    function_name=(
                        request.qualys_launch_report_function_name
                    ),
                )
            )

            if not qualys_launch_report_function_url:
                raise ValueError(
                    "Qualys Launch Report Function URL "
                    "could not be resolved."
                )

            logger.info(
                "Qualys Launch Report Function URL "
                "resolved successfully."
            )

            # ====================================================
            # 23. DEPLOY REPORTING 01 ONLY
            # ====================================================

            logger.info(
                "STEP 23: Deploying Reporting 01 ONLY."
            )

            reporting_01_deployment = (
                self.azure_manager.deploy_reporting_01(
                    request=request,
                    connections=connections,

                    cmdb_reporting_ip_function_url=(
                        cmdb_reporting_ip_function_url
                    ),

                    qualys_launch_report_function_url=(
                        qualys_launch_report_function_url
                    ),

                    reporting_part2_logic_app_url=(
                        reporting_1_5_callback_url
                    ),
                )
            )

            reporting_01_deployment_name = (
                reporting_01_deployment.get(
                    "deployment_name"
                )
            )

            reporting_01_provisioning_state = (
                reporting_01_deployment.get(
                    "provisioning_state"
                )
            )

            # ====================================================
            # 24. CHECK REPORTING 01 DEPLOYMENT
            # ====================================================

            if reporting_01_provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = (
                    reporting_01_deployment.get(
                        "error",
                        "Reporting 01 ARM deployment failed.",
                    )
                )

                logger.error(
                    "Reporting 01 deployment failed: %s",
                    error_message,
                )

                return ReportingDeploymentResponse(
                    success=False,
                    message=(
                        "Reporting 04, Reporting 03, Reporting 02 "
                        "and Reporting 1.5 deployed successfully, "
                        "but Reporting 01 deployment failed: "
                        f"{error_message}"
                    ),
                    subscription_id=request.subscription_id,
                    resource_group_name=request.resource_group_name,
                    location=request.location,
                    reporting_logic_app_name=(
                        request.reporting_logic_app_name
                    ),
                    reporting_03_logic_app_name=(
                        request.reporting_03_logic_app_name
                    ),
                    reporting_02_logic_app_name=(
                        request.reporting_02_logic_app_name
                    ),
                    reporting_1_5_logic_app_name=(
                        request.reporting_1_5_logic_app_name
                    ),
                    reporting_01_logic_app_name=(
                        request.reporting_01_logic_app_name
                    ),
                    storage_account_name=(
                        request.storage_account_name
                    ),
                    deployment_name=deployment_name,
                    provisioning_state=provisioning_state,
                    reporting_03_deployment_name=(
                        reporting_03_deployment_name
                    ),
                    reporting_03_provisioning_state=(
                        reporting_03_provisioning_state
                    ),
                    reporting_02_deployment_name=(
                        reporting_02_deployment_name
                    ),
                    reporting_02_provisioning_state=(
                        reporting_02_provisioning_state
                    ),
                    reporting_1_5_deployment_name=(
                        reporting_1_5_deployment_name
                    ),
                    reporting_1_5_provisioning_state=(
                        reporting_1_5_provisioning_state
                    ),
                    reporting_01_deployment_name=(
                        reporting_01_deployment_name
                    ),
                    reporting_01_provisioning_state=(
                        reporting_01_provisioning_state
                    ),
                    table_connection_id=table_connection_id,
                    sharepoint_connection_id=(
                        sharepoint_connection_id
                    ),
                    queue_connection_id=queue_connection_id,
                    callback_url=callback_url,
                    reporting_03_callback_url=callback_uri_02,
                    reporting_02_callback_url=(
                        reporting_02_callback_url
                    ),
                    callback_uri_1_5=(
                        reporting_1_5_callback_url
                    ),
                    function_urls=ReportingFunctionUrls(
                        split_vulnerabilities_function_url=(
                            split_vulnerabilities_function_url
                        ),
                        after_scoping_triaging_url=(
                            after_scoping_triaging_url
                        ),
                        triaging_validator_url=(
                            triaging_validator_url
                        ),
                        data_merging_function_url=(
                            data_merging_function_url
                        ),
                        new_vulnerabilities_function_url=(
                            new_vulnerabilities_function_url
                        ),
                        servicenow_api_url=servicenow_api_url,
                        config_service_url=config_service_url,
                        check_qualys_report_url=(
                            check_qualys_report_url
                        ),
                        download_qualys_report_url=(
                            download_qualys_report_url
                        ),
                        get_dfn_report_url=get_dfn_report_url,
                        cmdb_reporting_ip_function_url=(
                            cmdb_reporting_ip_function_url
                        ),
                        qualys_launch_report_function_url=(
                            qualys_launch_report_function_url
                        ),
                    ),
                    logic_app_urls=ReportingLogicAppUrls(
                        notification_service_url=(
                            notification_service_url
                        ),
                        completion_url=completion_url,
                        completion_sas_token=(
                            completion_sas_token
                        ),
                        completion_notification_logic_app_url=(
                            completion_notification_logic_app_url
                        ),
                        callback_uri_1_5=(
                            reporting_1_5_callback_url
                        ),
                    ),
                    completion_url=completion_url,
                    completion_sas_token=completion_sas_token,
                    completion_notification_logic_app_url=(
                        completion_notification_logic_app_url
                    ),
                )

            # ====================================================
            # 25. SUCCESS
            # ====================================================

            logger.info(
                "================================================"
            )

            logger.info(
                "Reporting deployment completed successfully."
            )

            logger.info(
                "Reporting 04 Logic App: %s",
                request.reporting_logic_app_name,
            )

            logger.info(
                "Reporting 03 Logic App: %s",
                request.reporting_03_logic_app_name,
            )

            logger.info(
                "Reporting 02 Logic App: %s",
                request.reporting_02_logic_app_name,
            )

            logger.info(
                "Reporting 1.5 Logic App: %s",
                request.reporting_1_5_logic_app_name,
            )

            logger.info(
                "Reporting 01 Logic App: %s",
                request.reporting_01_logic_app_name,
            )

            logger.info(
                "Reporting 04 callback URL resolved."
            )

            logger.info(
                "Reporting 03 callback URL resolved "
                "for Reporting 02."
            )

            logger.info(
                "Reporting 02 callback URL resolved "
                "for Reporting 1.5."
            )

            logger.info(
                "Reporting 1.5 callback URL resolved "
                "for Reporting 01."
            )

            logger.info(
                "Data Merging Function URL resolved."
            )

            logger.info(
                "New Vulnerabilities Function URL resolved."
            )

            logger.info(
                "ServiceNow Function URL resolved."
            )

            logger.info(
                "Config Service Function URL resolved."
            )

            logger.info(
                "Check Qualys Report Function URL resolved."
            )

            logger.info(
                "Download Qualys Report Function URL resolved."
            )

            logger.info(
                "Get DFN Report Function URL resolved."
            )

            logger.info(
                "CMDB Reporting IP Function URL resolved."
            )

            logger.info(
                "Qualys Launch Report Function URL resolved."
            )

            logger.info(
                "Completion Logic App callback URL resolved."
            )

            logger.info(
                "Completion Logic App SAS token extracted."
            )

            logger.info(
                "Completion Notification Logic App "
                "callback URL resolved."
            )

            logger.info(
                "Reporting 03 deployed using Reporting 04 "
                "callback URL."
            )

            logger.info(
                "Reporting 02 deployed using Reporting 03 "
                "callback URL."
            )

            logger.info(
                "Reporting 1.5 deployed using Reporting 02 "
                "callback URL."
            )

            logger.info(
                "Reporting 01 deployed using Reporting 1.5 "
                "callback URL."
            )

            logger.info(
                "================================================"
            )

            return ReportingDeploymentResponse(
                success=True,

                message=(
                    "Reporting 04, Reporting 03, Reporting 02, "
                    "Reporting 1.5 and Reporting 01 Logic Apps "
                    "deployed successfully. Reporting 03 was "
                    "deployed using the dynamically resolved "
                    "Reporting 04 callback URL, Reporting 02 "
                    "was deployed using the dynamically resolved "
                    "Reporting 03 callback URL, Reporting 1.5 "
                    "was deployed using the dynamically resolved "
                    "Reporting 02 callback URL, and Reporting 01 "
                    "was deployed using the dynamically resolved "
                    "Reporting 1.5 callback URL."
                ),

                subscription_id=request.subscription_id,

                resource_group_name=request.resource_group_name,

                location=request.location,

                reporting_logic_app_name=(
                    request.reporting_logic_app_name
                ),

                reporting_03_logic_app_name=(
                    request.reporting_03_logic_app_name
                ),

                reporting_02_logic_app_name=(
                    request.reporting_02_logic_app_name
                ),

                reporting_1_5_logic_app_name=(
                    request.reporting_1_5_logic_app_name
                ),

                reporting_01_logic_app_name=(
                    request.reporting_01_logic_app_name
                ),

                storage_account_name=(
                    request.storage_account_name
                ),

                deployment_name=deployment_name,

                provisioning_state=provisioning_state,

                reporting_03_deployment_name=(
                    reporting_03_deployment_name
                ),

                reporting_03_provisioning_state=(
                    reporting_03_provisioning_state
                ),

                reporting_02_deployment_name=(
                    reporting_02_deployment_name
                ),

                reporting_02_provisioning_state=(
                    reporting_02_provisioning_state
                ),

                reporting_1_5_deployment_name=(
                    reporting_1_5_deployment_name
                ),

                reporting_1_5_provisioning_state=(
                    reporting_1_5_provisioning_state
                ),

                reporting_01_deployment_name=(
                    reporting_01_deployment_name
                ),

                reporting_01_provisioning_state=(
                    reporting_01_provisioning_state
                ),

                table_connection_id=table_connection_id,

                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),

                queue_connection_id=queue_connection_id,

                callback_url=callback_url,

                reporting_03_callback_url=(
                    callback_uri_02
                ),

                reporting_02_callback_url=(
                    reporting_02_callback_url
                ),

                # IMPORTANT:
                # This is now the Reporting 1.5 callback URL.
                # It is the URL passed to Reporting 01 as
                # reportingPart2LogicAppUrl.
                callback_uri_1_5=(
                    reporting_1_5_callback_url
                ),

                function_urls=ReportingFunctionUrls(
                    split_vulnerabilities_function_url=(
                        split_vulnerabilities_function_url
                    ),
                    after_scoping_triaging_url=(
                        after_scoping_triaging_url
                    ),
                    triaging_validator_url=(
                        triaging_validator_url
                    ),
                    data_merging_function_url=(
                        data_merging_function_url
                    ),
                    new_vulnerabilities_function_url=(
                        new_vulnerabilities_function_url
                    ),
                    servicenow_api_url=servicenow_api_url,
                    config_service_url=config_service_url,
                    check_qualys_report_url=(
                        check_qualys_report_url
                    ),
                    download_qualys_report_url=(
                        download_qualys_report_url
                    ),
                    get_dfn_report_url=(
                        get_dfn_report_url
                    ),
                    cmdb_reporting_ip_function_url=(
                        cmdb_reporting_ip_function_url
                    ),
                    qualys_launch_report_function_url=(
                        qualys_launch_report_function_url
                    ),
                ),

                logic_app_urls=ReportingLogicAppUrls(
                    notification_service_url=(
                        notification_service_url
                    ),
                    completion_url=completion_url,
                    completion_sas_token=(
                        completion_sas_token
                    ),
                    completion_notification_logic_app_url=(
                        completion_notification_logic_app_url
                    ),

                    # Reporting 1.5 callback URL.
                    # This is used by Reporting 01.
                    callback_uri_1_5=(
                        reporting_1_5_callback_url
                    ),
                ),

                completion_url=completion_url,

                completion_sas_token=(
                    completion_sas_token
                ),

                completion_notification_logic_app_url=(
                    completion_notification_logic_app_url
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

                subscription_id=request.subscription_id,

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                reporting_logic_app_name=(
                    request.reporting_logic_app_name
                ),

                reporting_03_logic_app_name=(
                    request.reporting_03_logic_app_name
                ),

                reporting_02_logic_app_name=(
                    request.reporting_02_logic_app_name
                ),

                reporting_1_5_logic_app_name=(
                    request.reporting_1_5_logic_app_name
                ),

                reporting_01_logic_app_name=(
                    request.reporting_01_logic_app_name
                ),

                storage_account_name=(
                    request.storage_account_name
                ),

                deployment_name=deployment_name,

                provisioning_state=provisioning_state,

                reporting_03_deployment_name=(
                    reporting_03_deployment_name
                ),

                reporting_03_provisioning_state=(
                    reporting_03_provisioning_state
                ),

                reporting_02_deployment_name=(
                    reporting_02_deployment_name
                ),

                reporting_02_provisioning_state=(
                    reporting_02_provisioning_state
                ),

                reporting_1_5_deployment_name=(
                    reporting_1_5_deployment_name
                ),

                reporting_1_5_provisioning_state=(
                    reporting_1_5_provisioning_state
                ),

                reporting_01_deployment_name=(
                    reporting_01_deployment_name
                ),

                reporting_01_provisioning_state=(
                    reporting_01_provisioning_state
                ),

                table_connection_id=(
                    table_connection_id
                ),

                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),

                queue_connection_id=(
                    queue_connection_id
                ),

                callback_url=callback_url,

                reporting_03_callback_url=(
                    callback_uri_02
                ),

                reporting_02_callback_url=(
                    reporting_02_callback_url
                ),

                callback_uri_1_5=(
                    reporting_1_5_callback_url
                ),

                function_urls=(
                    ReportingFunctionUrls(
                        split_vulnerabilities_function_url=(
                            split_vulnerabilities_function_url
                        ),
                        after_scoping_triaging_url=(
                            after_scoping_triaging_url
                        ),
                        triaging_validator_url=(
                            triaging_validator_url
                        ),
                        data_merging_function_url=(
                            data_merging_function_url
                        ),
                        new_vulnerabilities_function_url=(
                            new_vulnerabilities_function_url
                        ),
                        servicenow_api_url=(
                            servicenow_api_url
                        ),
                        config_service_url=(
                            config_service_url
                        ),
                        check_qualys_report_url=(
                            check_qualys_report_url
                        ),
                        download_qualys_report_url=(
                            download_qualys_report_url
                        ),
                        get_dfn_report_url=(
                            get_dfn_report_url
                        ),
                        cmdb_reporting_ip_function_url=(
                            cmdb_reporting_ip_function_url
                        ),
                        qualys_launch_report_function_url=(
                            qualys_launch_report_function_url
                        ),
                    )
                    if split_vulnerabilities_function_url
                    else None
                ),

                logic_app_urls=(
                    ReportingLogicAppUrls(
                        notification_service_url=(
                            notification_service_url
                        ),
                        completion_url=(
                            completion_url
                        ),
                        completion_sas_token=(
                            completion_sas_token
                        ),
                        completion_notification_logic_app_url=(
                            completion_notification_logic_app_url
                        ),
                        callback_uri_1_5=(
                            reporting_1_5_callback_url
                        ),
                    )
                    if notification_service_url
                    else None
                ),

                completion_url=(
                    completion_url
                ),

                completion_sas_token=(
                    completion_sas_token
                ),

                completion_notification_logic_app_url=(
                    completion_notification_logic_app_url
                ),
            )