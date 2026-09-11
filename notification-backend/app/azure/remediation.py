import json
import logging
import uuid

from pathlib import Path
from typing import Any, Dict

import requests

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource.resources import ResourceManagementClient


logger = logging.getLogger(__name__)


# ============================================================
# REMEDIATION AZURE MANAGER
# ============================================================

class RemediationAzureManager:

    MANAGEMENT_API_VERSION = "2022-03-01"
    LOGIC_APP_API_VERSION = "2019-05-01"

    ARM_MANAGEMENT_URL = "https://management.azure.com"

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()

    # ========================================================
    # MANAGEMENT TOKEN
    # ========================================================

    def _get_management_token(self) -> str:

        token = self.credential.get_token(
            "https://management.azure.com/.default"
        )

        return token.token

    # ========================================================
    # MANAGEMENT REQUEST
    # ========================================================

    def _management_request(
        self,
        method: str,
        url: str,
        body: Dict[str, Any] | None = None,
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
            raise HttpResponseError(
                response=response
            )

        if not response.content:
            return {}

        return response.json()

    # ========================================================
    # GET CONNECTIONS
    # ========================================================

    def get_connections(
        self,
        subscription_id: str,
        resource_group_name: str,
        table_connection_name: str,
        queue_connection_name: str,
    ) -> Dict[str, str]:

        logger.info(
            "Getting Azure API connections: table=%s queue=%s",
            table_connection_name,
            queue_connection_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        resources = resource_client.resources.list_by_resource_group(
            resource_group_name,
            filter="resourceType eq 'Microsoft.Web/connections'",
        )

        table_connection_id = None
        queue_connection_id = None

        for resource in resources:

            if resource.name == table_connection_name:
                table_connection_id = resource.id

            elif resource.name == queue_connection_name:
                queue_connection_id = resource.id

        missing = []

        if not table_connection_id:
            missing.append(table_connection_name)

        if not queue_connection_id:
            missing.append(queue_connection_name)

        if missing:
            raise ValueError(
                "Required Azure API connection(s) not found: "
                + ", ".join(missing)
            )

        return {
            "table_connection_id": table_connection_id,
            "queue_connection_id": queue_connection_id,
        }

    # ========================================================
    # GET FUNCTION RESOURCE
    # ========================================================

    def get_function_resource(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> Dict[str, Any]:

        url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Web/sites/{function_app_name}"
            f"/functions/{function_name}"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        try:
            return self._management_request(
                "GET",
                url,
            )

        except Exception as exc:

            logger.exception(
                "Failed to get Function resource: %s/%s",
                function_app_name,
                function_name,
            )

            raise RuntimeError(
                f"Unable to get Azure Function "
                f"'{function_name}' from Function App "
                f"'{function_app_name}': {exc}"
            ) from exc

    # ========================================================
    # GET FUNCTION KEY
    # ========================================================

    def get_function_key(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> str:

        url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Web/sites/{function_app_name}"
            f"/functions/{function_name}"
            f"/listKeys"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        try:
            result = self._management_request(
                "POST",
                url,
            )

        except Exception as exc:

            logger.exception(
                "Failed to get Function key: %s/%s",
                function_app_name,
                function_name,
            )

            raise RuntimeError(
                f"Unable to get key for Azure Function "
                f"'{function_name}' in Function App "
                f"'{function_app_name}': {exc}"
            ) from exc

        keys = result.get("keys", {})

        function_key = keys.get("default")

        if not function_key and keys:
            function_key = next(iter(keys.values()))

        if not function_key:
            function_key = result.get("default")

        if not function_key:
            raise RuntimeError(
                f"No function key found for "
                f"{function_app_name}/{function_name}"
            )

        return function_key

    # ========================================================
    # GET FUNCTION URL
    # ========================================================

    def get_function_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> str:

        logger.info(
            "Resolving Function URL: app=%s function=%s",
            function_app_name,
            function_name,
        )

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

        route = (
            properties.get("invokeUrlTemplate")
            or properties.get("invoke_url_template")
            or properties.get("config", {}).get("route")
        )

        if not route:
            route = f"/api/{function_name}"

        # ----------------------------------------------------
        # Get Function App hostname
        # ----------------------------------------------------

        site_url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Web/sites/{function_app_name}"
            f"?api-version={self.MANAGEMENT_API_VERSION}"
        )

        site_resource = self._management_request(
            "GET",
            site_url,
        )

        site_properties = site_resource.get(
            "properties",
            {},
        )

        hostname = site_properties.get(
            "defaultHostName"
        )

        if not hostname:
            hostname = (
                f"{function_app_name}.azurewebsites.net"
            )

        # ----------------------------------------------------
        # Normalize route
        # ----------------------------------------------------

        if route.startswith("https://"):

            from urllib.parse import urlparse

            parsed = urlparse(route)

            route = parsed.path

            if parsed.query:
                route = f"{route}?{parsed.query}"

        if not route.startswith("/"):
            route = f"/{route}"

        if not route.startswith("/api/"):
            if route == "/api":
                pass
            elif route.startswith("/api"):
                pass
            else:
                route = f"/api{route}"

        # ----------------------------------------------------
        # Get Function Key
        # ----------------------------------------------------

        function_key = self.get_function_key(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            function_name=function_name,
        )

        # ----------------------------------------------------
        # Add code parameter
        # ----------------------------------------------------

        separator = "&" if "?" in route else "?"

        return (
            f"https://{hostname}"
            f"{route}"
            f"{separator}"
            f"code={function_key}"
        )

    # ========================================================
    # GET ALL REMEDIATION FUNCTION URLS
    # ========================================================

    def get_function_urls(
        self,
        subscription_id: str,
        resource_group_name: str,
        config_function_app_name: str,
        config_function_name: str,
        qualys_asset_group_function_app_name: str,
        qualys_asset_group_function_name: str,
        qualys_scan_function_app_name: str,
        qualys_scan_function_name: str,
    ) -> Dict[str, str]:

        logger.info(
            "Resolving Remediation Function URLs"
        )

        config_service_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=config_function_app_name,
            function_name=config_function_name,
        )

        qualys_asset_group_creation_function_url = (
            self.get_function_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                function_app_name=qualys_asset_group_function_app_name,
                function_name=qualys_asset_group_function_name,
            )
        )

        qualys_scan_function_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=qualys_scan_function_app_name,
            function_name=qualys_scan_function_name,
        )

        return {
            "config_service_url": config_service_url,
            "qualys_asset_group_creation_function_url":
                qualys_asset_group_creation_function_url,
            "qualys_scan_function_url":
                qualys_scan_function_url,
        }

    # ========================================================
    # DEPLOY REMEDIATION ARM
    # ========================================================

    def deploy(
        self,
        request,
        connections: Dict[str, str],
        function_urls: Dict[str, str],
    ) -> Dict[str, Any]:

        logger.info(
            "Starting Remediation deployment: %s",
            request.logic_app_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        # ----------------------------------------------------
        # Load ARM template
        # ----------------------------------------------------

        template_path = (
            Path(__file__).resolve().parents[2]
            / "arm"
            / "remediation.json"
        )

        if not template_path.exists():
            raise FileNotFoundError(
                f"Remediation ARM template not found: "
                f"{template_path}"
            )

        with open(
            template_path,
            "r",
            encoding="utf-8",
        ) as file:

            template = json.load(file)

        # ----------------------------------------------------
        # Managed API IDs
        # ----------------------------------------------------

        subscription_id = request.subscription_id
        location = request.location

        azure_tables_api_id = (
            f"/subscriptions/{subscription_id}"
            f"/providers/Microsoft.Web/locations/{location}"
            f"/managedApis/azuretables"
        )

        azure_queues_api_id = (
            f"/subscriptions/{subscription_id}"
            f"/providers/Microsoft.Web/locations/{location}"
            f"/managedApis/azurequeues"
        )

        # ----------------------------------------------------
        # ARM parameters
        # ----------------------------------------------------

        parameters = {
            "LA-Remediation-02": {
                "value": request.logic_app_name
            },

            "location": {
                "value": request.location
            },

            "storageAccountName": {
                "value": request.storage_account_name
            },

            "auditLogTableName": {
                "value": request.audit_log_table_name
            },

            "configServiceUrl": {
                "value": function_urls[
                    "config_service_url"
                ]
            },

            "qualysAssetGroupCreationFunctionUrl": {
                "value": function_urls[
                    "qualys_asset_group_creation_function_url"
                ]
            },

            "qualysScanFunctionUrl": {
                "value": function_urls[
                    "qualys_scan_function_url"
                ]
            },

            "qualysScanStatusQueueName": {
                "value": request.qualys_scan_status_queue_name
            },

            "$connections": {
                "value": {

                    "azuretables-1": {
                        "connectionId": connections[
                            "table_connection_id"
                        ],
                        "connectionName":
                            request.table_connection_name,
                        "id":
                            azure_tables_api_id,
                    },

                    "azurequeues-1": {
                        "connectionId": connections[
                            "queue_connection_id"
                        ],
                        "connectionName":
                            request.queue_connection_name,
                        "id":
                            azure_queues_api_id,
                    },
                }
            },
        }

        # ----------------------------------------------------
        # Deployment object
        # ----------------------------------------------------

        deployment_properties = {
            "mode": "Incremental",
            "template": template,
            "parameters": parameters,
        }

        deployment_name = (
            f"remediation-{uuid.uuid4().hex[:8]}"
        )

        logger.info(
            "Creating ARM deployment: %s",
            deployment_name,
        )

        try:

            poller = (
    resource_client.deployments
    .begin_create_or_update(
        request.resource_group_name,
        deployment_name,
        {
            "properties": deployment_properties
        },
    )
)

            deployment_result = poller.result()

            provisioning_state = (
                deployment_result.properties
                .provisioning_state
            )

            logger.info(
                "Remediation deployment completed: "
                "name=%s state=%s",
                deployment_name,
                provisioning_state,
            )

            if provisioning_state != "Succeeded":

                return {
                    "success": False,
                    "deployment_name": deployment_name,
                    "provisioning_state":
                        provisioning_state,
                    "error": (
                        "ARM deployment did not succeed"
                    ),
                }

            return {
                "success": True,
                "deployment_name": deployment_name,
                "provisioning_state":
                    provisioning_state,
            }

        except Exception as exc:

            logger.exception(
                "Remediation ARM deployment failed"
            )

            return {
                "success": False,
                "deployment_name": deployment_name,
                "provisioning_state": "Failed",
                "error": str(exc),
            }