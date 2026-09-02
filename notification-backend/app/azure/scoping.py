import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse

import requests

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient


logger = logging.getLogger(__name__)


class ScopingAzureManager:
    """
    Azure manager for Scoping-00 and Scoping-01 Logic App deployment.

    Responsibilities
    ----------------
    1. Resolve Azure Tables API connection.
    2. Resolve Azure Queues API connection.
    3. Resolve SharePoint API connection.
    4. Retrieve Azure Function metadata.
    5. Retrieve Azure Function keys.
    6. Build complete Azure Function URLs.
    7. Resolve all required Function URLs.
    8. Build ARM deployment parameters.
    9. Deploy arm/scoping.json.

    IMPORTANT
    ---------
    The ARM parameters passed here must match the parameters
    declared in arm/scoping.json.
    """

    MANAGEMENT_API_VERSION = "2022-03-01"
    ARM_MANAGEMENT_URL = "https://management.azure.com"

    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()

    # ============================================================
    # AUTHENTICATION
    # ============================================================

    def _get_management_token(self) -> str:
        """
        Get Azure Resource Manager access token.
        """

        token = self.credential.get_token(
            "https://management.azure.com/.default"
        )

        return token.token

    # ============================================================
    # MANAGEMENT REST REQUEST
    # ============================================================

    def _management_request(
        self,
        method: str,
        url: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute authenticated Azure Management REST request.
        """

        token = self._get_management_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        logger.debug(
            "Azure REST request: method=%s url=%s",
            method,
            url,
        )

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=body,
            timeout=60,
        )

        if not response.ok:

            logger.error(
                "Azure REST request failed: "
                "status=%s body=%s",
                response.status_code,
                response.text,
            )

            raise HttpResponseError(
                message=(
                    f"Azure REST request failed "
                    f"with status {response.status_code}: "
                    f"{response.text}"
                )
            )

        if not response.text:
            return {}

        try:
            return response.json()

        except ValueError as exc:

            raise ValueError(
                "Azure Management API returned "
                "a non-JSON response."
            ) from exc

    # ============================================================
    # API CONNECTIONS
    # ============================================================

    def get_connections(
        self,
        subscription_id: str,
        resource_group_name: str,
        table_connection_name: str,
        queue_connection_name: str,
        sharepoint_connection_name: str,
    ) -> Dict[str, str]:
        """
        Resolve Azure API connection resource IDs.

        Required connections:

            - Azure Tables
            - Azure Queues
            - SharePoint Online
        """

        logger.info(
            "Resolving API connections: "
            "table=%s queue=%s sharepoint=%s",
            table_connection_name,
            queue_connection_name,
            sharepoint_connection_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        table_connection_id: Optional[str] = None
        queue_connection_id: Optional[str] = None
        sharepoint_connection_id: Optional[str] = None

        connections = (
            resource_client.resources.list_by_resource_group(
                resource_group_name,
                filter="resourceType eq 'Microsoft.Web/connections'",
            )
        )

        for connection in connections:

            connection_name = connection.name

            logger.debug(
                "Found API connection: %s",
                connection_name,
            )

            if connection_name == table_connection_name:

                table_connection_id = connection.id

            elif connection_name == queue_connection_name:

                queue_connection_id = connection.id

            elif connection_name == sharepoint_connection_name:

                sharepoint_connection_id = connection.id

        # --------------------------------------------------------
        # Validate
        # --------------------------------------------------------

        if not table_connection_id:

            raise ValueError(
                "Azure Tables API connection was not found: "
                f"{table_connection_name}"
            )

        if not queue_connection_id:

            raise ValueError(
                "Azure Queues API connection was not found: "
                f"{queue_connection_name}"
            )

        if not sharepoint_connection_id:

            raise ValueError(
                "SharePoint API connection was not found: "
                f"{sharepoint_connection_name}"
            )

        logger.info(
            "Azure Tables connection resolved."
        )

        logger.info(
            "Azure Queues connection resolved."
        )

        logger.info(
            "SharePoint connection resolved."
        )

        return {
            "table_connection_id": table_connection_id,
            "queue_connection_id": queue_connection_id,
            "sharepoint_connection_id": sharepoint_connection_id,
        }

    # ============================================================
    # MANAGED API IDS
    # ============================================================

    def _get_managed_api_ids(
        self,
        subscription_id: str,
        location: str,
    ) -> Dict[str, str]:
        """
        Build managed API resource IDs used by $connections.
        """

        encoded_subscription = quote(
            subscription_id,
            safe="",
        )

        encoded_location = quote(
            location,
            safe="",
        )

        base = (
            f"/subscriptions/{encoded_subscription}"
            f"/providers/Microsoft.Web"
            f"/locations/{encoded_location}"
            f"/managedApis"
        )

        return {
            "table": (
                f"{base}/azuretables"
            ),
            "queue": (
                f"{base}/azurequeues"
            ),
            "sharepoint": (
                f"{base}/sharepointonline"
            ),
        }

    # ============================================================
    # FUNCTION RESOURCE
    # ============================================================

    def get_function_resource(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> Dict[str, Any]:
        """
        Retrieve Azure Function metadata.
        """

        url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/"
            f"{quote(subscription_id, safe='')}"
            f"/resourceGroups/"
            f"{quote(resource_group_name, safe='')}"
            f"/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name, safe='')}"
            f"/functions/"
            f"{quote(function_name, safe='')}"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        logger.info(
            "Retrieving Azure Function metadata: "
            "app=%s function=%s",
            function_app_name,
            function_name,
        )

        try:

            return self._management_request(
                method="GET",
                url=url,
            )

        except Exception as exc:

            raise ValueError(
                f"Unable to retrieve function "
                f"'{function_name}' from Function App "
                f"'{function_app_name}': {exc}"
            ) from exc

    # ============================================================
    # FUNCTION KEY
    # ============================================================

    def get_function_key(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> str:
        """
        Retrieve Azure Function key using listKeys.
        """

        url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/"
            f"{quote(subscription_id, safe='')}"
            f"/resourceGroups/"
            f"{quote(resource_group_name, safe='')}"
            f"/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name, safe='')}"
            f"/functions/"
            f"{quote(function_name, safe='')}"
            f"/listKeys"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        logger.info(
            "Retrieving Function key: "
            "app=%s function=%s",
            function_app_name,
            function_name,
        )

        try:

            result = self._management_request(
                method="POST",
                url=url,
                body={},
            )

        except Exception as exc:

            raise ValueError(
                f"Unable to retrieve function keys for "
                f"function '{function_name}' in Function App "
                f"'{function_app_name}': {exc}"
            ) from exc

        if not isinstance(result, dict):

            raise ValueError(
                f"Unexpected function key response for "
                f"'{function_name}'."
            )

        keys = result.get("keys")

        if isinstance(keys, dict):

            default_key = keys.get("default")

            if default_key:
                return str(default_key)

            for value in keys.values():

                if value:
                    return str(value)

        default_key = result.get("default")

        if default_key:
            return str(default_key)

        raise ValueError(
            f"No function key was found for function "
            f"'{function_name}' in Function App "
            f"'{function_app_name}'."
        )

    # ============================================================
    # FUNCTION URL
    # ============================================================

    def get_function_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> str:
        """
        Build a complete Azure Function URL including the
        Function access key.
        """

        function_resource = self.get_function_resource(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=function_name,
        )

        properties = function_resource.get(
            "properties",
            {},
        )

        if not isinstance(properties, dict):
            properties = {}

        # --------------------------------------------------------
        # Function route
        # --------------------------------------------------------

        route = properties.get(
            "invokeUrlTemplate"
        )

        if not route:

            route = properties.get(
                "invoke_url_template"
            )

        if not route:

            config = properties.get(
                "config"
            )

            if isinstance(config, dict):

                route = config.get(
                    "route"
                )

        if not route:

            route = f"/api/{function_name}"

        route = str(route)

        # --------------------------------------------------------
        # Function App hostname
        # --------------------------------------------------------

        site_url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/"
            f"{quote(subscription_id, safe='')}"
            f"/resourceGroups/"
            f"{quote(resource_group_name, safe='')}"
            f"/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name, safe='')}"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        site_resource = self._management_request(
            method="GET",
            url=site_url,
        )

        site_properties = site_resource.get(
            "properties",
            {},
        )

        hostname: Optional[str] = None

        if isinstance(site_properties, dict):

            hostname = site_properties.get(
                "defaultHostName"
            )

        if not hostname:

            hostname = (
                f"{function_app_name}.azurewebsites.net"
            )

        # --------------------------------------------------------
        # Normalize route
        # --------------------------------------------------------

        if (
            route.startswith("http://")
            or route.startswith("https://")
        ):

            parsed = urlparse(route)

            route = parsed.path

            if parsed.query:

                route = (
                    f"{route}?{parsed.query}"
                )

        if not route.startswith("/"):
            route = "/" + route

        if not route.startswith("/api/"):

            route = "/api" + route

        # --------------------------------------------------------
        # Function key
        # --------------------------------------------------------

        function_key = self.get_function_key(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=function_name,
        )

        separator = (
            "&"
            if "?" in route
            else "?"
        )

        return (
            f"https://{hostname}"
            f"{route}"
            f"{separator}"
            f"code={quote(function_key, safe='')}"
        )

    # ============================================================
    # ALL FUNCTION URLS
    # ============================================================

    def get_function_urls(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        config_function_name: str,
        business_day_hour_status_function_name: str,
        get_next_business_day_function_name: str,
        call_azure_function_name: str,
    ) -> Dict[str, str]:
        """
        Resolve all Function URLs required by Scoping.

        Returns:

            config_service_url
            business_day_hour_status_url
            get_next_business_day_url
            call_azure_function_url
        """

        logger.info(
            "Resolving Function URLs from Function App: %s",
            function_app_name,
        )

        # --------------------------------------------------------
        # Config Function
        # --------------------------------------------------------

        config_service_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=config_function_name,
        )

        # --------------------------------------------------------
        # Business Day / Hour Function
        # --------------------------------------------------------

        business_day_hour_status_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=business_day_hour_status_function_name,
        )

        # --------------------------------------------------------
        # Next Business Day Function
        # --------------------------------------------------------

        get_next_business_day_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=get_next_business_day_function_name,
        )

        # --------------------------------------------------------
        # Process Azure IP Data Function
        # --------------------------------------------------------

        call_azure_function_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=call_azure_function_name,
        )

        logger.info(
            "All required Function URLs resolved successfully."
        )

        return {
            "config_service_url": config_service_url,
            "business_day_hour_status_url": (
                business_day_hour_status_url
            ),
            "get_next_business_day_url": (
                get_next_business_day_url
            ),
            "call_azure_function_url": (
                call_azure_function_url
            ),
        }

    # ============================================================
    # DEPLOY
    # ============================================================

    def deploy(
        self,
        request: Any,
        connections: Dict[str, str],
        function_urls: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Deploy arm/scoping.json.

        Function URLs are supplied by the service layer.

        Only parameters that are available in the
        ScopingDeploymentRequest or resolved Function URLs
        are passed to ARM.
        """

        logger.info(
            "Starting Scoping ARM deployment: "
            "logic_app=%s scoping01=%s",
            request.logic_app_name,
            request.scoping01_logic_app_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        # ========================================================
        # ARM TEMPLATE PATH
        # ========================================================

        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "arm"
            / "scoping.json"
        )

        if not template_path.exists():

            raise FileNotFoundError(
                "Scoping ARM template not found: "
                f"{template_path}"
            )

        # ========================================================
        # LOAD TEMPLATE
        # ========================================================

        try:

            with open(
                template_path,
                "r",
                encoding="utf-8",
            ) as file:

                template = json.load(file)

        except json.JSONDecodeError as exc:

            raise ValueError(
                "Invalid JSON in Scoping ARM template: "
                f"{template_path}"
            ) from exc

        # ========================================================
        # DEPLOYMENT NAME
        # ========================================================

        deployment_name = (
            f"scoping-{uuid.uuid4().hex[:8]}"
        )

        # ========================================================
        # CONNECTION IDS
        # ========================================================

        table_connection_id = connections.get(
            "table_connection_id"
        )

        queue_connection_id = connections.get(
            "queue_connection_id"
        )

        sharepoint_connection_id = connections.get(
            "sharepoint_connection_id"
        )

        if not table_connection_id:

            raise ValueError(
                "Table connection ID is missing."
            )

        if not queue_connection_id:

            raise ValueError(
                "Queue connection ID is missing."
            )

        if not sharepoint_connection_id:

            raise ValueError(
                "SharePoint connection ID is missing."
            )

        # ========================================================
        # MANAGED API IDS
        # ========================================================

        managed_api_ids = self._get_managed_api_ids(
            subscription_id=request.subscription_id,
            location=request.location,
        )

        # ========================================================
        # FUNCTION URLS
        # ========================================================

        if function_urls is None:
            function_urls = {}

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

        # ========================================================
        # ARM PARAMETERS
        # ========================================================

        parameters: Dict[str, Any] = {

            # ----------------------------------------------------
            # LOGIC APP NAMES
            # ----------------------------------------------------

            "logicAppName": {
                "value": request.logic_app_name,
            },

            "scoping01LogicAppName": {
                "value": request.scoping01_logic_app_name,
            },

            # ----------------------------------------------------
            # LOCATION
            # ----------------------------------------------------

            "location": {
                "value": request.location,
            },

            # ----------------------------------------------------
            # STORAGE
            # ----------------------------------------------------

            "storageAccountName": {
                "value": request.storage_account_name,
            },

            "scopingScheduleQueueName": {
                "value": request.scoping_schedule_queue_name,
            },

            "notificationLogTableName": {
                "value": request.notification_log_table_name,
            },

            # ----------------------------------------------------
            # NOTIFICATION
            # ----------------------------------------------------

            "NotificationStatus": {
                "value": request.notification_status,
            },

            "notificationServiceUrl": {
                "value": request.notification_service_url,
            },

            # ----------------------------------------------------
            # FUNCTION URLS
            # ----------------------------------------------------

            "configServiceUrl": {
                "value": config_service_url,
            },

            "businessDayHourStatusUrl": {
                "value": business_day_hour_status_url,
            },

            "getNextBusinessDayUrl": {
                "value": get_next_business_day_url,
            },

            "callAzureFunctionUrl": {
                "value": call_azure_function_url,
            },

            # ----------------------------------------------------
            # SHAREPOINT
            # ----------------------------------------------------

            "sharePointUrl": {
                "value": request.share_point_url,
            },

            # ----------------------------------------------------
            # COMPLETION CALLBACK
            # ----------------------------------------------------

            "completionLogicAppUrl": {
                "value": request.completion_logic_app_url,
            },

            "callbackSecretKey": {
                "value": request.callback_secret_key,
            },

            # ----------------------------------------------------
            # API CONNECTIONS
            # ----------------------------------------------------

            "$connections": {
                "value": {

                    request.table_connection_name: {
                        "connectionId": (
                            table_connection_id
                        ),
                        "connectionName": (
                            request.table_connection_name
                        ),
                        "id": managed_api_ids["table"],
                    },

                    request.queue_connection_name: {
                        "connectionId": (
                            queue_connection_id
                        ),
                        "connectionName": (
                            request.queue_connection_name
                        ),
                        "id": managed_api_ids["queue"],
                    },

                    request.sharepoint_connection_name: {
                        "connectionId": (
                            sharepoint_connection_id
                        ),
                        "connectionName": (
                            request.sharepoint_connection_name
                        ),
                        "id": managed_api_ids["sharepoint"],
                    },
                }
            },
        }

        # ========================================================
        # DEPLOYMENT BODY
        # ========================================================

        deployment_body = {
            "properties": {
                "mode": "Incremental",
                "template": template,
                "parameters": parameters,
            }
        }

        # ========================================================
        # SAFE LOGGING
        # ========================================================

        logger.info(
            "Deploying Scoping ARM template: "
            "deployment=%s",
            deployment_name,
        )

        logger.info(
            "Scoping-00 Logic App: %s",
            request.logic_app_name,
        )

        logger.info(
            "Scoping-01 Logic App: %s",
            request.scoping01_logic_app_name,
        )

        logger.info(
            "Storage Account: %s",
            request.storage_account_name,
        )

        logger.info(
            "Scoping Schedule Queue: %s",
            request.scoping_schedule_queue_name,
        )

        logger.info(
            "Notification Log Table: %s",
            request.notification_log_table_name,
        )

        logger.info(
            "Notification Status: %s",
            request.notification_status,
        )

        logger.info(
            "Notification Service URL configured."
        )

        logger.info(
            "Config Function URL resolved."
        )

        logger.info(
            "Business Day/Hour Function URL resolved."
        )

        logger.info(
            "Next Business Day Function URL resolved."
        )

        logger.info(
            "Process Azure IP Data Function URL resolved."
        )

        logger.info(
            "SharePoint URL configured."
        )

        logger.info(
            "Completion Logic App URL configured."
        )

        logger.info(
            "Table Connection: %s",
            request.table_connection_name,
        )

        logger.info(
            "Queue Connection: %s",
            request.queue_connection_name,
        )

        logger.info(
            "SharePoint Connection: %s",
            request.sharepoint_connection_name,
        )

        # ========================================================
        # START ARM DEPLOYMENT
        # ========================================================

        try:

            deployment = (
                resource_client.deployments
                .begin_create_or_update(
                    request.resource_group_name,
                    deployment_name,
                    deployment_body,
                )
            )

            result = deployment.result()

            provisioning_state: Optional[str] = None

            if result.properties:

                provisioning_state = (
                    result.properties.provisioning_state
                )

            logger.info(
                "Scoping deployment completed: "
                "name=%s state=%s",
                deployment_name,
                provisioning_state,
            )

            # ====================================================
            # FAILED
            # ====================================================

            if provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message: Optional[str] = None

                if result.properties:

                    error = getattr(
                        result.properties,
                        "error",
                        None,
                    )

                    if error:

                        error_message = str(error)

                return {
                    "deployment_name": deployment_name,
                    "provisioning_state": (
                        provisioning_state
                        or "Failed"
                    ),
                    "error": (
                        error_message
                        or "ARM deployment failed."
                    ),
                }

            # ====================================================
            # SUCCESS
            # ====================================================

            return {
                "deployment_name": deployment_name,
                "provisioning_state": provisioning_state,
            }

        except Exception as exc:

            logger.exception(
                "Scoping ARM deployment failed."
            )

            return {
                "deployment_name": deployment_name,
                "provisioning_state": "Failed",
                "error": str(exc),
            }