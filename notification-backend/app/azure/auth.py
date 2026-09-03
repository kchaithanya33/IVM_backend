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


class AuthScanAzureService:
    """
    Azure implementation for AuthScan deployment.

    IMPORTANT:
        AuthScan-02 is always deployed first.

        AuthScan-01 is deployed only after:
          1. AuthScan-02 ARM deployment succeeds.
          2. AuthScan-02 HTTP trigger callback URL is obtained.

        The callback URL is then supplied to AuthScan-01 through
        the ARM parameter 'authScan02LogicAppUrl'.
    """

    MANAGEMENT_API_VERSION = "2022-03-01"
    LOGIC_APP_API_VERSION = "2019-05-01"
    ARM_MANAGEMENT_URL = "https://management.azure.com"

    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()

    # =========================================================
    # AUTHENTICATION
    # =========================================================

    def _get_management_token(self) -> str:
        return self.credential.get_token(
            "https://management.azure.com/.default"
        ).token

    # =========================================================
    # MANAGEMENT REQUEST
    # =========================================================

    def _management_request(
        self,
        method: str,
        url: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        token = self._get_management_token()

        response = requests.request(
            method=method,
            url=url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=60,
        )

        if not response.ok:
            logger.error(
                "Azure Management request failed status=%s body=%s",
                response.status_code,
                response.text,
            )
            raise HttpResponseError(
                message=(
                    f"Azure REST request failed with status "
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

    # =========================================================
    # RESOURCE CLIENT
    # =========================================================

    def _resource_client(
        self,
        subscription_id: str,
    ) -> ResourceManagementClient:
        return ResourceManagementClient(
            self.credential,
            subscription_id,
        )

    # =========================================================
    # STORAGE
    # =========================================================

    def get_storage_account_name(
        self,
        subscription_id: str,
        resource_group_name: str,
    ) -> str:
        client = self._resource_client(subscription_id)

        resources = client.resources.list_by_resource_group(
            resource_group_name,
            filter=(
                "resourceType eq "
                "'Microsoft.Storage/storageAccounts'"
            ),
        )

        for resource in resources:
            if resource.name:
                logger.info(
                    "Storage account resolved: %s",
                    resource.name,
                )
                return str(resource.name)

        raise ValueError(
            f"No Azure Storage Account found in resource group "
            f"'{resource_group_name}'."
        )

    # =========================================================
    # API CONNECTIONS
    # =========================================================

    def get_connections(
        self,
        subscription_id: str,
        resource_group_name: str,
        table_connection_name: str,
        queue_connection_name: str,
        sharepoint_connection_name: str,
        office365_connection_name: str,
    ) -> Dict[str, str]:
        client = self._resource_client(subscription_id)

        wanted = {
            table_connection_name: "table_connection_id",
            queue_connection_name: "queue_connection_id",
            sharepoint_connection_name: "sharepoint_connection_id",
            office365_connection_name: "office365_connection_id",
        }

        found: Dict[str, str] = {}

        resources = client.resources.list_by_resource_group(
            resource_group_name,
            filter="resourceType eq 'Microsoft.Web/connections'",
        )

        for resource in resources:
            name = str(resource.name or "")
            if name in wanted and resource.id:
                found[wanted[name]] = str(resource.id)

        required = {
            "table_connection_id",
            "queue_connection_id",
            "sharepoint_connection_id",
            "office365_connection_id",
        }

        missing = [
            key for key in required
            if not found.get(key)
        ]

        if missing:
            raise ValueError(
                f"Required Azure API connection(s) not found: {missing}"
            )

        return found

    # =========================================================
    # MANAGED API IDS
    # =========================================================

    def _get_managed_api_ids(
        self,
        subscription_id: str,
        location: str,
    ) -> Dict[str, str]:
        sub = quote(subscription_id, safe="")
        loc = quote(location, safe="")

        base = (
            f"/subscriptions/{sub}"
            f"/providers/Microsoft.Web"
            f"/locations/{loc}/managedApis"
        )

        return {
            "table": f"{base}/azuretables",
            "queue": f"{base}/azurequeues",
            "sharepoint": f"{base}/sharepointonline",
            "office365": f"{base}/office365",
        }

    # =========================================================
    # CONNECTION PARAMETER
    # =========================================================

    def _build_connections_parameter(
        self,
        request: Any,
        connections: Dict[str, str],
    ) -> Dict[str, Any]:
        managed = self._get_managed_api_ids(
            request.subscription_id,
            request.location,
        )

        return {
            request.table_connection_name: {
                "connectionId": connections["table_connection_id"],
                "connectionName": request.table_connection_name,
                "id": managed["table"],
            },
            request.queue_connection_name: {
                "connectionId": connections["queue_connection_id"],
                "connectionName": request.queue_connection_name,
                "id": managed["queue"],
            },
            request.sharepoint_connection_name: {
                "connectionId": connections["sharepoint_connection_id"],
                "connectionName": request.sharepoint_connection_name,
                "id": managed["sharepoint"],
            },
            request.office365_connection_name: {
                "connectionId": connections["office365_connection_id"],
                "connectionName": request.office365_connection_name,
                "id": managed["office365"],
            },
        }

    # =========================================================
    # FUNCTION URL
    # =========================================================

    def get_function_resource(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> Dict[str, Any]:
        url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}/resourceGroups/"
            f"{quote(resource_group_name, safe='')}/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name, safe='')}/functions/"
            f"{quote(function_name, safe='')}?api-version="
            f"{self.MANAGEMENT_API_VERSION}"
        )

        try:
            return self._management_request("GET", url)
        except Exception as exc:
            raise ValueError(
                f"Unable to retrieve function '{function_name}' "
                f"from Function App '{function_app_name}': {exc}"
            ) from exc

    def get_function_key(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> str:
        url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}/resourceGroups/"
            f"{quote(resource_group_name, safe='')}/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name, safe='')}/functions/"
            f"{quote(function_name, safe='')}/listKeys?api-version="
            f"{self.MANAGEMENT_API_VERSION}"
        )

        try:
            result = self._management_request("POST", url, {})
        except Exception as exc:
            raise ValueError(
                f"Unable to retrieve key for function "
                f"'{function_name}': {exc}"
            ) from exc

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
            f"No function key found for '{function_name}'."
        )

    def get_function_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> str:
        function_resource = self.get_function_resource(
            subscription_id,
            resource_group_name,
            function_app_name,
            function_name,
        )

        properties = function_resource.get("properties", {})
        route = None

        if isinstance(properties, dict):
            route = properties.get("invokeUrlTemplate")
            if not route:
                route = properties.get("invoke_url_template")

        if not route:
            route = f"/api/{function_name}"

        route = str(route)

        site_url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}/resourceGroups/"
            f"{quote(resource_group_name, safe='')}/providers/Microsoft.Web/sites/"
            f"{quote(function_app_name, safe='')}?api-version="
            f"{self.MANAGEMENT_API_VERSION}"
        )

        site = self._management_request("GET", site_url)
        site_properties = site.get("properties", {})

        hostname = None
        if isinstance(site_properties, dict):
            hostname = site_properties.get("defaultHostName")

        if not hostname:
            hostname = f"{function_app_name}.azurewebsites.net"

        if route.startswith(("http://", "https://")):
            parsed = urlparse(route)
            route = parsed.path
            if parsed.query:
                route = f"{route}?{parsed.query}"

        if not route.startswith("/"):
            route = "/" + route

        if not route.startswith("/api/"):
            if route != "/api":
                route = "/api" + route

        key = self.get_function_key(
            subscription_id,
            resource_group_name,
            function_app_name,
            function_name,
        )

        separator = "&" if "?" in route else "?"

        return (
            f"https://{hostname}{route}"
            f"{separator}code={quote(key, safe='')}"
        )

    def get_function_urls(
        self,
        request: Any,
    ) -> Dict[str, str]:
        kwargs = {
            "subscription_id": request.subscription_id,
            "resource_group_name": request.resource_group_name,
            "function_app_name": request.function_app_name,
        }

        return {
            "config_service_url": self.get_function_url(
                **kwargs,
                function_name=request.config_service_function_name,
            ),
            "excelipexractor": self.get_function_url(
    **kwargs,
    function_name=request.excelipexractor,
),
            "business_days_service_url": self.get_function_url(
                **kwargs,
                function_name=request.business_days_service_function_name,
            ),
            "get_next_business_day_url": self.get_function_url(
                **kwargs,
                function_name=request.get_next_business_day_function_name,
            ),
            "qualys_scan_fetch_function_url": self.get_function_url(
                **kwargs,
                function_name=request.qualys_scan_fetch_function_name,
            ),
            "qualys_auth_function_url": self.get_function_url(
                **kwargs,
                function_name=request.qualys_auth_function_name,
            ),
            "qualys_auth_failure_analysis_function_url": self.get_function_url(
                **kwargs,
                function_name=request.qualys_auth_failure_analysis_function_name,
            ),
        }

    # =========================================================
    # LOGIC APP CALLBACK URL
    # =========================================================

    def get_logic_app_triggers(
        self,
        subscription_id: str,
        resource_group_name: str,
        logic_app_name: str,
    ) -> Dict[str, Any]:
        url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}/resourceGroups/"
            f"{quote(resource_group_name, safe='')}/providers/Microsoft.Logic/workflows/"
            f"{quote(logic_app_name, safe='')}/triggers?api-version="
            f"{self.LOGIC_APP_API_VERSION}"
        )
        return self._management_request("GET", url)

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

        triggers = response.get("value", [])
        if not isinstance(triggers, list):
            raise ValueError(
                f"Invalid trigger response for Logic App "
                f"'{logic_app_name}'."
            )

        requested = trigger_name.strip().lower()
        selected = None

        # Exact trigger resource name.
        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue
            name = str(trigger.get("name", ""))
            if name.strip().lower() == requested:
                selected = trigger
                break

        # Display/title/description fallback.
        if selected is None:
            for trigger in triggers:
                if not isinstance(trigger, dict):
                    continue
                props = trigger.get("properties", {})
                if not isinstance(props, dict):
                    continue

                for candidate in (
                    props.get("displayName"),
                    props.get("title"),
                    props.get("description"),
                ):
                    if (
                        candidate
                        and str(candidate).strip().lower() == requested
                    ):
                        selected = trigger
                        break

                if selected:
                    break

        # If only one Request trigger exists, use it.
        if selected is None:
            request_triggers = []

            for trigger in triggers:
                if not isinstance(trigger, dict):
                    continue
                props = trigger.get("properties", {})
                if not isinstance(props, dict):
                    continue

                if str(props.get("type", "")).lower() == "request":
                    request_triggers.append(trigger)

            if len(request_triggers) == 1:
                selected = request_triggers[0]

        if selected is None:
            available = [
                str(item.get("name"))
                for item in triggers
                if isinstance(item, dict)
            ]
            raise ValueError(
                f"Trigger '{trigger_name}' not found in Logic App "
                f"'{logic_app_name}'. Available triggers: {available}"
            )

        actual_name = selected.get("name")
        if not actual_name:
            raise ValueError(
                f"Trigger '{trigger_name}' does not contain a valid name."
            )

        url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}/resourceGroups/"
            f"{quote(resource_group_name, safe='')}/providers/Microsoft.Logic/workflows/"
            f"{quote(logic_app_name, safe='')}/triggers/"
            f"{quote(str(actual_name), safe='')}/listCallbackUrl?api-version="
            f"{self.LOGIC_APP_API_VERSION}"
        )

        callback = self._management_request("POST", url, {})

        value = callback.get("value") or callback.get("callbackUrl")
        if not value:
            raise ValueError(
                f"Azure did not return callback URL for trigger "
                f"'{actual_name}'."
            )

        return str(value)

    # =========================================================
    # TEMPLATE
    # =========================================================

    def _load_template(self) -> Dict[str, Any]:
        template_path = (
            Path(__file__).resolve().parents[2]
            / "arm"
            / "AuthScan.json"
        )

        if not template_path.exists():
            raise FileNotFoundError(
                f"AuthScan ARM template not found. Expected: {template_path}"
            )

        with template_path.open("r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {template_path}"
                ) from exc

    # =========================================================
    # ARM PARAMETER BUILDING
    # =========================================================

    def _template_parameter_names(
        self,
        template: Dict[str, Any],
    ) -> set[str]:
        parameters = template.get("parameters", {})

        if not isinstance(parameters, dict):
            raise ValueError(
                "AuthScan.json has no valid 'parameters' object."
            )

        return set(parameters.keys())

    def _all_parameter_values(
        self,
        request: Any,
        storage_account_name: str,
        connections: Dict[str, str],
        function_urls: Dict[str, str],
        notification_service_url: str,
        auth_scan02_logic_app_url: str,
    ) -> Dict[str, Any]:
        return {
            "logicApp1Name": request.auth_scan01_logic_app_name,
            "logicApp2Name": request.auth_scan02_logic_app_name,
            "location": request.location,
            "storageAccountName": storage_account_name,

            "configServiceUrl": function_urls["config_service_url"],
            "businessDaysServiceUrl": function_urls["business_days_service_url"],
            "getNextBusinessDayUrl": function_urls["get_next_business_day_url"],
            "qualysScanFetchFunctionUrl": function_urls[
                "qualys_scan_fetch_function_url"
            ],
            "qualysAuthFunctionUrl": function_urls[
                "qualys_auth_function_url"
            ],
            "qualysAuthFailureAnalysisFunctionUrl": function_urls[
                "qualys_auth_failure_analysis_function_url"
            ],

            "notificationServiceUrl": notification_service_url,

            # EMPTY during AuthScan-02 deployment.
            # REAL CALLBACK URL during AuthScan-01 deployment.
            "authScan02LogicAppUrl": auth_scan02_logic_app_url,

            "authscanqueue": request.authscan_queue_name,
            "authScanExecutionQueueName": request.auth_scan_execution_queue_name,
            "qualysScanStatusQueueName": request.qualys_scan_status_queue_name,
            "vulnscanqueue": request.vulnscan_queue_name,

            "auditLogTableName": request.audit_log_table_name,
            "authScanResultsTableName": request.auth_scan_results_table_name,
            "cycleTableName": request.cycle_table_name,

            "authScanProfile": request.auth_scan_profile,
            "qualysScannerName": request.qualys_scanner_name,
            "scannerId": request.scanner_id,
            "meyDiageoScanner": request.mey_diageo_scanner,
            "diageoScanners": request.diageo_scanners,

            "qualysApiUrl": request.qualys_api_url or "",
            "qualysDashboardUrl": (
                request.qualys_dashboard_url
                or "https://qualysguard.qualys.eu/"
            ),
            "servicenowApiUrl": request.servicenow_api_url or "",
            "mulesoftApiKey": request.mulesoft_api_key or "",
            "excelipexractor": function_urls["excelipexractor"],
            "vulnScanTriggerUrl": request.vuln_scan_trigger_url or "",
            "assetServiceUrl": request.asset_service_url or "",
            "keyVaultUrl": request.key_vault_url or "",

            "$connections": self._build_connections_parameter(
                request,
                connections,
            ),
        }

    def _build_parameters(
        self,
        request: Any,
        template: Dict[str, Any],
        storage_account_name: str,
        connections: Dict[str, str],
        function_urls: Dict[str, str],
        notification_service_url: str,
        auth_scan02_logic_app_url: str,
    ) -> Dict[str, Any]:
        template_names = self._template_parameter_names(template)

        all_values = self._all_parameter_values(
            request=request,
            storage_account_name=storage_account_name,
            connections=connections,
            function_urls=function_urls,
            notification_service_url=notification_service_url,
            auth_scan02_logic_app_url=auth_scan02_logic_app_url,
        )

        parameters = {
            name: {"value": all_values[name]}
            for name in template_names
            if name in all_values
        }

        missing = []
        template_parameters = template.get("parameters", {})

        if isinstance(template_parameters, dict):
            for name, definition in template_parameters.items():
                if not isinstance(definition, dict):
                    continue

                if (
                    name not in parameters
                    and "defaultValue" not in definition
                ):
                    missing.append(name)

        if missing:
            raise ValueError(
                "AuthScan ARM template contains required parameters "
                f"that the backend did not supply: {missing}"
            )

        return parameters

    # =========================================================
    # RESOURCE SELECTION
    # =========================================================

    def _select_logic_app_resource(
        self,
        template: Dict[str, Any],
        logic_app_parameter: str,
    ) -> Dict[str, Any]:
        resources = template.get("resources", [])

        if not isinstance(resources, list):
            raise ValueError(
                "AuthScan.json resources must be an array."
            )

        expected_name = f"[parameters('{logic_app_parameter}')]"

        for resource in resources:
            if not isinstance(resource, dict):
                continue

            if resource.get("type") != "Microsoft.Logic/workflows":
                continue

            if resource.get("name") == expected_name:
                return resource

        raise ValueError(
            f"Could not find Logic App resource using parameter "
            f"'{logic_app_parameter}'."
        )

    # =========================================================
    # ARM DEPLOYMENT OPERATIONS / DIAGNOSTICS
    # =========================================================

    def _get_deployment_operations(
        self,
        subscription_id: str,
        resource_group_name: str,
        deployment_name: str,
    ) -> list[Dict[str, Any]]:
        url = (
            f"{self.ARM_MANAGEMENT_URL}/subscriptions/"
            f"{quote(subscription_id, safe='')}/resourceGroups/"
            f"{quote(resource_group_name, safe='')}/providers/"
            f"Microsoft.Resources/deployments/{quote(deployment_name, safe='')}/"
            f"operations?api-version=2022-09-01"
        )

        try:
            result = self._management_request("GET", url)
            value = result.get("value", [])
            return value if isinstance(value, list) else []
        except Exception:
            logger.exception(
                "Unable to retrieve deployment operations for %s",
                deployment_name,
            )
            return []

    @staticmethod
    def _format_deployment_error(
        operations: list[Dict[str, Any]],
    ) -> str:
        errors = []

        for operation in operations:
            props = operation.get("properties", {})
            if not isinstance(props, dict):
                continue

            status_message = props.get("statusMessage")
            if not status_message:
                continue

            if isinstance(status_message, dict):
                code = status_message.get("error", {}).get("code")
                message = status_message.get("error", {}).get("message")

                if code or message:
                    errors.append(
                        f"{code or 'DeploymentError'}: {message or status_message}"
                    )
                else:
                    errors.append(json.dumps(status_message))
            else:
                errors.append(str(status_message))

        return "\n".join(errors)

    # =========================================================
    # DEPLOY ONE LOGIC APP
    # =========================================================

    def _deploy_logic_app(
        self,
        request: Any,
        deployment_name: str,
        template: Dict[str, Any],
        parameters: Dict[str, Any],
        logic_app_parameter: str,
    ) -> Dict[str, Any]:
        selected_resource = self._select_logic_app_resource(
            template,
            logic_app_parameter,
        )

        phase_template = dict(template)
        phase_template["resources"] = [selected_resource]

        deployment_body = {
            "properties": {
                "mode": "Incremental",
                "template": phase_template,
                "parameters": parameters,
            }
        }

        client = self._resource_client(request.subscription_id)

        logger.info(
            "Deploying Logic App phase=%s deployment=%s",
            logic_app_parameter,
            deployment_name,
        )

        try:
            deployment = client.deployments.begin_create_or_update(
                request.resource_group_name,
                deployment_name,
                deployment_body,
            )
            result = deployment.result()
        except Exception as exc:
            operations = self._get_deployment_operations(
                request.subscription_id,
                request.resource_group_name,
                deployment_name,
            )
            details = self._format_deployment_error(operations)

            if details:
                raise RuntimeError(
                    f"ARM deployment '{deployment_name}' failed.\n{details}"
                ) from exc

            raise

        state = None
        if result.properties:
            state = result.properties.provisioning_state

        if str(state).lower() != "succeeded":
            operations = self._get_deployment_operations(
                request.subscription_id,
                request.resource_group_name,
                deployment_name,
            )
            details = self._format_deployment_error(operations)

            raise RuntimeError(
                f"ARM deployment '{deployment_name}' failed with state "
                f"'{state}'."
                + (f"\n{details}" if details else "")
            )

        logger.info(
            "Logic App deployment succeeded: %s state=%s",
            deployment_name,
            state,
        )

        return {
            "deployment_name": deployment_name,
            "provisioning_state": state,
        }

    # =========================================================
    # MAIN DEPLOYMENT
    # =========================================================

    def deploy(self, request: Any) -> Dict[str, Any]:
        logger.info(
            "START AuthScan deployment: AuthScan-02 -> AuthScan-01"
        )

        # -----------------------------------------------------
        # 1. RESOLVE STORAGE
        # -----------------------------------------------------
        storage_account_name = request.storage_account_name

        if not storage_account_name:
            storage_account_name = self.get_storage_account_name(
                request.subscription_id,
                request.resource_group_name,
            )

        # -----------------------------------------------------
        # 2. RESOLVE CONNECTIONS
        # -----------------------------------------------------
        connections = self.get_connections(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            table_connection_name=request.table_connection_name,
            queue_connection_name=request.queue_connection_name,
            sharepoint_connection_name=request.sharepoint_connection_name,
            office365_connection_name=request.office365_connection_name,
        )

        # -----------------------------------------------------
        # 3. RESOLVE FUNCTION URLS
        # -----------------------------------------------------
        function_urls = self.get_function_urls(request)

        # -----------------------------------------------------
        # 4. RESOLVE EXISTING NOTIFICATION CALLBACK
        # -----------------------------------------------------
        notification_service_url = self.get_logic_app_callback_url(
            subscription_id=request.subscription_id,
            resource_group_name=request.resource_group_name,
            logic_app_name=request.notification_logic_app_name,
            trigger_name=request.notification_logic_app_trigger_name,
        )

        # -----------------------------------------------------
        # 5. LOAD TEMPLATE
        # -----------------------------------------------------
        template = self._load_template()

        # =====================================================
        # PHASE 1: AUTHSCAN-02
        # =====================================================
        logger.info("PHASE 1: Deploying AuthScan-02")

        auth02_deployment_name = (
            f"authscan02-{uuid.uuid4().hex[:8]}"
        )

        # AuthScan-02 does NOT need its own callback URL.
        # AuthScan-01 is the consumer of AuthScan-02 callback.
        auth02_parameters = self._build_parameters(
            request=request,
            template=template,
            storage_account_name=storage_account_name,
            connections=connections,
            function_urls=function_urls,
            notification_service_url=notification_service_url,
            auth_scan02_logic_app_url="",
        )

        auth02_result = self._deploy_logic_app(
            request=request,
            deployment_name=auth02_deployment_name,
            template=template,
            parameters=auth02_parameters,
            logic_app_parameter="logicApp2Name",
        )

        if str(
            auth02_result["provisioning_state"]
        ).lower() != "succeeded":
            raise RuntimeError(
                "AuthScan-02 deployment did not succeed; "
                "AuthScan-01 will not be deployed."
            )

        logger.info(
            "PHASE 1 COMPLETE: AuthScan-02 deployed successfully."
        )

        # =====================================================
        # PHASE 2: GET AUTHSCAN-02 CALLBACK URL
        # =====================================================
        logger.info(
            "PHASE 2: Resolving AuthScan-02 HTTP callback URL"
        )

        auth_scan02_logic_app_url = (
            self.get_logic_app_callback_url(
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                logic_app_name=request.auth_scan02_logic_app_name,
                trigger_name=request.auth_scan02_logic_app_trigger_name,
            )
        )

        if not auth_scan02_logic_app_url:
            raise RuntimeError(
                "AuthScan-02 callback URL was not returned; "
                "AuthScan-01 will not be deployed."
            )

        logger.info(
            "PHASE 2 COMPLETE: AuthScan-02 callback URL resolved."
        )

        # =====================================================
        # PHASE 3: AUTHSCAN-01
        # =====================================================
        logger.info(
            "PHASE 3: Deploying AuthScan-01 using AuthScan-02 callback URL"
        )

        auth01_deployment_name = (
            f"authscan01-{uuid.uuid4().hex[:8]}"
        )

        auth01_parameters = self._build_parameters(
            request=request,
            template=template,
            storage_account_name=storage_account_name,
            connections=connections,
            function_urls=function_urls,
            notification_service_url=notification_service_url,
            auth_scan02_logic_app_url=auth_scan02_logic_app_url,
        )

        # Explicit safety check: never deploy AuthScan-01 without
        # the callback URL obtained after AuthScan-02.
        if not auth01_parameters.get("authScan02LogicAppUrl", {}).get("value"):
            raise RuntimeError(
                "authScan02LogicAppUrl is empty. "
                "AuthScan-01 deployment has been stopped."
            )

        auth01_result = self._deploy_logic_app(
            request=request,
            deployment_name=auth01_deployment_name,
            template=template,
            parameters=auth01_parameters,
            logic_app_parameter="logicApp1Name",
        )

        if str(
            auth01_result["provisioning_state"]
        ).lower() != "succeeded":
            raise RuntimeError(
                "AuthScan-01 deployment did not succeed."
            )

        logger.info(
            "PHASE 3 COMPLETE: AuthScan-01 deployed successfully."
        )

        # =====================================================
        # RESPONSE
        # =====================================================
        return {
            "success": True,
            "message": (
                "AuthScan-02 was deployed first, its HTTP callback "
                "URL was retrieved, and AuthScan-01 was then deployed "
                "with that callback URL."
            ),
            "subscription_id": request.subscription_id,
            "resource_group_name": request.resource_group_name,
            "location": request.location,
            "auth_scan01_logic_app_name": request.auth_scan01_logic_app_name,
            "auth_scan02_logic_app_name": request.auth_scan02_logic_app_name,
            "storage_account_name": storage_account_name,
            "auth_scan02_deployment_name": auth02_result[
                "deployment_name"
            ],
            "auth_scan01_deployment_name": auth01_result[
                "deployment_name"
            ],
            "auth_scan02_provisioning_state": auth02_result[
                "provisioning_state"
            ],
            "auth_scan01_provisioning_state": auth01_result[
                "provisioning_state"
            ],
            "table_connection_id": connections["table_connection_id"],
            "queue_connection_id": connections["queue_connection_id"],
            "sharepoint_connection_id": connections[
                "sharepoint_connection_id"
            ],
            "office365_connection_id": connections[
                "office365_connection_id"
            ],
            "function_urls": function_urls,
            "logic_app_urls": {
                "notification_service_url": notification_service_url,
                "auth_scan02_logic_app_url": auth_scan02_logic_app_url,
            },
        }
