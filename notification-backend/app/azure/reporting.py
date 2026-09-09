import json
import logging
import uuid

from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse

import requests

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource.resources import ResourceManagementClient


logger = logging.getLogger(__name__)


class ReportingAzureManager:
    """
    Azure manager for Reporting deployment.

    Reporting deployment flow:

        1. Resolve Azure Tables connection
        2. Resolve SharePoint connection
        3. Resolve Split Vulnerabilities Function URL
        4. Resolve Notification Logic App callback URL
        5. Deploy arm/reporting.json
    """

    MANAGEMENT_API_VERSION = "2022-03-01"

    LOGIC_APP_API_VERSION = "2019-05-01"

    ARM_MANAGEMENT_URL = (
        "https://management.azure.com"
    )

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
        Execute an authenticated Azure Management API request.
        """

        token = self._get_management_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

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
                    "Azure REST request failed with "
                    f"status {response.status_code}: "
                    f"{response.text}"
                )
            )

        if not response.text:
            return {}

        try:
            result = response.json()

        except ValueError as exc:
            raise ValueError(
                "Azure Management API returned "
                "a non-JSON response."
            ) from exc

        if not isinstance(result, dict):
            raise ValueError(
                "Azure Management API returned "
                "an unexpected response."
            )

        return result

    # ============================================================
    # API CONNECTIONS
    # ============================================================

    def get_connections(
        self,
        subscription_id: str,
        resource_group_name: str,
        azure_tables_connection_name: str,
        sharepoint_connection_name: str,
    ) -> Dict[str, str]:
        """
        Resolve existing Azure Tables and SharePoint
        API connection resource IDs.
        """

        logger.info(
            "Resolving Reporting API connections: "
            "azure_tables=%s sharepoint=%s",
            azure_tables_connection_name,
            sharepoint_connection_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        table_connection_id: Optional[str] = None

        sharepoint_connection_id: Optional[str] = None

        connections = (
            resource_client.resources.list_by_resource_group(
                resource_group_name,
                filter=(
                    "resourceType eq "
                    "'Microsoft.Web/connections'"
                ),
            )
        )

        for connection in connections:

            connection_name = connection.name

            if connection_name == azure_tables_connection_name:

                table_connection_id = connection.id

            elif connection_name == sharepoint_connection_name:

                sharepoint_connection_id = connection.id

        if not table_connection_id:

            raise ValueError(
                "Azure Tables API connection was not found: "
                f"{azure_tables_connection_name}"
            )

        if not sharepoint_connection_id:

            raise ValueError(
                "SharePoint API connection was not found: "
                f"{sharepoint_connection_name}"
            )

        logger.info(
            "Reporting API connections resolved successfully."
        )

        return {
            "table_connection_id": table_connection_id,
            "sharepoint_connection_id": (
                sharepoint_connection_id
            ),
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
        Resolve Azure managed API resource IDs.
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
            "azuretables": (
                f"{base}/azuretables"
            ),
            "sharepointonline": (
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
        Retrieve an Azure Function resource.
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
        Retrieve a function-level key.
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

        try:

            result = self._management_request(
                method="POST",
                url=url,
                body={},
            )

        except Exception as exc:

            raise ValueError(
                "Unable to retrieve function keys "
                f"for function '{function_name}': {exc}"
            ) from exc

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
            "No function key found for "
            f"function '{function_name}'."
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
        Build the complete Azure Function HTTP URL.

        Example:

            https://myfunction.azurewebsites.net/api/MyFunction?code=xxxxx
        """

        function_resource = (
            self.get_function_resource(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                function_app_name=function_app_name,
                function_name=function_name,
            )
        )

        properties = function_resource.get(
            "properties",
            {},
        )

        if not isinstance(properties, dict):
            properties = {}

        # --------------------------------------------------------
        # Find invoke URL template
        # --------------------------------------------------------

        route = properties.get(
            "invokeUrlTemplate"
        )

        if not route:

            route = properties.get(
                "invoke_url_template"
            )

        # --------------------------------------------------------
        # Fallback to config.route
        # --------------------------------------------------------

        if not route:

            config = properties.get(
                "config"
            )

            if isinstance(config, dict):

                route = config.get("route")

        # --------------------------------------------------------
        # Final fallback
        # --------------------------------------------------------

        if not route:

            route = (
                f"/api/{function_name}"
            )

        route = str(route)

        # --------------------------------------------------------
        # Get Function App site
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
                f"{function_app_name}"
                ".azurewebsites.net"
            )

        # --------------------------------------------------------
        # Normalize route
        # --------------------------------------------------------

        if route.startswith(
            ("http://", "https://")
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
        # Get Function key
        # --------------------------------------------------------

        function_key = (
            self.get_function_key(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                function_app_name=function_app_name,
                function_name=function_name,
            )
        )

        separator = (
            "&"
            if "?" in route
            else "?"
        )

        function_url = (
            f"https://{hostname}"
            f"{route}"
            f"{separator}"
            f"code={quote(function_key, safe='')}"
        )

        logger.info(
            "Resolved Function URL for '%s'.",
            function_name,
        )

        return function_url

    # ============================================================
    # LOGIC APP TRIGGERS
    # ============================================================

    def get_logic_app_triggers(
        self,
        subscription_id: str,
        resource_group_name: str,
        logic_app_name: str,
    ) -> Dict[str, Any]:
        """
        Retrieve Logic App triggers.
        """

        url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/"
            f"{quote(subscription_id, safe='')}"
            f"/resourceGroups/"
            f"{quote(resource_group_name, safe='')}"
            f"/providers/Microsoft.Logic/workflows/"
            f"{quote(logic_app_name, safe='')}"
            f"/triggers"
            f"?api-version={self.LOGIC_APP_API_VERSION}"
        )

        try:

            return self._management_request(
                method="GET",
                url=url,
            )

        except Exception as exc:

            raise ValueError(
                "Unable to retrieve triggers from "
                f"Logic App '{logic_app_name}': {exc}"
            ) from exc

    # ============================================================
    # LOGIC APP CALLBACK URL
    # ============================================================

    def get_logic_app_callback_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        logic_app_name: str,
        trigger_name: str,
    ) -> str:
        """
        Resolve the callback URL for a Logic App trigger.
        """

        trigger_response = (
            self.get_logic_app_triggers(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                logic_app_name=logic_app_name,
            )
        )

        triggers = trigger_response.get(
            "value",
            [],
        )

        if not isinstance(triggers, list):

            raise ValueError(
                "Invalid trigger response for "
                f"Logic App '{logic_app_name}'."
            )

        selected_trigger = None

        requested = (
            trigger_name.strip().lower()
        )

        # --------------------------------------------------------
        # Exact trigger-name match
        # --------------------------------------------------------

        for trigger in triggers:

            if not isinstance(trigger, dict):
                continue

            current_name = str(
                trigger.get(
                    "name",
                    "",
                )
            )

            if (
                current_name.strip().lower()
                == requested
            ):

                selected_trigger = trigger

                break

        # --------------------------------------------------------
        # Match displayName/title/description
        # --------------------------------------------------------

        if selected_trigger is None:

            for trigger in triggers:

                if not isinstance(trigger, dict):
                    continue

                properties = trigger.get(
                    "properties",
                    {},
                )

                if not isinstance(properties, dict):
                    continue

                candidates = [
                    properties.get("displayName"),
                    properties.get("title"),
                    properties.get("description"),
                ]

                for candidate in candidates:

                    if not candidate:
                        continue

                    if (
                        str(candidate)
                        .strip()
                        .lower()
                        == requested
                    ):

                        selected_trigger = trigger

                        break

                if selected_trigger:
                    break

        # --------------------------------------------------------
        # If there is only one Request trigger, use it
        # --------------------------------------------------------

        if selected_trigger is None:

            request_triggers = []

            for trigger in triggers:

                if not isinstance(trigger, dict):
                    continue

                properties = trigger.get(
                    "properties",
                    {},
                )

                if not isinstance(properties, dict):
                    continue

                trigger_type = str(
                    properties.get(
                        "type",
                        "",
                    )
                ).lower()

                if trigger_type == "request":

                    request_triggers.append(trigger)

            if len(request_triggers) == 1:

                selected_trigger = (
                    request_triggers[0]
                )

        # --------------------------------------------------------
        # Trigger not found
        # --------------------------------------------------------

        if selected_trigger is None:

            available_triggers = [
                str(
                    trigger.get("name")
                )
                for trigger in triggers
                if isinstance(trigger, dict)
            ]

            raise ValueError(
                f"Trigger '{trigger_name}' was not found "
                f"in Logic App '{logic_app_name}'. "
                f"Available triggers: "
                f"{available_triggers}"
            )

        actual_trigger_name = (
            selected_trigger.get("name")
        )

        # --------------------------------------------------------
        # listCallbackUrl
        # --------------------------------------------------------

        callback_url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/"
            f"{quote(subscription_id, safe='')}"
            f"/resourceGroups/"
            f"{quote(resource_group_name, safe='')}"
            f"/providers/Microsoft.Logic/workflows/"
            f"{quote(logic_app_name, safe='')}"
            f"/triggers/"
            f"{quote(str(actual_trigger_name), safe='')}"
            f"/listCallbackUrl"
            f"?api-version={self.LOGIC_APP_API_VERSION}"
        )

        callback_response = (
            self._management_request(
                method="POST",
                url=callback_url,
                body={},
            )
        )

        resolved_url = callback_response.get(
            "value"
        )

        if not resolved_url:

            resolved_url = callback_response.get(
                "callbackUrl"
            )

        if not resolved_url:

            raise ValueError(
                "Azure did not return a callback URL "
                f"for trigger '{actual_trigger_name}' "
                f"in Logic App '{logic_app_name}'."
            )

        logger.info(
            "Resolved Logic App callback URL: "
            "logic_app=%s trigger=%s",
            logic_app_name,
            actual_trigger_name,
        )

        return str(resolved_url)

    # ============================================================
    # DEPLOY REPORTING
    # ============================================================

    def deploy(
        self,
        request: Any,
        connections: Dict[str, str],
        notification_service_url: str,
        split_vulnerabilities_function_url: str,
    ) -> Dict[str, Any]:
        """
        Deploy arm/reporting.json.

        Dynamic values:

            notification_service_url
                -> notificationServiceUrl

            split_vulnerabilities_function_url
                -> splitVulnerabilitiesFunctionUrl
        """

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        # --------------------------------------------------------
        # ARM template
        # --------------------------------------------------------

        template_path = (
            Path(__file__).resolve().parent.parent.parent
            / "arm"
            / "reporting.json"
        )

        if not template_path.exists():

            raise FileNotFoundError(
                "Reporting ARM template not found: "
                f"{template_path}"
            )

        with open(
            template_path,
            "r",
            encoding="utf-8",
        ) as file:

            template = json.load(file)

        # --------------------------------------------------------
        # Connection IDs
        # --------------------------------------------------------

        table_connection_id = connections.get(
            "table_connection_id"
        )

        sharepoint_connection_id = connections.get(
            "sharepoint_connection_id"
        )

        if not table_connection_id:

            raise ValueError(
                "Azure Tables connection ID is missing."
            )

        if not sharepoint_connection_id:

            raise ValueError(
                "SharePoint connection ID is missing."
            )

        # --------------------------------------------------------
        # Validate dynamic URLs
        # --------------------------------------------------------

        if not notification_service_url:

            raise ValueError(
                "Notification Service callback URL "
                "could not be resolved."
            )

        if not split_vulnerabilities_function_url:

            raise ValueError(
                "Split Vulnerabilities Function URL "
                "could not be resolved."
            )

        # --------------------------------------------------------
        # Managed API IDs
        # --------------------------------------------------------

        managed_api_ids = (
            self._get_managed_api_ids(
                subscription_id=request.subscription_id,
                location=request.location,
            )
        )

        # --------------------------------------------------------
        # $connections
        #
        # IMPORTANT:
        #
        # reporting.json currently references:
        #
        #   azuretables-1
        #   sharepointonline-1
        #
        # inside:
        #
        #   @parameters('$connections')['azuretables-1']
        #   @parameters('$connections')['sharepointonline-1']
        #
        # Therefore these keys must match those names.
        # --------------------------------------------------------

        connections_parameter = {
            "azuretables-1": {
                "connectionId": table_connection_id,
                "connectionName": (
                    request.azure_tables_connection_name
                ),
                "id": managed_api_ids[
                    "azuretables"
                ],
            },
            "sharepointonline-1": {
                "connectionId": sharepoint_connection_id,
                "connectionName": (
                    request.sharepoint_connection_name
                ),
                "id": managed_api_ids[
                    "sharepointonline"
                ],
            },
        }

        # --------------------------------------------------------
        # ARM PARAMETERS
        # --------------------------------------------------------

        parameters: Dict[str, Any] = {

            # Reporting Logic App
            "LA-reporting-04": {
                "value": (
                    request.reporting_logic_app_name
                ),
            },

            # Azure region
            "location": {
                "value": request.location,
            },

            # Storage Account
            "storageAccountName": {
                "value": request.storage_account_name,
            },

            # DYNAMIC Notification Logic App URL
            "notificationServiceUrl": {
                "value": notification_service_url,
            },

            # SharePoint Site
            "sharePointSiteUrl": {
                "value": request.share_point_site_url,
            },

            # Audit Log table
          

            # DYNAMIC Function URL
            "splitVulnerabilitiesFunctionUrl": {
                "value": (
                    split_vulnerabilities_function_url
                ),
            },

            # API connection names
            "azureTablesConnectionName": {
                "value": (
                    request.azure_tables_connection_name
                ),
            },

            "sharePointOnlineConnectionName": {
                "value": (
                    request.sharepoint_connection_name
                ),
            },

            # Logic App $connections
            "$connections": {
                "value": connections_parameter,
            },
        }

        # --------------------------------------------------------
        # Deployment name
        # --------------------------------------------------------

        deployment_name = (
            f"reporting-{uuid.uuid4().hex[:8]}"
        )

        # --------------------------------------------------------
        # Deployment body
        # --------------------------------------------------------

        deployment_body = {
            "properties": {
                "mode": "Incremental",
                "template": template,
                "parameters": parameters,
            }
        }

        logger.info(
            "Deploying Reporting Logic App: %s",
            request.reporting_logic_app_name,
        )

        logger.info(
            "Notification Service URL resolved dynamically."
        )

        logger.info(
            "Split Vulnerabilities Function URL "
            "resolved dynamically."
        )

        # --------------------------------------------------------
        # ARM deployment
        # --------------------------------------------------------

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

            provisioning_state = None

            if result.properties:

                provisioning_state = (
                    result.properties.provisioning_state
                )

            logger.info(
                "Reporting deployment completed: "
                "deployment=%s state=%s",
                deployment_name,
                provisioning_state,
            )

            # ----------------------------------------------------
            # Failed deployment
            # ----------------------------------------------------

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

                        error_message = str(
                            error
                        )

                return {
                    "deployment_name": (
                        deployment_name
                    ),
                    "provisioning_state": (
                        provisioning_state
                        or "Failed"
                    ),
                    "error": (
                        error_message
                        or "ARM deployment failed."
                    ),
                }

            # ----------------------------------------------------
            # Success
            # ----------------------------------------------------

            return {
                "deployment_name": (
                    deployment_name
                ),
                "provisioning_state": (
                    provisioning_state
                ),
            }

        except Exception as exc:

            logger.exception(
                "Reporting ARM deployment failed."
            )

            return {
                "deployment_name": (
                    deployment_name
                ),
                "provisioning_state": "Failed",
                "error": str(exc),
            }