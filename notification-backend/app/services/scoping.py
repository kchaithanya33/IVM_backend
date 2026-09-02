
import logging
from typing import Any, Dict, Optional

from app.schemas.scoping import (
    ScopingDeploymentRequest,
    ScopingDeploymentResponse,
    ScopingFunctionUrls,
)

from app.azure.scoping import ScopingAzureManager


logger = logging.getLogger(__name__)


class ScopingDeploymentService:
    """
    Service layer for Scoping-00 and Scoping-01 deployment.

    Flow
    ----
        API Request
             |
             v
        Resolve API Connections
             |
             v
        Resolve Azure Function URLs
             |
             v
        Deploy scoping.json
             |
             v
        Return deployment response

    Important
    ---------
    CMDBReportURL is NOT part of the deployment request.

    It is generated later by Scoping-01 during workflow execution,
    so this service does not read request.cmdb_report_url.
    """

    def __init__(self) -> None:
        self.azure_manager = ScopingAzureManager()

    # ============================================================
    # DEPLOY SCOPING
    # ============================================================

    def deploy_scoping(
        self,
        request: ScopingDeploymentRequest,
    ) -> ScopingDeploymentResponse:

        logger.info(
            "Starting Scoping deployment: "
            "scoping00=%s scoping01=%s resource_group=%s "
            "function_app=%s storage_account=%s",
            request.logic_app_name,
            request.scoping01_logic_app_name,
            request.resource_group_name,
            request.function_app_name,
            request.storage_account_name,
        )

        # ========================================================
        # DEFAULT / RESULT VALUES
        # ========================================================

        table_connection_id: Optional[str] = None
        queue_connection_id: Optional[str] = None
        sharepoint_connection_id: Optional[str] = None

        function_urls: Dict[str, str] = {}

        deployment_name: Optional[str] = None
        provisioning_state: Optional[str] = None

        try:

            # ====================================================
            # STEP 1
            # RESOLVE API CONNECTIONS
            # ====================================================

            logger.info(
                "Step 1: Resolving Azure API connections."
            )

            connections = self.azure_manager.get_connections(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                table_connection_name=request.table_connection_name,
                queue_connection_name=request.queue_connection_name,
                sharepoint_connection_name=(
                    request.sharepoint_connection_name
                ),
            )

            # ----------------------------------------------------
            # Extract connection IDs
            # ----------------------------------------------------

            table_connection_id = connections.get(
                "table_connection_id"
            )

            queue_connection_id = connections.get(
                "queue_connection_id"
            )

            sharepoint_connection_id = connections.get(
                "sharepoint_connection_id"
            )

            # ----------------------------------------------------
            # Validate connections
            # ----------------------------------------------------

            if not table_connection_id:
                raise ValueError(
                    "Azure Tables connection could not be resolved."
                )

            if not queue_connection_id:
                raise ValueError(
                    "Azure Queues connection could not be resolved."
                )

            if not sharepoint_connection_id:
                raise ValueError(
                    "SharePoint connection could not be resolved."
                )

            logger.info(
                "Azure API connections resolved successfully."
            )

            logger.debug(
                "Table connection ID: %s",
                table_connection_id,
            )

            logger.debug(
                "Queue connection ID: %s",
                queue_connection_id,
            )

            logger.debug(
                "SharePoint connection ID: %s",
                sharepoint_connection_id,
            )

            # ====================================================
            # STEP 2
            # RESOLVE FUNCTION URLS
            # ====================================================

            logger.info(
                "Step 2: Resolving Azure Function URLs."
            )

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
                    call_azure_function_name=(
                        request.call_azure_function_name
                    ),
                )
            )

            if not isinstance(function_urls, dict):
                raise ValueError(
                    "Azure Function URL resolution returned "
                    "an invalid response."
                )

            # ----------------------------------------------------
            # Extract URLs
            # ----------------------------------------------------

            config_service_url = function_urls.get(
                "config_service_url"
            )

            business_day_hour_status_url = function_urls.get(
                "business_day_hour_status_url"
            )

            get_next_business_day_url = function_urls.get(
                "get_next_business_day_url"
            )

            call_azure_function_url = function_urls.get(
                "call_azure_function_url"
            )

            # ====================================================
            # VALIDATE FUNCTION URLS
            # ====================================================

            if not config_service_url:
                raise ValueError(
                    "Config Service Function URL "
                    "could not be resolved."
                )

            if not business_day_hour_status_url:
                raise ValueError(
                    "Business Day Hour Status Function URL "
                    "could not be resolved."
                )

            if not get_next_business_day_url:
                raise ValueError(
                    "Get Next Business Day Function URL "
                    "could not be resolved."
                )

            if not call_azure_function_url:
                raise ValueError(
                    "Call Azure Function URL "
                    "could not be resolved."
                )

            logger.info(
                "All required Azure Function URLs "
                "resolved successfully."
            )

            # ----------------------------------------------------
            # Safe URL logging
            # ----------------------------------------------------

            logger.debug(
                "Config Function URL: %s",
                config_service_url.split("?")[0],
            )

            logger.debug(
                "Business Day Hour Status URL: %s",
                business_day_hour_status_url.split("?")[0],
            )

            logger.debug(
                "Get Next Business Day URL: %s",
                get_next_business_day_url.split("?")[0],
            )

            logger.debug(
                "Call Azure Function URL: %s",
                call_azure_function_url.split("?")[0],
            )

            # ====================================================
            # STEP 3
            # DEPLOY ARM TEMPLATE
            # ====================================================

            logger.info(
                "Step 3: Deploying Scoping-00 and "
                "Scoping-01 ARM template."
            )

            deployment_result = self.azure_manager.deploy(
                request=request,
                connections=connections,
                function_urls=function_urls,
            )

            if not isinstance(deployment_result, dict):
                raise ValueError(
                    "Azure deployment returned an invalid response."
                )

            deployment_name = deployment_result.get(
                "deployment_name"
            )

            provisioning_state = deployment_result.get(
                "provisioning_state"
            )

            # ====================================================
            # STEP 4
            # CHECK DEPLOYMENT RESULT
            # ====================================================

            if provisioning_state in {
                "Succeeded",
                "succeeded",
            }:

                logger.info(
                    "Scoping deployment succeeded. "
                    "deployment=%s",
                    deployment_name,
                )

                # ------------------------------------------------
                # Build response Function URL model
                # ------------------------------------------------

                resolved_function_urls = ScopingFunctionUrls(
                    config_service_url=config_service_url,
                    business_day_hour_status_url=(
                        business_day_hour_status_url
                    ),
                    get_next_business_day_url=(
                        get_next_business_day_url
                    ),
                    call_azure_function_url=(
                        call_azure_function_url
                    ),
                )

                return ScopingDeploymentResponse(
                    success=True,

                    message=(
                        f"{request.logic_app_name} and "
                        f"{request.scoping01_logic_app_name} "
                        "deployment completed successfully."
                    ),

                    # --------------------------------------------
                    # AZURE
                    # --------------------------------------------

                    subscription_id=request.subscription_id,

                    resource_group_name=(
                        request.resource_group_name
                    ),

                    location=request.location,

                    # --------------------------------------------
                    # LOGIC APPS
                    # --------------------------------------------

                    logic_app_name=request.logic_app_name,

                    scoping01_logic_app_name=(
                        request.scoping01_logic_app_name
                    ),

                    # --------------------------------------------
                    # STORAGE
                    # --------------------------------------------

                    storage_account_name=(
                        request.storage_account_name
                    ),

                    # --------------------------------------------
                    # DEPLOYMENT
                    # --------------------------------------------

                    deployment_name=deployment_name,

                    provisioning_state=(
                        provisioning_state
                    ),

                    # --------------------------------------------
                    # API CONNECTIONS
                    # --------------------------------------------

                    table_connection_id=(
                        table_connection_id
                    ),

                    queue_connection_id=(
                        queue_connection_id
                    ),

                    sharepoint_connection_id=(
                        sharepoint_connection_id
                    ),

                    # --------------------------------------------
                    # FUNCTION URLS
                    # --------------------------------------------

                    function_urls=resolved_function_urls,
                )

            # ====================================================
            # STEP 5
            # DEPLOYMENT FAILED
            # ====================================================

            error_message = deployment_result.get(
                "error",
                "Unknown ARM deployment error.",
            )

            logger.error(
                "Scoping ARM deployment failed. "
                "deployment=%s state=%s error=%s",
                deployment_name,
                provisioning_state,
                error_message,
            )

            # ----------------------------------------------------
            # Build function URL response if available
            # ----------------------------------------------------

            resolved_function_urls: Optional[
                ScopingFunctionUrls
            ] = None

            if function_urls:

                resolved_function_urls = ScopingFunctionUrls(
                    config_service_url=function_urls.get(
                        "config_service_url"
                    ),
                    business_day_hour_status_url=(
                        function_urls.get(
                            "business_day_hour_status_url"
                        )
                    ),
                    get_next_business_day_url=(
                        function_urls.get(
                            "get_next_business_day_url"
                        )
                    ),
                    call_azure_function_url=(
                        function_urls.get(
                            "call_azure_function_url"
                        )
                    ),
                )

            return ScopingDeploymentResponse(
                success=False,

                message=(
                    f"Scoping deployment failed: "
                    f"{error_message}"
                ),

                # --------------------------------------------
                # AZURE
                # --------------------------------------------

                subscription_id=request.subscription_id,

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                # --------------------------------------------
                # LOGIC APPS
                # --------------------------------------------

                logic_app_name=request.logic_app_name,

                scoping01_logic_app_name=(
                    request.scoping01_logic_app_name
                ),

                # --------------------------------------------
                # STORAGE
                # --------------------------------------------

                storage_account_name=(
                    request.storage_account_name
                ),

                # --------------------------------------------
                # DEPLOYMENT
                # --------------------------------------------

                deployment_name=deployment_name,

                provisioning_state=(
                    provisioning_state
                ),

                # --------------------------------------------
                # API CONNECTIONS
                # --------------------------------------------

                table_connection_id=(
                    table_connection_id
                ),

                queue_connection_id=(
                    queue_connection_id
                ),

                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),

                # --------------------------------------------
                # FUNCTION URLS
                # --------------------------------------------

                function_urls=resolved_function_urls,
            )

        # ========================================================
        # UNEXPECTED ERROR
        # ========================================================

        except Exception as exc:

            logger.exception(
                "Scoping deployment failed unexpectedly."
            )

            # ----------------------------------------------------
            # Build partial function URL response
            # ----------------------------------------------------

            resolved_function_urls: Optional[
                ScopingFunctionUrls
            ] = None

            if function_urls:

                resolved_function_urls = ScopingFunctionUrls(
                    config_service_url=function_urls.get(
                        "config_service_url"
                    ),
                    business_day_hour_status_url=(
                        function_urls.get(
                            "business_day_hour_status_url"
                        )
                    ),
                    get_next_business_day_url=(
                        function_urls.get(
                            "get_next_business_day_url"
                        )
                    ),
                    call_azure_function_url=(
                        function_urls.get(
                            "call_azure_function_url"
                        )
                    ),
                )

            return ScopingDeploymentResponse(
                success=False,

                message=(
                    f"{request.logic_app_name} deployment failed: "
                    f"{str(exc)}"
                ),

                # --------------------------------------------
                # AZURE
                # --------------------------------------------

                subscription_id=request.subscription_id,

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                # --------------------------------------------
                # LOGIC APPS
                # --------------------------------------------

                logic_app_name=request.logic_app_name,

                scoping01_logic_app_name=(
                    request.scoping01_logic_app_name
                ),

                # --------------------------------------------
                # STORAGE
                # --------------------------------------------

                storage_account_name=(
                    request.storage_account_name
                ),

                # --------------------------------------------
                # DEPLOYMENT
                # --------------------------------------------

                deployment_name=deployment_name,

                provisioning_state=(
                    provisioning_state
                ),

                # --------------------------------------------
                # API CONNECTIONS
                # --------------------------------------------

                table_connection_id=(
                    table_connection_id
                ),

                queue_connection_id=(
                    queue_connection_id
                ),

                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),

                # --------------------------------------------
                # FUNCTION URLS
                # --------------------------------------------

                function_urls=resolved_function_urls,
            )
