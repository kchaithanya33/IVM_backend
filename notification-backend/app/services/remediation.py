
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
            # Get Remediation-02 Function URLs
            #
            # Existing Remediation-02 logic remains unchanged.
            # =================================================

            logger.info(
                "Resolving Remediation-02 Function URLs"
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
            # Deploy LA-Remediation-02 FIRST
            #
            # Existing Remediation-02 deployment is untouched.
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
            # Handle Remediation-02 deployment failure
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
            # Get Remediation-02 callback URL
            #
            # IMPORTANT:
            # This happens only after 02 succeeds.
            # =================================================

            logger.info(
                "Resolving Remediation-02 callback URL"
            )

            callback_uri_02 = (
                self.azure_manager.get_logic_app_callback_url(
                    subscription_id=
                        request.subscription_id,

                    resource_group_name=
                        request.resource_group_name,

                    logic_app_name=
                        request.logic_app_name,

                    trigger_name=
                        "When_a_HTTP_request_is_received",
                )
            )

            logger.info(
                "Remediation-02 callback URL resolved"
            )

            # =================================================
            # STEP 6
            # Resolve Remediation-01 Function URLs
            #
            # These are dynamically resolved from:
            # Function App + Function Name
            # =================================================

            logger.info(
                "Resolving Remediation-01 Function URLs"
            )

            remediation_01_function_urls = (
                self.azure_manager
                .get_remediation_01_function_urls(
                    subscription_id=
                        request.subscription_id,

                    resource_group_name=
                        request.resource_group_name,

                    excel_processing_function_app_name=
                        request.excel_processing_function_app_name,

                    excel_processing_function_name=
                        request.excel_processing_function_name,

                    qualys_qid_option_profile_function_app_name=
                        request.qualys_qid_option_profile_function_app_name,

                    qualys_qid_option_profile_function_name=
                        request.qualys_qid_option_profile_function_name,

                    dfn_file_content_function_app_name=
                        request.dfn_file_content_function_app_name,

                    dfn_file_content_function_name=
                        request.dfn_file_content_function_name,

                    cmdb_ip_extractor_function_app_name=
                        request.cmdb_ip_extractor_function_app_name,

                    cmdb_ip_extractor_function_name=
                        request.cmdb_ip_extractor_function_name,

                    all_ip_qid_extractor_function_app_name=
                        request.all_ip_qid_extractor_function_app_name,

                    all_ip_qid_extractor_function_name=
                        request.all_ip_qid_extractor_function_name,
                )
            )

            # =================================================
            # STEP 7
            # MERGE FUNCTION URLS
            #
            # IMPORTANT:
            #
            # Remediation-02 provides:
            #
            #   config_service_url
            #   qualys_asset_group_creation_function_url
            #   qualys_scan_function_url
            #
            # Remediation-01 provides:
            #
            #   excel_processing_function_url
            #   qualys_qid_option_profile_url
            #   dfn_file_content_function_url
            #   cmdb_ip_extractor_function_url
            #   all_ip_qid_extractor_function_url
            #
            # Keep them together exactly like the Scoping pattern.
            # =================================================

            all_function_urls = {
                **function_urls,
                **remediation_01_function_urls,
            }

            logger.info(
                "Remediation Function URLs resolved successfully"
            )

            logger.info(
                "Resolved Function URL keys: %s",
                sorted(all_function_urls.keys()),
            )

            # =================================================
            # STEP 8
            # Resolve Remediation-01 callback URLs
            #
            # 1. Remediation Scan callback + SAS
            # 2. Notification Service callback
            # =================================================

            logger.info(
                "Resolving Remediation-01 callback URLs"
            )

            remediation_01_callback_urls = (
                self.azure_manager
                .get_remediation_01_callback_urls(
                    subscription_id=
                        request.subscription_id,

                    resource_group_name=
                        request.resource_group_name,

                    remediation_scan_logic_app_name=
                        request.remediation_scan_logic_app_name,

                    remediation_scan_trigger_name=
                        request.remediation_scan_trigger_name,

                    notification_service_logic_app_name=
                        request.notification_service_logic_app_name,

                    notification_service_trigger_name=
                        request.notification_service_trigger_name,
                )
            )

            # =================================================
            # STEP 9
            # Deploy LA-Remediation-01
            #
            # IMPORTANT:
            #
            # Pass ALL function URLs, not only the 01 URLs.
            #
            # This means:
            #
            # all_function_urls
            #
            # contains both 02 + 01 function URLs.
            # =================================================

            logger.info(
                "Deploying Logic App: %s",
                request.remediation_01_logic_app_name,
            )

            remediation_01_result = (
                self.azure_manager.deploy_remediation_01(
                    request=request,

                    connections=connections,

                    function_urls=
                        all_function_urls,

                    callback_urls=
                        remediation_01_callback_urls,

                    callback_uri_02=
                        callback_uri_02,
                )
            )

            # =================================================
            # STEP 10
            # Handle Remediation-01 deployment failure
            # =================================================

            if not remediation_01_result.get("success"):

                return RemediationDeploymentResponse(
                    success=False,

                    message=(
                        "LA-Remediation-02 deployed successfully, "
                        "but LA-Remediation-01 deployment failed: "
                        + remediation_01_result.get(
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

                    remediation_01_logic_app_name=
                        request.remediation_01_logic_app_name,

                    storage_account_name=
                        request.storage_account_name,

                    deployment_name=
                        remediation_01_result.get(
                            "deployment_name"
                        ),

                    provisioning_state=
                        remediation_01_result.get(
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
                            **all_function_urls
                        ),

                    remediation_scan_url=
                        remediation_01_callback_urls.get(
                            "remediation_scan_url"
                        ),

                    remediation_sas_token=
                        remediation_01_callback_urls.get(
                            "remediation_sas_token"
                        ),

                    notification_service_url=
                        remediation_01_callback_urls.get(
                            "notification_service_url"
                        ),

                    callback_uri_02=
                        callback_uri_02,
                )

            # =================================================
            # STEP 11
            # Resolve Remediation-0.5 Function URLs
            #
            # Function App + Function Name are supplied in the
            # request and the Azure manager resolves the URLs.
            # =================================================

            logger.info(
                "Resolving Remediation-0.5 Function URLs"
            )

            remediation_05_function_urls = (
                self.azure_manager
                .get_remediation_05_function_urls(
                    subscription_id=
                        request.subscription_id,

                    resource_group_name=
                        request.resource_group_name,

                    business_days_function_app_name=
                        request.business_days_function_app_name,

                    business_days_function_name=
                        request.business_days_function_name,

                    get_next_business_day_function_app_name=
                        request.get_next_business_day_function_app_name,

                    get_next_business_day_function_name=
                        request.get_next_business_day_function_name,
                )
            )

            # =================================================
            # STEP 12
            # Resolve Remediation-0.5 Logic App callback URL
            #
            # Logic App name + trigger name are supplied in the
            # request and the Azure manager resolves the URL.
            # =================================================

            logger.info(
                "Resolving Remediation-0.5 Logic App callback URL"
            )

            business_day_logic_app_url = (
                self.azure_manager
                .get_remediation_05_callback_url(
                    subscription_id=
                        request.subscription_id,

                    resource_group_name=
                        request.resource_group_name,

                    business_day_logic_app_name=
                        request.business_day_logic_app_name,

                    business_day_logic_app_trigger_name=
                        request.business_day_logic_app_trigger_name,
                )
            )

            # =================================================
            # STEP 13
            # Deploy LA-Remediation-0.5
            #
            # Existing Remediation-02 and Remediation-01
            # deployment logic remains unchanged.
            # =================================================

            logger.info(
                "Deploying Logic App: LA-Remediation-0.5"
            )

            remediation_05_result = (
                self.azure_manager.deploy_remediation_05(
                    request=request,

                    connections=connections,

                    function_urls=
                        remediation_05_function_urls,

                    business_day_logic_app_url=
                        business_day_logic_app_url,
                )
            )

            # =================================================
            # STEP 14
            # Handle Remediation-0.5 deployment failure
            # =================================================

            if not remediation_05_result.get("success"):

                return RemediationDeploymentResponse(
                    success=False,

                    message=(
                        "LA-Remediation-02 and "
                        "LA-Remediation-01 deployed successfully, "
                        "but LA-Remediation-0.5 deployment failed: "
                        + remediation_05_result.get(
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

                    remediation_01_logic_app_name=
                        request.remediation_01_logic_app_name,

                    storage_account_name=
                        request.storage_account_name,

                    deployment_name=
                        remediation_05_result.get(
                            "deployment_name"
                        ),

                    provisioning_state=
                        remediation_05_result.get(
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
                            **{
                                **all_function_urls,
                                **remediation_05_function_urls,
                            }
                        ),

                    remediation_scan_url=
                        remediation_01_callback_urls.get(
                            "remediation_scan_url"
                        ),

                    remediation_sas_token=
                        remediation_01_callback_urls.get(
                            "remediation_sas_token"
                        ),

                    notification_service_url=
                        remediation_01_callback_urls.get(
                            "notification_service_url"
                        ),

                    callback_uri_02=
                        callback_uri_02,

                    business_day_logic_app_url=
                        business_day_logic_app_url,
                )

            # =================================================
            # STEP 15
            # SUCCESS
            # =================================================

            logger.info(
                "LA-Remediation-02, LA-Remediation-01 and "
                "LA-Remediation-0.5 deployed successfully"
            )

            return RemediationDeploymentResponse(
                success=True,

                message=(
                    "LA-Remediation-02, "
                    "LA-Remediation-01 and "
                    "LA-Remediation-0.5 deployed successfully"
                ),

                subscription_id=
                    request.subscription_id,

                resource_group_name=
                    request.resource_group_name,

                location=
                    request.location,

                logic_app_name=
                    request.logic_app_name,

                remediation_01_logic_app_name=
                    request.remediation_01_logic_app_name,

                storage_account_name=
                    request.storage_account_name,

                deployment_name=
                    remediation_05_result.get(
                        "deployment_name"
                    ),

                provisioning_state=
                    remediation_05_result.get(
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
                        **{
                            **all_function_urls,
                            **remediation_05_function_urls,
                        }
                    ),

                remediation_scan_url=
                    remediation_01_callback_urls.get(
                        "remediation_scan_url"
                    ),

                remediation_sas_token=
                    remediation_01_callback_urls.get(
                        "remediation_sas_token"
                    ),

                notification_service_url=
                    remediation_01_callback_urls.get(
                        "notification_service_url"
                    ),

                callback_uri_02=
                    callback_uri_02,

                business_day_logic_app_url=
                    business_day_logic_app_url,
            )


            logger.info(
                "LA-Remediation-02 and LA-Remediation-01 "
                "deployed successfully"
            )

            return RemediationDeploymentResponse(
                success=True,

                message=(
                    "LA-Remediation-02 and "
                    "LA-Remediation-01 deployed successfully"
                ),

                subscription_id=
                    request.subscription_id,

                resource_group_name=
                    request.resource_group_name,

                location=
                    request.location,

                logic_app_name=
                    request.logic_app_name,

                remediation_01_logic_app_name=
                    request.remediation_01_logic_app_name,

                storage_account_name=
                    request.storage_account_name,

                deployment_name=
                    remediation_01_result.get(
                        "deployment_name"
                    ),

                provisioning_state=
                    remediation_01_result.get(
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
                        **all_function_urls
                    ),

                remediation_scan_url=
                    remediation_01_callback_urls.get(
                        "remediation_scan_url"
                    ),

                remediation_sas_token=
                    remediation_01_callback_urls.get(
                        "remediation_sas_token"
                    ),

                notification_service_url=
                    remediation_01_callback_urls.get(
                        "notification_service_url"
                    ),

                callback_uri_02=
                    callback_uri_02,
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

                remediation_01_logic_app_name=
                    request.remediation_01_logic_app_name,

                storage_account_name=
                    request.storage_account_name,
            )
