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


class VulnAzureService:
    """
    Azure operations for Vulnerability Scan Logic Apps.
    """

    MANAGEMENT_API_VERSION = "2022-03-01"
    LOGIC_APP_API_VERSION = "2019-05-01"
    ARM_MANAGEMENT_URL = "https://management.azure.com"

    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()

    # ============================================================
    # MANAGEMENT TOKEN
    # ============================================================

    def _get_management_token(self) -> str:
        return self.credential.get_token(
            "https://management.azure.com/.default"
        ).token

    # ============================================================
    # MANAGEMENT REST REQUEST
    # ============================================================

    def _management_request(
        self,
        method: str,
        url: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        response = requests.request(
            method=method,
            url=url,
            headers={
                "Authorization": (
                    f"Bearer {self._get_management_token()}"
                ),
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60,
        )

        if not response.ok:
            raise HttpResponseError(
                message=(
                    "Azure REST request failed with status "
                    f"{response.status_code}: {response.text}"
                )
            )

        if not response.text:
            return {}

        result = response.json()

        if not isinstance(result, dict):
            raise ValueError(
                "Azure Management API returned an unexpected response."
            )

        return result

    # ============================================================
    # RESOURCE GROUP LOCATION
    # ============================================================

    def get_resource_group_location(
        self,
        subscription_id: str,
        resource_group_name: str,
    ) -> str:

        client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        group = client.resource_groups.get(
            resource_group_name
        )

        if not group.location:
            raise ValueError(
                f"Resource group '{resource_group_name}' "
                "has no location."
            )

        return str(group.location)

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
    ) -> Dict[str, Any]:

        logger.info(
            "Resolving Vulnerability Scan API connections: "
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
                filter=(
                    "resourceType eq "
                    "'Microsoft.Web/connections'"
                ),
            )
        )

        for connection in connections:

            connection_name = str(connection.name)

            if connection_name == table_connection_name:
                table_connection_id = str(connection.id)

            elif connection_name == queue_connection_name:
                queue_connection_id = str(connection.id)

            elif connection_name == sharepoint_connection_name:
                sharepoint_connection_id = str(connection.id)

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

        location = self.get_resource_group_location(
            subscription_id,
            resource_group_name,
        )

        managed = self._get_managed_api_ids(
            subscription_id=subscription_id,
            location=location,
        )

        arm_connections = {
            table_connection_name: {
                "connectionId": table_connection_id,
                "connectionName": table_connection_name,
                "id": managed["table"],
            },
            queue_connection_name: {
                "connectionId": queue_connection_id,
                "connectionName": queue_connection_name,
                "id": managed["queue"],
            },
            sharepoint_connection_name: {
                "connectionId": sharepoint_connection_id,
                "connectionName": sharepoint_connection_name,
                "id": managed["sharepoint"],
            },
        }

        return {
            "table_connection_id": table_connection_id,
            "queue_connection_id": queue_connection_id,
            "sharepoint_connection_id": sharepoint_connection_id,
            "arm_connections": arm_connections,
        }

    # ============================================================
    # MANAGED API IDS
    # ============================================================

    def _get_managed_api_ids(
        self,
        subscription_id: str,
        location: str,
    ) -> Dict[str, str]:

        base = (
            f"/subscriptions/{quote(subscription_id, safe='')}"
            f"/providers/Microsoft.Web/locations/"
            f"{quote(location, safe='')}/managedApis"
        )

        return {
            "table": f"{base}/azuretables",
            "queue": f"{base}/azurequeues",
            "sharepoint": f"{base}/sharepointonline",
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

        url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}"
            f"/resourceGroups/"
            f"{quote(resource_group_name, safe='')}"
            f"/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name, safe='')}"
            f"/functions/"
            f"{quote(function_name, safe='')}"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        return self._management_request(
            "GET",
            url,
        )

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

        url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
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

        result = self._management_request(
            "POST",
            url,
            {},
        )

        keys = result.get("keys")

        if isinstance(keys, dict):

            if keys.get("default"):
                return str(keys["default"])

            for value in keys.values():
                if value:
                    return str(value)

        if result.get("default"):
            return str(result["default"])

        raise ValueError(
            f"No function key found for function "
            f"'{function_name}'."
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

        resource = self.get_function_resource(
            subscription_id,
            resource_group_name,
            function_app_name,
            function_name,
        )

        props = resource.get(
            "properties",
            {},
        )

        route = None

        if isinstance(props, dict):

            route = (
                props.get("invokeUrlTemplate")
                or props.get("invoke_url_template")
            )

        if not route:
            route = f"/api/{function_name}"

        route = str(route)

        if route.startswith(
            ("http://", "https://")
        ):
            parsed = urlparse(route)

            route = parsed.path

            if parsed.query:
                route += f"?{parsed.query}"

        if not route.startswith("/"):
            route = "/" + route

        if not route.startswith("/api/"):
            route = "/api" + route

        site_url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}"
            f"/resourceGroups/"
            f"{quote(resource_group_name, safe='')}"
            f"/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name, safe='')}"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        site = self._management_request(
            "GET",
            site_url,
        )

        site_props = site.get(
            "properties",
            {},
        )

        hostname = None

        if isinstance(site_props, dict):
            hostname = site_props.get(
                "defaultHostName"
            )

        if not hostname:
            hostname = (
                f"{function_app_name}.azurewebsites.net"
            )

        key = self.get_function_key(
            subscription_id,
            resource_group_name,
            function_app_name,
            function_name,
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
            f"code={quote(key, safe='')}"
        )

    # ============================================================
    # LOGIC APP TRIGGERS
    # ============================================================

    def get_logic_app_triggers(
        self,
        subscription_id: str,
        resource_group_name: str,
        logic_app_name: str,
    ) -> Dict[str, Any]:

        url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}"
            f"/resourceGroups/"
            f"{quote(resource_group_name, safe='')}"
            f"/providers/Microsoft.Logic/workflows/"
            f"{quote(logic_app_name, safe='')}"
            f"/triggers"
            f"?api-version={self.LOGIC_APP_API_VERSION}"
        )

        return self._management_request(
            "GET",
            url,
        )

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

        response = self.get_logic_app_triggers(
            subscription_id,
            resource_group_name,
            logic_app_name,
        )

        triggers = response.get(
            "value",
            [],
        )

        if not isinstance(triggers, list):
            raise ValueError(
                f"Invalid trigger response for "
                f"Logic App '{logic_app_name}'."
            )

        requested = (
            trigger_name.strip().lower()
        )

        selected = None

        # --------------------------------------------------------
        # EXACT TRIGGER NAME
        # --------------------------------------------------------

        for trigger in triggers:

            if not isinstance(trigger, dict):
                continue

            if (
                str(trigger.get("name", ""))
                .strip()
                .lower()
                == requested
            ):
                selected = trigger
                break

        # --------------------------------------------------------
        # DISPLAY NAME / TITLE / DESCRIPTION
        # --------------------------------------------------------

        if selected is None:

            for trigger in triggers:

                if not isinstance(trigger, dict):
                    continue

                props = trigger.get(
                    "properties",
                    {},
                )

                if not isinstance(props, dict):
                    continue

                for candidate in (
                    props.get("displayName"),
                    props.get("title"),
                    props.get("description"),
                ):

                    if (
                        candidate
                        and str(candidate)
                        .strip()
                        .lower()
                        == requested
                    ):
                        selected = trigger
                        break

                if selected:
                    break

        # --------------------------------------------------------
        # IF ONLY ONE REQUEST TRIGGER EXISTS
        # --------------------------------------------------------

        if selected is None:

            request_triggers = []

            for trigger in triggers:

                if not isinstance(trigger, dict):
                    continue

                props = trigger.get(
                    "properties",
                    {},
                )

                if not isinstance(props, dict):
                    continue

                if (
                    str(
                        props.get("type", "")
                    ).lower()
                    == "request"
                ):
                    request_triggers.append(
                        trigger
                    )

            if len(request_triggers) == 1:
                selected = request_triggers[0]

        # --------------------------------------------------------
        # TRIGGER NOT FOUND
        # --------------------------------------------------------

        if selected is None:

            available = [
                str(trigger.get("name"))
                for trigger in triggers
                if isinstance(trigger, dict)
            ]

            raise ValueError(
                f"Trigger '{trigger_name}' was not found "
                f"in Logic App '{logic_app_name}'. "
                f"Available triggers: {available}"
            )

        actual_name = selected.get("name")

        if not actual_name:
            raise ValueError(
                f"Logic App trigger '{trigger_name}' "
                "has no valid name."
            )

        # --------------------------------------------------------
        # LIST CALLBACK URL
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
            f"{quote(str(actual_name), safe='')}"
            f"/listCallbackUrl"
            f"?api-version="
            f"{self.LOGIC_APP_API_VERSION}"
        )

        callback = self._management_request(
            "POST",
            callback_url,
            {},
        )

        value = (
            callback.get("value")
            or callback.get("callbackUrl")
        )

        if not value:
            raise ValueError(
                "Azure did not return a callback URL "
                f"for trigger '{actual_name}' "
                f"in Logic App '{logic_app_name}'."
            )

        return str(value)

    # ============================================================
    # DEPLOY LOGIC APP RESOURCE
    # ============================================================

    def deploy(
        self,
        subscription_id: str,
        resource_group_name: str,
        location: str,
        template_resource_index: int,
        parameters: Dict[str, Any],
        deployment_prefix: str,
    ) -> Dict[str, Any]:

        # IMPORTANT:
        # Put the ARM file here:
        #
        # project/
        #   arm/
        #       LA-VulnScan-Merged.json
        #
        candidates = [
            Path(__file__).resolve().parents[2]
            / "arm"
            / "vuln.json"
        ]

        template_path = candidates[0]

        if not template_path.exists():
            raise FileNotFoundError(
                "Vulnerability Scan ARM template not found: "
                f"{template_path}"
            )

        with open(
            template_path,
            "r",
            encoding="utf-8",
        ) as file:

            template = json.load(file)

        resources = template.get(
            "resources"
        )

        if not isinstance(resources, list):
            raise ValueError(
                "LA-VulnScan-Merged.json does not "
                "contain a resources array."
            )

        if template_resource_index not in range(
            len(resources)
        ):
            raise ValueError(
                f"Invalid Vulnerability Scan resource "
                f"index {template_resource_index}."
            )

        # --------------------------------------------------------
        # DEPLOY ONLY ONE LOGIC APP
        # --------------------------------------------------------

        single_template = dict(
            template
        )

        single_template["resources"] = [
            resources[template_resource_index]
        ]

        root_parameters = template.get(
            "parameters",
            {},
        )

        supplied = dict(parameters)

        # --------------------------------------------------------
        # VALIDATE REQUIRED ROOT PARAMETERS
        # --------------------------------------------------------

        for name, definition in root_parameters.items():

            if (
                name not in supplied
                and "defaultValue" not in definition
            ):
                raise ValueError(
                    "Vulnerability Scan ARM template "
                    f"parameter '{name}' is required "
                    "but the backend did not supply it."
                )

        deployment_parameters = {
            name: value
            for name, value in supplied.items()
            if name in root_parameters
        }

        deployment_name = (
            f"{deployment_prefix}-"
            f"{uuid.uuid4().hex[:8]}"
        )

        body = {
            "properties": {
                "mode": "Incremental",
                "template": single_template,
                "parameters": deployment_parameters,
            }
        }

        client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        try:

            deployment = (
                client.deployments
                .begin_create_or_update(
                    resource_group_name,
                    deployment_name,
                    body,
                )
            )

            result = deployment.result()

            properties = getattr(
                result,
                "properties",
                None,
            )

            state = (
                getattr(
                    properties,
                    "provisioning_state",
                    None,
                )
                if properties
                else None
            )

            if (
                state
                and str(state).lower()
                == "succeeded"
            ):
                return {
                    "deployment_name": deployment_name,
                    "provisioning_state": str(state),
                }

            error = (
                getattr(
                    properties,
                    "error",
                    None,
                )
                if properties
                else None
            )

            return {
                "deployment_name": deployment_name,
                "provisioning_state": str(
                    state or "Failed"
                ),
                "error": str(
                    error
                    or "ARM deployment failed."
                ),
            }

        except Exception as exc:

            logger.exception(
                "Vulnerability Scan ARM deployment failed: %s",
                deployment_name,
            )

            return {
                "deployment_name": deployment_name,
                "provisioning_state": "Failed",
                "error": str(exc),
            }