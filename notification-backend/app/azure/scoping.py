

import json
import logging
import uuid

from pathlib import Path
from typing import Any, Dict, Optional, Set
from urllib.parse import quote, urlparse

import requests

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource.resources import ResourceManagementClient


logger = logging.getLogger(__name__)


class ScopingAzureManager:
    """
    Azure manager for Scoping deployment.

    Deployment order:

        1. Resolve existing resources
        2. Deploy Scoping-02
        3. Resolve Scoping-02 callback URL
        4. Deploy Scoping-00 + Scoping-01
           using the Scoping-02 callback URL
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
                    f"Azure REST request failed with "
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
        table_connection_name: str,
        queue_connection_name: str,
        sharepoint_connection_name: str,
    ) -> Dict[str, str]:

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
            resource_client.resources
            .list_by_resource_group(
                resource_group_name,
                filter=(
                    "resourceType eq "
                    "'Microsoft.Web/connections'"
                ),
            )
        )

        for connection in connections:

            connection_name = connection.name

            if connection_name == table_connection_name:

                table_connection_id = connection.id

            elif connection_name == queue_connection_name:

                queue_connection_id = connection.id

            elif connection_name == sharepoint_connection_name:

                sharepoint_connection_id = connection.id

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

        return {
            "table_connection_id": table_connection_id,
            "queue_connection_id": queue_connection_id,
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
            "table": f"{base}/azuretables",
            "queue": f"{base}/azurequeues",
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
                f"Unable to retrieve function keys for "
                f"function '{function_name}': {exc}"
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
            f"No function key found for "
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
                route = config.get("route")

        if not route:
            route = f"/api/{function_name}"

        route = str(route)

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
        process_asset_data_function_name: str,
        create_asset_groups_function_name: str,
        error_processor_function_name: str,
        check_working_hours_function_name: str,
    ) -> Dict[str, str]:

        return {

            "config_service_url": (
                self.get_function_url(
                    subscription_id,
                    resource_group_name,
                    function_app_name,
                    config_function_name,
                )
            ),

            "business_day_hour_status_url": (
                self.get_function_url(
                    subscription_id,
                    resource_group_name,
                    function_app_name,
                    business_day_hour_status_function_name,
                )
            ),

            "get_next_business_day_url": (
                self.get_function_url(
                    subscription_id,
                    resource_group_name,
                    function_app_name,
                    get_next_business_day_function_name,
                )
            ),

            "call_azure_function_url": (
                self.get_function_url(
                    subscription_id,
                    resource_group_name,
                    function_app_name,
                    call_azure_function_name,
                )
            ),

            "process_asset_data_url": (
                self.get_function_url(
                    subscription_id,
                    resource_group_name,
                    function_app_name,
                    process_asset_data_function_name,
                )
            ),

            "create_asset_groups_url": (
                self.get_function_url(
                    subscription_id,
                    resource_group_name,
                    function_app_name,
                    create_asset_groups_function_name,
                )
            ),

            "error_processor_url": (
                self.get_function_url(
                    subscription_id,
                    resource_group_name,
                    function_app_name,
                    error_processor_function_name,
                )
            ),

            "check_working_hours_url": (
                self.get_function_url(
                    subscription_id,
                    resource_group_name,
                    function_app_name,
                    check_working_hours_function_name,
                )
            ),
        }

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
                f"Unable to retrieve triggers from "
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
                f"Invalid trigger response for "
                f"Logic App '{logic_app_name}'."
            )

        selected_trigger = None

        requested = (
            trigger_name.strip().lower()
        )

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
                selected_trigger = request_triggers[0]

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

        actual_trigger_name = selected_trigger.get(
            "name"
        )

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
                f"Azure did not return a callback URL "
                f"for trigger '{actual_trigger_name}' "
                f"in Logic App '{logic_app_name}'."
            )

        return str(resolved_url)

    # ============================================================
    # DEPLOYMENT
    # ============================================================

    def deploy(
        self,
        request: Any,
        connections: Dict[str, str],
        function_urls: Dict[str, str],
        notification_service_url: str,
        completion_logic_app_url: str,
        scoping02_logic_app_url: Optional[str] = None,
        stages: Optional[Set[str]] = None,
    ) -> Dict[str, Any]:

        """
        Deploy selected Scoping Logic Apps.

        stages can contain:

            {"scoping02"}

        or:

            {"scoping00", "scoping01"}

        or all three.
        """

        if stages is None:

            stages = {
                "scoping02",
                "scoping00",
                "scoping01",
            }

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

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

        with open(
            template_path,
            "r",
            encoding="utf-8",
        ) as file:

            template = json.load(file)

        # ========================================================
        # FILTER ARM RESOURCES
        # ========================================================

        resources = template.get(
            "resources",
            [],
        )

        filtered_resources = []

        for resource in resources:

            resource_name = str(
                resource.get("name", "")
            )

            if (
                resource_name
                == "[parameters('scoping02LogicAppName')]"
            ):

                if "scoping02" in stages:
                    filtered_resources.append(resource)

            elif (
                resource_name
                == "[parameters('logicAppName')]"
            ):

                if "scoping00" in stages:
                    filtered_resources.append(resource)

            elif (
                resource_name
                == "[parameters('scoping01LogicAppName')]"
            ):

                if "scoping01" in stages:
                    filtered_resources.append(resource)

            else:

                # Preserve any non-Logic-App resources
                filtered_resources.append(resource)

        template["resources"] = filtered_resources

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

        managed_api_ids = (
            self._get_managed_api_ids(
                subscription_id=request.subscription_id,
                location=request.location,
            )
        )

        # ========================================================
        # REQUIRED FUNCTION URLS
        # ========================================================

        required_function_urls = {

            "Config Service Function URL":
                function_urls.get(
                    "config_service_url"
                ),

            "Business Day Hour Status Function URL":
                function_urls.get(
                    "business_day_hour_status_url"
                ),

            "Get Next Business Day Function URL":
                function_urls.get(
                    "get_next_business_day_url"
                ),

            "Call Azure Function URL":
                function_urls.get(
                    "call_azure_function_url"
                ),

            "Process Asset Data Function URL":
                function_urls.get(
                    "process_asset_data_url"
                ),

            "Create Asset Groups Function URL":
                function_urls.get(
                    "create_asset_groups_url"
                ),

            "Error Processor Function URL":
                function_urls.get(
                    "error_processor_url"
                ),

            "Check Working Hours Function URL":
                function_urls.get(
                    "check_working_hours_url"
                ),
        }

        for description, value in (
            required_function_urls.items()
        ):

            if not value:

                raise ValueError(
                    f"{description} could not be resolved."
                )

        # ========================================================
        # SCOPING-02 CALLBACK
        # ========================================================

        if (
            "scoping00" in stages
            or "scoping01" in stages
        ):

            if not scoping02_logic_app_url:

                raise ValueError(
                    "Scoping-02 callback URL is required "
                    "before deploying Scoping-00/01."
                )

        # ========================================================
        # ARM PARAMETERS
        # ========================================================

        parameters: Dict[str, Any] = {

            "logicAppName": {
                "value": request.logic_app_name,
            },

            "scoping01LogicAppName": {
                "value": request.scoping01_logic_app_name,
            },

            "scoping02LogicAppName": {
                "value": request.scoping02_logic_app_name,
            },

            "location": {
                "value": request.location,
            },

            "storageAccountName": {
                "value": request.storage_account_name,
            },

            "scopingScheduleQueueName": {
                "value": (
                    request.scoping_schedule_queue_name
                ),
            },

            "notificationLogTableName": {
                "value": (
                    request.notification_log_table_name
                ),
            },

            "NotificationStatus": {
                "value": request.notification_status,
            },

            "notificationServiceUrl": {
                "value": notification_service_url,
            },

            "configServiceUrl": {
                "value": function_urls[
                    "config_service_url"
                ],
            },

            "businessDayHourStatusUrl": {
                "value": function_urls[
                    "business_day_hour_status_url"
                ],
            },

            "getNextBusinessDayUrl": {
                "value": function_urls[
                    "get_next_business_day_url"
                ],
            },

            "callAzureFunctionUrl": {
                "value": function_urls[
                    "call_azure_function_url"
                ],
            },

            "processAssetDataUrl": {
                "value": function_urls[
                    "process_asset_data_url"
                ],
            },

            "createAssetGroupsUrl": {
                "value": function_urls[
                    "create_asset_groups_url"
                ],
            },

            "errorProcessorUrl": {
                "value": function_urls[
                    "error_processor_url"
                ],
            },

            "checkWorkingHoursUrl": {
                "value": function_urls[
                    "check_working_hours_url"
                ],
            },

            "scoping02LogicAppUrl": {
                "value": (
                    scoping02_logic_app_url
                    or ""
                ),
            },

            "sharePointUrl": {
                "value": request.share_point_url,
            },

            "completionLogicAppUrl": {
                "value": completion_logic_app_url,
            },

            "callbackSecretKey": {
                "value": request.callback_secret_key,
            },

            "$connections": {
                "value": {

                    request.table_connection_name: {
                        "connectionId":
                            table_connection_id,

                        "connectionName":
                            request.table_connection_name,

                        "id":
                            managed_api_ids["table"],
                    },

                    request.queue_connection_name: {
                        "connectionId":
                            queue_connection_id,

                        "connectionName":
                            request.queue_connection_name,

                        "id":
                            managed_api_ids["queue"],
                    },

                    request.sharepoint_connection_name: {
                        "connectionId":
                            sharepoint_connection_id,

                        "connectionName":
                            request.sharepoint_connection_name,

                        "id":
                            managed_api_ids["sharepoint"],
                    },
                }
            },
        }

        deployment_name = (
            f"scoping-{uuid.uuid4().hex[:8]}"
        )

        deployment_body = {
            "properties": {
                "mode": "Incremental",
                "template": template,
                "parameters": parameters,
            }
        }

        logger.info(
            "Deploying Scoping stage: %s",
            sorted(stages),
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
                "Scoping stage completed: "
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
                        error_message = str(error)

                return {
                    "deployment_name":
                        deployment_name,

                    "provisioning_state":
                        provisioning_state or "Failed",

                    "error":
                        error_message
                        or "ARM deployment failed.",
                }

            return {
                "deployment_name":
                    deployment_name,

                "provisioning_state":
                    provisioning_state,
            }

        except Exception as exc:

            logger.exception(
                "Scoping ARM deployment failed."
            )

            return {
                "deployment_name":
                    deployment_name,

                "provisioning_state":
                    "Failed",

                "error":
                    str(exc),
            }
