import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import requests

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient


logger = logging.getLogger(__name__)


class ScopingAzureManager:
    """
    Azure manager for Scoping-00 Logic App deployment.

    Responsibilities
    ----------------
    1. Resolve Azure API connections.
    2. Retrieve actual Azure Function route metadata.
    3. Retrieve Function App function keys using Azure REST API.
    4. Build the real Function URLs dynamically.
    5. Build ARM deployment parameters.
    6. Deploy the Scoping Logic App ARM template.
    """

    MANAGEMENT_API_VERSION = "2022-03-01"

    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()

    # ============================================================
    # AUTHENTICATION
    # ============================================================

    def _get_management_token(self) -> str:
        """
        Get an Azure Resource Manager access token.
        """

        token = self.credential.get_token(
            "https://management.azure.com/.default"
        )

        return token.token

    # ============================================================
    # REST REQUEST
    # ============================================================

    def _management_request(
        self,
        method: str,
        url: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute an authenticated Azure Management REST request.
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
                "Azure REST request failed: status=%s body=%s",
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

        return response.json()

    # ============================================================
    # CONNECTIONS
    # ============================================================

    def get_connections(
        self,
        subscription_id: str,
        resource_group_name: str,
        table_connection_name: str,
        queue_connection_name: str,
    ) -> Dict[str, Optional[str]]:
        """
        Resolve Logic App API connection resource IDs.
        """

        logger.info(
            "Resolving API connections: table=%s queue=%s",
            table_connection_name,
            queue_connection_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        table_connection_id = None
        queue_connection_id = None

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

            if connection_name == queue_connection_name:
                queue_connection_id = connection.id

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

        logger.info(
            "Resolved Azure Tables connection: %s",
            table_connection_id,
        )

        logger.info(
            "Resolved Azure Queues connection: %s",
            queue_connection_id,
        )

        return {
            "table_connection_id": table_connection_id,
            "queue_connection_id": queue_connection_id,
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
        Retrieve the actual Azure Function resource.

        This is important because the Function App function name
        does NOT necessarily equal the HTTP route.

        Example:

            Function name:
                GetPartitionConfigs

            Actual route:
                /api/config/{partition}

        Azure stores the actual route in function metadata.
        """

        url = (
            "https://management.azure.com"
            f"/subscriptions/{quote(subscription_id)}"
            f"/resourceGroups/{quote(resource_group_name)}"
            f"/providers/Microsoft.Web/sites/{quote(function_app_name)}"
            f"/functions/{quote(function_name)}"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        logger.info(
            "Retrieving Azure Function metadata: app=%s function=%s",
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
                f"Unable to retrieve function '{function_name}' "
                f"from Function App '{function_app_name}': {exc}"
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
        Retrieve the function key using the Azure REST listKeys
        operation.

        This avoids the WebSiteManagementClient issue where the
        returned SDK object can differ between Azure SDK versions.
        """

        url = (
            "https://management.azure.com"
            f"/subscriptions/{quote(subscription_id)}"
            f"/resourceGroups/{quote(resource_group_name)}"
            f"/providers/Microsoft.Web/sites/{quote(function_app_name)}"
            f"/functions/{quote(function_name)}"
            f"/listKeys"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        logger.info(
            "Retrieving function key using REST listKeys: "
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

        # Azure normally returns:
        #
        # {
        #     "keys": {
        #         "default": "...."
        #     }
        # }
        #
        # Some API versions may return keys directly.

        keys = result.get("keys")

        if isinstance(keys, dict):

            function_key = keys.get("default")

            if not function_key:
                for value in keys.values():

                    if value:
                        function_key = value
                        break

            if function_key:
                return str(function_key)

        # Fallback in case the API returns keys directly.

        function_key = result.get("default")

        if function_key:
            return str(function_key)

        raise ValueError(
            f"No function key was found for function "
            f"'{function_name}' in Function App "
            f"'{function_app_name}'."
        )

    # ============================================================
    # EXTRACT ACTUAL FUNCTION ROUTE
    # ============================================================

    def get_function_route(
        self,
        function_resource: Dict[str, Any],
        function_name: str,
    ) -> str:
        """
        Extract the actual HTTP route from Azure Function metadata.

        Azure may return the route under:

            properties.invoke_url_template

        or:

            properties.config.route

        or other metadata depending on the Functions runtime/API
        version.

        If Azure does not expose a custom route, we fall back to:

            /api/{function_name}
        """

        properties = function_resource.get(
            "properties",
            {},
        )

        if not isinstance(properties, dict):
            properties = {}

        # --------------------------------------------------------
        # Preferred: invokeUrlTemplate
        # --------------------------------------------------------

        invoke_url_template = (
            properties.get("invokeUrlTemplate")
        )

        if invoke_url_template:

            logger.info(
                "Azure returned invokeUrlTemplate for "
                "function '%s': %s",
                function_name,
                invoke_url_template,
            )

            return str(invoke_url_template)

        # --------------------------------------------------------
        # Alternative property naming
        # --------------------------------------------------------

        invoke_url_template = (
            properties.get("invoke_url_template")
        )

        if invoke_url_template:

            logger.info(
                "Azure returned invoke_url_template for "
                "function '%s': %s",
                function_name,
                invoke_url_template,
            )

            return str(invoke_url_template)

        # --------------------------------------------------------
        # Check function config
        # --------------------------------------------------------

        config = properties.get("config")

        if isinstance(config, dict):

            route = config.get("route")

            if route:

                logger.info(
                    "Azure returned custom route for "
                    "function '%s': %s",
                    function_name,
                    route,
                )

                route = str(route)

                if not route.startswith("/"):
                    route = "/" + route

                if not route.startswith("/api/"):
                    route = "/api" + route

                return route

        # --------------------------------------------------------
        # Fallback
        # --------------------------------------------------------

        logger.warning(
            "Azure did not expose a custom route for function "
            "'%s'. Using default route: %s",
            function_name,
            function_name,
        )

        return f"/api/{function_name}"

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
        Build the real Azure Function URL dynamically.

        Example:

            Function name:
                GetPartitionConfigs

            Azure route:
                /api/config/{partition}

            Result:

            https://function-app-chai.azurewebsites.net/api/config/{partition}?code=XXXX
        """

        logger.info(
            "Resolving Function URL: app=%s function=%s",
            function_app_name,
            function_name,
        )

        # --------------------------------------------------------
        # Get Function App
        # --------------------------------------------------------

        web_client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        # Verify resource group exists.

        try:
            resource = web_client.resources.get(
                resource_group_name,
                "Microsoft.Web",
                "",
                "sites",
                function_app_name,
                "2022-03-01",
            )

        except Exception:
            resource = None

        # --------------------------------------------------------
        # Retrieve function metadata using REST
        # --------------------------------------------------------

        function_resource = self.get_function_resource(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=function_name,
        )

        if not function_resource:
            raise ValueError(
                f"Function '{function_name}' was not found "
                f"in Function App '{function_app_name}'."
            )

        # --------------------------------------------------------
        # Get hostname
        # --------------------------------------------------------

        site_url = (
            "https://management.azure.com"
            f"/subscriptions/{quote(subscription_id)}"
            f"/resourceGroups/{quote(resource_group_name)}"
            f"/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name)}"
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

        hostname = None

        if isinstance(site_properties, dict):
            hostname = site_properties.get(
                "defaultHostName"
            )

        if not hostname:
            hostname = (
                f"{function_app_name}.azurewebsites.net"
            )

        # --------------------------------------------------------
        # Get actual route
        # --------------------------------------------------------

        route = self.get_function_route(
            function_resource=function_resource,
            function_name=function_name,
        )

        # --------------------------------------------------------
        # If Azure returns a complete URL, use its path
        # --------------------------------------------------------

        if route.startswith("http://") or route.startswith(
            "https://"
        ):

            # Remove hostname because we want to use the current
            # Function App hostname.

            from urllib.parse import urlparse

            parsed = urlparse(route)

            route = parsed.path

            if parsed.query:
                route = f"{route}?{parsed.query}"

        # --------------------------------------------------------
        # Normalize route
        # --------------------------------------------------------

        if not route.startswith("/"):
            route = "/" + route

        # --------------------------------------------------------
        # Get function key
        # --------------------------------------------------------

        function_key = self.get_function_key(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=function_name,
        )

        # --------------------------------------------------------
        # Build URL
        # --------------------------------------------------------

        separator = "&" if "?" in route else "?"

        url = (
            f"https://{hostname}"
            f"{route}"
            f"{separator}"
            f"code={quote(function_key, safe='')}"
        )

        logger.info(
            "Resolved Function URL: app=%s function=%s url=%s",
            function_app_name,
            function_name,
            url.split("?")[0],
        )

        return url

    # ============================================================
    # RESOLVE ALL FUNCTION URLS
    # ============================================================

    def get_function_urls(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        config_function_name: str,
        business_day_hour_status_function_name: str,
        get_next_business_day_function_name: str,
    ) -> Dict[str, str]:
        """
        Resolve all Function URLs required by Scoping-00.
        """

        logger.info(
            "Resolving Scoping Function URLs from Function App: %s",
            function_app_name,
        )

        # --------------------------------------------------------
        # Config
        # --------------------------------------------------------

        config_service_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=config_function_name,
        )

        # --------------------------------------------------------
        # Business Day / Hour
        # --------------------------------------------------------

        business_day_hour_status_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=business_day_hour_status_function_name,
        )

        # --------------------------------------------------------
        # Next Business Day
        # --------------------------------------------------------

        get_next_business_day_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=get_next_business_day_function_name,
        )

        return {
            "config_service_url": config_service_url,
            "business_day_hour_status_url": (
                business_day_hour_status_url
            ),
            "get_next_business_day_url": (
                get_next_business_day_url
            ),
        }

    # ============================================================
    # DEPLOY
    # ============================================================

    def deploy(
        self,
        request: Any,
        connections: Dict[str, Optional[str]],
        function_urls: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Deploy the Scoping ARM template.

        IMPORTANT:
        Azure ResourceManagementClient expects the deployment
        request body to contain:

            {
                "properties": {
                    "mode": "...",
                    "template": "...",
                    "parameters": "..."
                }
            }

        The previous implementation placed these properties at
        the root, which caused:

            Required property 'properties' not found in JSON.
        """

        logger.info(
            "Starting ARM deployment for Logic App: %s",
            request.logic_app_name,
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
                f"Scoping ARM template not found: "
                f"{template_path}"
            )

        # ========================================================
        # LOAD TEMPLATE
        # ========================================================

        with open(
            template_path,
            "r",
            encoding="utf-8",
        ) as file:

            template = json.load(file)

        # ========================================================
        # DEPLOYMENT NAME
        # ========================================================

        deployment_name = (
            f"scoping-{uuid.uuid4().hex[:8]}"
        )

        # ========================================================
        # CONNECTION IDS
        # ========================================================

        table_connection_id = (
            connections.get("table_connection_id")
        )

        queue_connection_id = (
            connections.get("queue_connection_id")
        )

        if not table_connection_id:

            raise ValueError(
                "Table connection ID is missing."
            )

        if not queue_connection_id:

            raise ValueError(
                "Queue connection ID is missing."
            )

        # ========================================================
        # MANAGED API IDS
        # ========================================================

        table_managed_api_id = (
            f"/subscriptions/"
            f"{request.subscription_id}"
            f"/providers/Microsoft.Web/"
            f"locations/{request.location}"
            f"/managedApis/azuretables"
        )

        queue_managed_api_id = (
            f"/subscriptions/"
            f"{request.subscription_id}"
            f"/providers/Microsoft.Web/"
            f"locations/{request.location}"
            f"/managedApis/azurequeues"
        )

        # ========================================================
        # FUNCTION URL VALIDATION
        # ========================================================

        config_service_url = function_urls.get(
            "config_service_url"
        )

        business_day_hour_status_url = function_urls.get(
            "business_day_hour_status_url"
        )

        get_next_business_day_url = function_urls.get(
            "get_next_business_day_url"
        )

        if not config_service_url:
            raise ValueError(
                "Config Service Function URL is missing."
            )

        if not business_day_hour_status_url:
            raise ValueError(
                "Business Day Hour Status Function URL "
                "is missing."
            )

        if not get_next_business_day_url:
            raise ValueError(
                "Get Next Business Day Function URL "
                "is missing."
            )

        # ========================================================
        # ARM PARAMETERS
        # ========================================================

        parameters = {

            "logicAppName": {
                "value": request.logic_app_name
            },

            "location": {
                "value": request.location
            },

            "storageAccountName": {
                "value": request.storage_account_name
            },

            "scopingScheduleQueueName": {
                "value": request.scoping_schedule_queue_name
            },

            "notificationLogTableName": {
                "value": request.notification_log_table_name
            },

            "completionLogicAppUrl": {
                "value": request.completion_logic_app_url
            },

            "callbackSecretKey": {
                "value": request.callback_secret_key
            },

            "notificationServiceUrl": {
                "value": request.notification_service_url
            },

            # ----------------------------------------------------
            # DYNAMIC FUNCTION URLS
            # ----------------------------------------------------

            "configServiceUrl": {
                "value": config_service_url
            },

            "businessDayHourStatusUrl": {
                "value": business_day_hour_status_url
            },

            "getNextBusinessDayUrl": {
                "value": get_next_business_day_url
            },

            # ----------------------------------------------------
            # LOGIC APP API CONNECTIONS
            # ----------------------------------------------------

            "$connections": {
                "value": {

                    request.table_connection_name: {
                        "connectionId": table_connection_id,
                        "connectionName": (
                            request.table_connection_name
                        ),
                        "id": table_managed_api_id,
                    },

                    request.queue_connection_name: {
                        "connectionId": queue_connection_id,
                        "connectionName": (
                            request.queue_connection_name
                        ),
                        "id": queue_managed_api_id,
                    },
                }
            },
        }

        # ========================================================
        # CORRECT ARM DEPLOYMENT BODY
        # ========================================================
        #
        # THIS IS THE IMPORTANT FIX.
        #
        # Wrong:
        #
        # {
        #     "mode": "...",
        #     "template": "...",
        #     "parameters": "..."
        # }
        #
        # Correct:
        #
        # {
        #     "properties": {
        #         "mode": "...",
        #         "template": "...",
        #         "parameters": "..."
        #     }
        # }
        #

        deployment_properties = {
            "properties": {
                "mode": "Incremental",
                "template": template,
                "parameters": parameters,
            }
        }

        # ========================================================
        # LOG SAFE DEPLOYMENT INFORMATION
        # ========================================================

        logger.info(
            "Deploying Scoping ARM template: %s",
            deployment_name,
        )

        logger.info(
            "Logic App: %s",
            request.logic_app_name,
        )

        logger.info(
            "Storage Account: %s",
            request.storage_account_name,
        )

        logger.info(
            "Table Connection: %s",
            table_connection_id,
        )

        logger.info(
            "Queue Connection: %s",
            queue_connection_id,
        )

        logger.info(
            "Config Function URL: %s",
            config_service_url.split("?")[0],
        )

        logger.info(
            "Business Day Function URL: %s",
            business_day_hour_status_url.split("?")[0],
        )

        logger.info(
            "Next Business Day Function URL: %s",
            get_next_business_day_url.split("?")[0],
        )

        # ========================================================
        # START DEPLOYMENT
        # ========================================================

        try:

            deployment = (
                resource_client.deployments
                .begin_create_or_update(
                    request.resource_group_name,
                    deployment_name,
                    deployment_properties,
                )
            )

            result = deployment.result()

            provisioning_state = None

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
            # ARM DEPLOYMENT ERROR
            # ====================================================

            if provisioning_state not in {
                "Succeeded",
                "succeeded",
            }:

                error_message = None

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
                        provisioning_state or "Failed"
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