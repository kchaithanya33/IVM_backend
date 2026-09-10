import json
import logging
import uuid

from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse, parse_qs, urlunparse

import requests

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource.resources import ResourceManagementClient


logger = logging.getLogger(__name__)


class ReportingAzureManager:
    """
    Azure manager for Reporting deployment.

    Existing deployment flow:

        1. Resolve Azure Tables connection
        2. Resolve SharePoint connection
        3. Resolve Azure Queue connection
        4. Deploy Reporting 04 ONLY
        5. Resolve Reporting 04 callback URL
        6. Resolve Notification Logic App callback URL
        7. Resolve Completion Logic App callback URL
        8. Extract completionUrl and completionSasToken
        9. Resolve Function URLs
       10. Deploy Reporting 03 ONLY
       11. Return deployment details

    Reporting 02 is now additionally supported.

    Reporting 02 flow:

        1. Reporting 03 must already be deployed
        2. Resolve Reporting 03 callback URL
        3. Resolve Reporting 02 Function URLs
        4. Resolve separate Completion Notification Logic App URL
        5. Deploy Reporting 02
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
        azure_queue_connection_name: str,
    ) -> Dict[str, str]:
        """
        Resolve existing Azure Tables, SharePoint and
        Azure Queue API connection resource IDs.
        """

        logger.info(
            "Resolving Reporting API connections: "
            "azure_tables=%s sharepoint=%s azure_queue=%s",
            azure_tables_connection_name,
            sharepoint_connection_name,
            azure_queue_connection_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        table_connection_id: Optional[str] = None

        sharepoint_connection_id: Optional[str] = None

        queue_connection_id: Optional[str] = None

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

            elif connection_name == azure_queue_connection_name:

                queue_connection_id = connection.id

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

        if not queue_connection_id:

            raise ValueError(
                "Azure Queue API connection was not found: "
                f"{azure_queue_connection_name}"
            )

        logger.info(
            "Reporting API connections resolved successfully."
        )

        return {
            "table_connection_id": table_connection_id,
            "sharepoint_connection_id": (
                sharepoint_connection_id
            ),
            "queue_connection_id": (
                queue_connection_id
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
            "azurequeues": (
                f"{base}/azurequeues"
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
        Resolve the complete callback URL for a Logic App trigger.

        Calls Azure listCallbackUrl.
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
    # LOGIC APP CALLBACK DETAILS
    # ============================================================

    def get_logic_app_callback_details(
        self,
        subscription_id: str,
        resource_group_name: str,
        logic_app_name: str,
        trigger_name: str,
    ) -> Dict[str, str]:
        """
        Resolve a Logic App callback URL and split it into:

            completion_url
            completion_sas_token

        completion_url contains only the URL path.

        The /complete/{taskId}/{workflowName}/{token}
        path is NOT added here.

        EXISTING COMPLETION FLOW - DO NOT CHANGE.
        """

        resolved_callback_url = (
            self.get_logic_app_callback_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                logic_app_name=logic_app_name,
                trigger_name=trigger_name,
            )
        )

        parsed = urlparse(
            resolved_callback_url
        )

        if not parsed.scheme or not parsed.netloc:

            raise ValueError(
                "Azure returned an invalid Logic App "
                f"callback URL: {resolved_callback_url}"
            )

        query_parameters = parse_qs(
            parsed.query,
            keep_blank_values=True,
        )

        sig_values = query_parameters.get(
            "sig"
        )

        if not sig_values or not sig_values[0]:

            raise ValueError(
                "The Logic App callback URL does not "
                "contain a 'sig' parameter."
            )

        completion_sas_token = str(
            sig_values[0]
        )

        # --------------------------------------------------------
        # Remove query string
        # --------------------------------------------------------

        completion_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip("/"),
                "",
                "",
                "",
            )
        )

        if not completion_url:

            raise ValueError(
                "Unable to construct completion URL from "
                f"Logic App callback URL: "
                f"{resolved_callback_url}"
            )

        logger.info(
            "Logic App completion URL resolved successfully: "
            "logic_app=%s trigger=%s",
            logic_app_name,
            trigger_name,
        )

        logger.info(
            "Logic App completion SAS token extracted "
            "from callback URL."
        )

        return {
            "completion_url": completion_url,
            "completion_sas_token": (
                completion_sas_token
            ),
        }

    # ============================================================
    # REPORTING 04 CALLBACK URL
    # ============================================================

    def get_reporting_callback_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        reporting_logic_app_name: str,
        trigger_name: str = "When_a_HTTP_request_is_received",
    ) -> str:
        """
        Resolve the callback URL of Reporting 04.

        This URL becomes callbackUrl for Reporting 03.

        EXISTING FLOW - DO NOT CHANGE.
        """

        callback_url = (
            self.get_logic_app_callback_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                logic_app_name=reporting_logic_app_name,
                trigger_name=trigger_name,
            )
        )

        if not callback_url:

            raise ValueError(
                "Unable to resolve Reporting 04 "
                "callback URL."
            )

        logger.info(
            "Reporting 04 callback URL resolved successfully."
        )

        return callback_url

    # ============================================================
    # REPORTING 03 CALLBACK URL
    # ============================================================

    def get_reporting_03_callback_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        reporting_03_logic_app_name: str,
        trigger_name: str = "When_a_HTTP_request_is_received",
    ) -> str:
        """
        Resolve the callback URL of Reporting 03.

        This URL becomes callbackUri02 for Reporting 02.

        Reporting 03 must already be deployed before this
        method is called.
        """

        callback_url = (
            self.get_logic_app_callback_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                logic_app_name=reporting_03_logic_app_name,
                trigger_name=trigger_name,
            )
        )

        if not callback_url:

            raise ValueError(
                "Unable to resolve Reporting 03 "
                "callback URL."
            )

        logger.info(
            "Reporting 03 callback URL resolved successfully."
        )

        return callback_url

    # ============================================================
    # COMPLETION NOTIFICATION LOGIC APP CALLBACK URL
    # ============================================================

    def get_completion_notification_logic_app_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        logic_app_name: str,
        trigger_name: str,
    ) -> str:
        """
        Resolve the callback URL of the separate
        Completion Notification Logic App.

        IMPORTANT:

        This is NOT the existing Completion Logic App.

        Existing Completion Logic App:
            completion_logic_app_name
            completion_logic_app_trigger_name

        Separate Reporting 02 Completion Notification Logic App:
            completion_notification_logic_app_name
            completion_notification_logic_app_trigger_name
        """

        if not logic_app_name:

            raise ValueError(
                "Completion Notification Logic App "
                "name is required."
            )

        if not trigger_name:

            raise ValueError(
                "Completion Notification Logic App "
                "trigger name is required."
            )

        callback_url = (
            self.get_logic_app_callback_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                logic_app_name=logic_app_name,
                trigger_name=trigger_name,
            )
        )

        if not callback_url:

            raise ValueError(
                "Unable to resolve Completion Notification "
                "Logic App callback URL."
            )

        logger.info(
            "Completion Notification Logic App callback "
            "URL resolved successfully: logic_app=%s "
            "trigger=%s",
            logic_app_name,
            trigger_name,
        )

        return callback_url

    # ============================================================
    # LOAD REPORTING ARM TEMPLATE
    # ============================================================

    def _load_reporting_template(self) -> Dict[str, Any]:
        """
        Load the combined Reporting ARM template.
        """

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

        if not isinstance(template, dict):

            raise ValueError(
                "Reporting ARM template must be a JSON object."
            )

        return template

    # ============================================================
    # GET REPORTING RESOURCE
    # ============================================================

    def _get_reporting_resource(
        self,
        template: Dict[str, Any],
        resource_name_parameter: str,
    ) -> Dict[str, Any]:
        """
        Extract one Reporting Logic App resource from
        the combined ARM template.

        Supports ARM parameter expressions such as:

            [parameters('LA-reporting-04')]

        and also handles minor formatting differences.
        """

        resources = template.get(
            "resources",
            [],
        )

        if not isinstance(resources, list):

            raise ValueError(
                "Reporting ARM template resources "
                "must be a list."
            )

        # --------------------------------------------------------
        # Normalize target parameter expression
        # --------------------------------------------------------

        target_expression = (
            f"[parameters('{resource_name_parameter}')]"
        )

        normalized_target = (
            target_expression
            .replace(" ", "")
            .replace('"', "'")
            .lower()
        )

        # --------------------------------------------------------
        # Search Logic App resources
        # --------------------------------------------------------

        available_resources = []

        for resource in resources:

            if not isinstance(resource, dict):
                continue

            resource_type = str(
                resource.get(
                    "type",
                    "",
                )
            ).lower()

            if resource_type != (
                "microsoft.logic/workflows"
            ).lower():
                continue

            resource_name = resource.get(
                "name"
            )

            available_resources.append(
                resource_name
            )

            if not isinstance(
                resource_name,
                str,
            ):
                continue

            normalized_name = (
                resource_name
                .replace(" ", "")
                .replace('"', "'")
                .lower()
            )

            if normalized_name == normalized_target:

                logger.info(
                    "Found Reporting Logic App resource "
                    "for parameter '%s'.",
                    resource_name_parameter,
                )

                return resource

        # --------------------------------------------------------
        # Fallback:
        # Search the resource JSON for the parameter reference.
        # --------------------------------------------------------

        parameter_reference = (
            f"parameters('{resource_name_parameter}')"
            .replace(" ", "")
            .lower()
        )

        for resource in resources:

            if not isinstance(resource, dict):
                continue

            resource_type = str(
                resource.get(
                    "type",
                    "",
                )
            ).lower()

            if resource_type != (
                "microsoft.logic/workflows"
            ).lower():
                continue

            resource_name = resource.get(
                "name"
            )

            if not isinstance(
                resource_name,
                str,
            ):
                continue

            normalized_name = (
                resource_name
                .replace(" ", "")
                .replace('"', "'")
                .lower()
            )

            if parameter_reference in normalized_name:

                logger.info(
                    "Found Reporting Logic App resource "
                    "using parameter reference '%s'.",
                    resource_name_parameter,
                )

                return resource

        raise ValueError(
            "Unable to find Reporting Logic App resource "
            f"using parameter '{resource_name_parameter}'. "
            f"Available Logic App resources: "
            f"{available_resources}"
        )

    # ============================================================
    # BUILD SINGLE LOGIC APP TEMPLATE
    # ============================================================

    def _build_single_logic_app_template(
        self,
        template: Dict[str, Any],
        resource_name_parameter: str,
    ) -> Dict[str, Any]:
        """
        Create an ARM template containing only one
        Reporting Logic App resource.

        This is required because reporting.json contains
        multiple Reporting Logic Apps.
        """

        resource = self._get_reporting_resource(
            template=template,
            resource_name_parameter=resource_name_parameter,
        )

        original_parameters = template.get(
            "parameters",
            {},
        )

        if not isinstance(original_parameters, dict):

            raise ValueError(
                "Reporting ARM template parameters "
                "must be an object."
            )

        required_parameter_names = {
            resource_name_parameter,
            "location",
        }

        # --------------------------------------------------------
        # Keep only parameters needed by selected resource.
        # --------------------------------------------------------

        filtered_parameters = {}

        for name, definition in original_parameters.items():

            if name in required_parameter_names:

                filtered_parameters[name] = definition

        # --------------------------------------------------------
        # Reporting 04 parameters
        # --------------------------------------------------------

        if resource_name_parameter == "LA-reporting-04":

            reporting_04_parameters = {
                "storageAccountName",
                "notificationServiceUrl",
                "sharePointSiteUrl",
                "auditLogTableName",
                "splitVulnerabilitiesFunctionUrl",
                "$connections",
            }

            for name in reporting_04_parameters:

                if name in original_parameters:

                    filtered_parameters[name] = (
                        original_parameters[name]
                    )

        # --------------------------------------------------------
        # Reporting 03 parameters
        # --------------------------------------------------------

        elif resource_name_parameter == "LA-reporting-03":

            reporting_03_parameters = {
                "storageAccountName",
                "auditLogTableName",
                "sharePointSiteUrl",
                "notificationServiceUrl",
                "callbackUrl",
                "completionUrl",
                "completionSasToken",
                "afterScopingTriagingUrl",
                "triagingValidatorUrl",
                "logicAppName",
                "callbackSecretKey",
                "$connections",
            }

            for name in reporting_03_parameters:

                if name in original_parameters:

                    filtered_parameters[name] = (
                        original_parameters[name]
                    )

            # ----------------------------------------------------
            # IMPORTANT:
            #
            # The combined ARM template may not declare
            # logicAppName at the top level even though the
            # Reporting 03 resource references:
            #
            # [parameters('logicAppName')]
            #
            # Add it dynamically if it is missing.
            # ----------------------------------------------------

            if "logicAppName" not in filtered_parameters:

                filtered_parameters["logicAppName"] = {
                    "type": "string",
                    "defaultValue": "LA-reporting-03",
                }

        # --------------------------------------------------------
        # Reporting 02 parameters
        # --------------------------------------------------------

        elif resource_name_parameter == "LA-Reporting02":

            reporting_02_parameters = {
                "storageAccountName",
                "dataMergingFunctionUrl",
                "newVulnerabilitiesFunctionUrl",
                "auditLogTableName",
                "statusTableName",
                "configServiceUrl",
                "notificationServiceUrl",
                "mulesoftApiUrl",
                "sharePointSiteUrl",
                "servicenowApiUrl",
                "completion_notification_LogicAppUrl",
                "callbackSecretKey02",
                "callbackUri02",
                "completionUrl",
                "$connections",
            }

            for name in reporting_02_parameters:

                if name in original_parameters:

                    filtered_parameters[name] = (
                        original_parameters[name]
                    )

        else:

            raise ValueError(
                "Unsupported Reporting resource parameter: "
                f"{resource_name_parameter}"
            )

        return {
            "$schema": template.get(
                "$schema"
            ),
            "contentVersion": template.get(
                "contentVersion",
                "1.0.0.0",
            ),
            "parameters": filtered_parameters,
            "resources": [
                resource
            ],
        }

    # ============================================================
    # DEPLOY SINGLE REPORTING TEMPLATE
    # ============================================================

    def _deploy_reporting_template(
        self,
        request: Any,
        template: Dict[str, Any],
        parameters: Dict[str, Any],
        deployment_prefix: str,
    ) -> Dict[str, Any]:
        """
        Deploy a single Reporting ARM template.
        """

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        deployment_name = (
            f"{deployment_prefix}-{uuid.uuid4().hex[:8]}"
        )

        deployment_body = {
            "properties": {
                "mode": "Incremental",
                "template": template,
                "parameters": parameters,
            }
        }

        logger.info(
            "Starting ARM deployment: "
            "deployment=%s",
            deployment_name,
        )

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
                "ARM deployment completed: "
                "deployment=%s state=%s",
                deployment_name,
                provisioning_state,
            )

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
                "ARM deployment failed: %s",
                deployment_name,
            )

            return {
                "deployment_name": (
                    deployment_name
                ),
                "provisioning_state": "Failed",
                "error": str(exc),
            }

    # ============================================================
    # DEPLOY REPORTING 04
    # ============================================================

    def deploy(
        self,
        request: Any,
        connections: Dict[str, str],
        notification_service_url: str,
        split_vulnerabilities_function_url: str,
    ) -> Dict[str, Any]:
        """
        Deploy Reporting 04 ONLY.

        Reporting 03 is intentionally NOT deployed here.

        Reporting 03 is deployed later using deploy_reporting_03()
        after Reporting 04 callbackUrl has been resolved.

        EXISTING FLOW - DO NOT CHANGE.
        """

        table_connection_id = connections.get(
            "table_connection_id"
        )

        sharepoint_connection_id = connections.get(
            "sharepoint_connection_id"
        )

        queue_connection_id = connections.get(
            "queue_connection_id"
        )

        if not table_connection_id:

            raise ValueError(
                "Azure Tables connection ID is missing."
            )

        if not sharepoint_connection_id:

            raise ValueError(
                "SharePoint connection ID is missing."
            )

        if not queue_connection_id:

            raise ValueError(
                "Azure Queue connection ID is missing."
            )

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
        # Load combined template
        # --------------------------------------------------------

        combined_template = (
            self._load_reporting_template()
        )

        # --------------------------------------------------------
        # Extract Reporting 04 only
        # --------------------------------------------------------

        template = (
            self._build_single_logic_app_template(
                template=combined_template,
                resource_name_parameter="LA-reporting-04",
            )
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
            "azurequeues-1": {
                "connectionId": queue_connection_id,
                "connectionName": (
                    request.azure_queue_connection_name
                ),
                "id": managed_api_ids[
                    "azurequeues"
                ],
            },
        }

        # --------------------------------------------------------
        # ARM parameters - Reporting 04
        # --------------------------------------------------------

        parameters: Dict[str, Any] = {

            "LA-reporting-04": {
                "value": (
                    request.reporting_logic_app_name
                ),
            },

            "location": {
                "value": request.location,
            },

            "storageAccountName": {
                "value": request.storage_account_name,
            },

            "notificationServiceUrl": {
                "value": notification_service_url,
            },

            "sharePointSiteUrl": {
                "value": request.share_point_site_url,
            },

            "splitVulnerabilitiesFunctionUrl": {
                "value": (
                    split_vulnerabilities_function_url
                ),
            },

            "auditLogTableName": {
                "value": "NotificationLogs",
            },

            "$connections": {
                "value": connections_parameter,
            },
        }

        logger.info(
            "Deploying Reporting 04 ONLY: %s",
            request.reporting_logic_app_name,
        )

        return self._deploy_reporting_template(
            request=request,
            template=template,
            parameters=parameters,
            deployment_prefix="reporting-04",
        )

    # ============================================================
    # DEPLOY REPORTING 03
    # ============================================================

    def deploy_reporting_03(
        self,
        request: Any,
        connections: Dict[str, str],
        notification_service_url: str,
        callback_url: str,
        completion_url: str,
        completion_sas_token: str,
        after_scoping_triaging_url: str,
        triaging_validator_url: str,
    ) -> Dict[str, Any]:
        """
        Deploy Reporting 03 ONLY.

        Reporting 03 receives dynamically resolved values:

            callbackUrl
            completionUrl
            completionSasToken
            afterScopingTriagingUrl
            triagingValidatorUrl

        EXISTING FLOW - DO NOT CHANGE.
        """

        table_connection_id = connections.get(
            "table_connection_id"
        )

        sharepoint_connection_id = connections.get(
            "sharepoint_connection_id"
        )

        queue_connection_id = connections.get(
            "queue_connection_id"
        )

        if not table_connection_id:

            raise ValueError(
                "Azure Tables connection ID is missing."
            )

        if not sharepoint_connection_id:

            raise ValueError(
                "SharePoint connection ID is missing."
            )

        if not queue_connection_id:

            raise ValueError(
                "Azure Queue connection ID is missing."
            )

        # --------------------------------------------------------
        # Validate dynamic values
        # --------------------------------------------------------

        dynamic_values = {
            "notificationServiceUrl": (
                notification_service_url
            ),
            "callbackUrl": callback_url,
            "completionUrl": completion_url,
            "completionSasToken": completion_sas_token,
            "afterScopingTriagingUrl": (
                after_scoping_triaging_url
            ),
            "triagingValidatorUrl": (
                triaging_validator_url
            ),
            "callbackSecretKey": (
                request.callback_secret_key
            ),
        }

        for name, value in dynamic_values.items():

            if value is None or str(value).strip() == "":

                raise ValueError(
                    f"Required Reporting 03 value "
                    f"'{name}' is missing."
                )

        # --------------------------------------------------------
        # Load combined template
        # --------------------------------------------------------

        combined_template = (
            self._load_reporting_template()
        )

        # --------------------------------------------------------
        # Extract Reporting 03 only
        # --------------------------------------------------------

        template = (
            self._build_single_logic_app_template(
                template=combined_template,
                resource_name_parameter="LA-reporting-03",
            )
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
            "azurequeues-1": {
                "connectionId": queue_connection_id,
                "connectionName": (
                    request.azure_queue_connection_name
                ),
                "id": managed_api_ids[
                    "azurequeues"
                ],
            },
        }

        # --------------------------------------------------------
        # ARM parameters - Reporting 03
        # --------------------------------------------------------

        parameters: Dict[str, Any] = {

            "LA-reporting-03": {
                "value": (
                    request.reporting_03_logic_app_name
                ),
            },

            "location": {
                "value": request.location,
            },

            "storageAccountName": {
                "value": request.storage_account_name,
            },

            "auditLogTableName": {
                "value": "NotificationLogs",
            },

            "sharePointSiteUrl": {
                "value": request.share_point_site_url,
            },

            "notificationServiceUrl": {
                "value": notification_service_url,
            },

            # ----------------------------------------------------
            # Reporting 04 callback URL
            # ----------------------------------------------------

            "callbackUrl": {
                "value": callback_url,
            },

            # ----------------------------------------------------
            # Completion Logic App base URL
            #
            # Existing completion flow.
            # ----------------------------------------------------

            "completionUrl": {
                "value": completion_url,
            },

            # ----------------------------------------------------
            # Raw sig value
            # ----------------------------------------------------

            "completionSasToken": {
                "value": completion_sas_token,
            },

            # ----------------------------------------------------
            # Function URLs
            # ----------------------------------------------------

            "afterScopingTriagingUrl": {
                "value": (
                    after_scoping_triaging_url
                ),
            },

            "triagingValidatorUrl": {
                "value": (
                    triaging_validator_url
                ),
            },

            # ----------------------------------------------------
            # Reporting 03 workflow name
            # ----------------------------------------------------

            "logicAppName": {
                "value": (
                    request.reporting_03_logic_app_name
                ),
            },

            # ----------------------------------------------------
            # Callback secret
            # ----------------------------------------------------

            "callbackSecretKey": {
                "value": (
                    request.callback_secret_key
                ),
            },

            # ----------------------------------------------------
            # API connections
            # ----------------------------------------------------

            "$connections": {
                "value": connections_parameter,
            },
        }

        logger.info(
            "Deploying Reporting 03 ONLY: %s",
            request.reporting_03_logic_app_name,
        )

        logger.info(
            "Reporting 03 callbackUrl is the "
            "Reporting 04 callback URL."
        )

        logger.info(
            "Reporting 03 completionUrl and "
            "completionSasToken resolved dynamically."
        )

        return self._deploy_reporting_template(
            request=request,
            template=template,
            parameters=parameters,
            deployment_prefix="reporting-03",
        )

    # ============================================================
    # DEPLOY REPORTING 02
    # ============================================================

    def deploy_reporting_02(
        self,
        request: Any,
        connections: Dict[str, str],
        data_merging_function_url: str,
        new_vulnerabilities_function_url: str,
        servicenow_api_url: str,
        completion_notification_logic_app_url: str,
        callback_uri02: str,
        config_service_url: str,
        notification_service_url: str,
        mulesoft_api_url: Optional[str] = None,
        completion_url: str = "",
    ) -> Dict[str, Any]:
        """
        Deploy Reporting 02 ONLY.

        Reporting 02 receives dynamically resolved values:

            dataMergingFunctionUrl
            newVulnerabilitiesFunctionUrl
            servicenowApiUrl
            completion_notification_LogicAppUrl
            callbackUri02

        IMPORTANT:

        callbackUri02 must be the callback URL of the
        already deployed Reporting 03 Logic App.

        The existing Completion Logic App is NOT used for
        completion_notification_LogicAppUrl.
        """

        # ========================================================
        # CONNECTIONS
        # ========================================================

        table_connection_id = connections.get(
            "table_connection_id"
        )

        sharepoint_connection_id = connections.get(
            "sharepoint_connection_id"
        )

        queue_connection_id = connections.get(
            "queue_connection_id"
        )

        if not table_connection_id:

            raise ValueError(
                "Azure Tables connection ID is missing."
            )

        if not sharepoint_connection_id:

            raise ValueError(
                "SharePoint connection ID is missing."
            )

        if not queue_connection_id:

            raise ValueError(
                "Azure Queue connection ID is missing."
            )

        # ========================================================
        # VALIDATE REPORTING 02 DYNAMIC VALUES
        # ========================================================

        dynamic_values = {
            "dataMergingFunctionUrl": (
                data_merging_function_url
            ),
            "newVulnerabilitiesFunctionUrl": (
                new_vulnerabilities_function_url
            ),
            "servicenowApiUrl": (
                servicenow_api_url
            ),
            "completion_notification_LogicAppUrl": (
                completion_notification_logic_app_url
            ),
            "callbackUri02": (
                callback_uri02
            ),
            "configServiceUrl": (
                config_service_url
            ),
            "notificationServiceUrl": (
                notification_service_url
            ),
          
            "completionUrl": (
                completion_url
            ),
        }

        for name, value in dynamic_values.items():

            if value is None or str(value).strip() == "":

                raise ValueError(
                    f"Required Reporting 02 value "
                    f"'{name}' is missing."
                )

        # ========================================================
        # LOAD COMBINED TEMPLATE
        # ========================================================

        combined_template = (
            self._load_reporting_template()
        )

        # ========================================================
        # EXTRACT REPORTING 02 ONLY
        # ========================================================

        template = (
            self._build_single_logic_app_template(
                template=combined_template,
                resource_name_parameter="LA-Reporting02",
            )
        )

        # ========================================================
        # MANAGED API IDS
        # ========================================================

        managed_api_ids = (
            self._get_managed_api_ids(
                subscription_id=request.subscription_id,
                location=request.location,
            )
        )

        # ========================================================
        # $connections
        # ========================================================

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
            "azurequeues-1": {
                "connectionId": queue_connection_id,
                "connectionName": (
                    request.azure_queue_connection_name
                ),
                "id": managed_api_ids[
                    "azurequeues"
                ],
            },
        }

        # ========================================================
        # ARM PARAMETERS - REPORTING 02
        # ========================================================

        parameters: Dict[str, Any] = {

            # ----------------------------------------------------
            # Reporting 02 Logic App name
            # ----------------------------------------------------

            "LA-Reporting02": {
                "value": (
                    request.reporting_02_logic_app_name
                ),
            },

            # ----------------------------------------------------
            # Location
            # ----------------------------------------------------

            "location": {
                "value": request.location,
            },

            # ----------------------------------------------------
            # Storage
            # ----------------------------------------------------

            "storageAccountName": {
                "value": request.storage_account_name,
            },

            # ----------------------------------------------------
            # Dynamic Data Merging Function URL
            # ----------------------------------------------------

            "dataMergingFunctionUrl": {
                "value": data_merging_function_url,
            },

            # ----------------------------------------------------
            # Dynamic New Vulnerabilities Function URL
            # ----------------------------------------------------

            "newVulnerabilitiesFunctionUrl": {
                "value": (
                    new_vulnerabilities_function_url
                ),
            },

            # ----------------------------------------------------
            # Audit Table
            # ----------------------------------------------------

            "auditLogTableName": {
                "value": "NotificationLogs",
            },

            # ----------------------------------------------------
            # Status Table
            # ----------------------------------------------------

            "statusTableName": {
                "value": "NotificationStatus",
            },

            # ----------------------------------------------------
            # Configuration Service
            # ----------------------------------------------------

            "configServiceUrl": {
                "value": config_service_url,
            },

            # ----------------------------------------------------
            # Notification Service
            # ----------------------------------------------------

            "notificationServiceUrl": {
                "value": notification_service_url,
            },

            # ----------------------------------------------------
            # MuleSoft API
            # ----------------------------------------------------

            "mulesoftApiUrl": {
                "value": '6yhn7ujm8ik',
            },

            # ----------------------------------------------------
            # SharePoint
            # ----------------------------------------------------

            "sharePointSiteUrl": {
                "value": request.share_point_site_url,
            },

            # ----------------------------------------------------
            # Dynamic ServiceNow Function URL
            # ----------------------------------------------------

            "servicenowApiUrl": {
                "value": servicenow_api_url,
            },

            # ----------------------------------------------------
            # SEPARATE Completion Notification Logic App URL
            #
            # IMPORTANT:
            #
            # This is NOT completionUrl.
            #
            # This comes from:
            #
            # completion_notification_logic_app_name
            # completion_notification_logic_app_trigger_name
            #
            # and is resolved independently.
            # ----------------------------------------------------

            "completion_notification_LogicAppUrl": {
                "value": (
                    completion_notification_logic_app_url
                ),
            },

            # ----------------------------------------------------
            # Existing completion URL
            #
            # Kept separate from the Completion Notification
            # Logic App URL.
            # ----------------------------------------------------

            "completionUrl": {
                "value": completion_url,
            },

            # ----------------------------------------------------
            # Callback URI 02
            #
            # This is the Reporting 03 callback URL.
            # Reporting 03 must be deployed first.
            # ----------------------------------------------------

            "callbackUri02": {
                "value": callback_uri02,
            },

            # ----------------------------------------------------
            # Callback Secret
            #
            # Reporting 02 ARM template expects callbackSecretKey02.
            # ----------------------------------------------------

            "callbackSecretKey02": {
                "value": request.callback_secret_key,
            },

            # ----------------------------------------------------
            # API connections
            # ----------------------------------------------------

            "$connections": {
                "value": connections_parameter,
            },
        }

        logger.info(
            "Deploying Reporting 02 ONLY: %s",
            request.reporting_02_logic_app_name,
        )

        logger.info(
            "Reporting 02 dataMergingFunctionUrl resolved "
            "dynamically from Function App and Function."
        )

        logger.info(
            "Reporting 02 newVulnerabilitiesFunctionUrl "
            "resolved dynamically from Function App and Function."
        )

        logger.info(
            "Reporting 02 servicenowApiUrl resolved "
            "dynamically from Function App and Function."
        )

        logger.info(
            "Reporting 02 completion_notification_"
            "LogicAppUrl resolved from the separate "
            "Completion Notification Logic App."
        )

        logger.info(
            "Reporting 02 callbackUri02 is the callback "
            "URL of the already deployed Reporting 03."
        )

        return self._deploy_reporting_template(
            request=request,
            template=template,
            parameters=parameters,
            deployment_prefix="reporting-02",
        )