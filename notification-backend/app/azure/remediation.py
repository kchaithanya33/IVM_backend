
import json
import logging
import uuid

from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

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
            {}
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
    # Existing Remediation-02 logic untouched
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
    # GET REMEDIATION 01 FUNCTION URLS
    # ========================================================

    def get_remediation_01_function_urls(
        self,
        subscription_id: str,
        resource_group_name: str,
        excel_processing_function_app_name: str,
        excel_processing_function_name: str,
        qualys_qid_option_profile_function_app_name: str,
        qualys_qid_option_profile_function_name: str,
        dfn_file_content_function_app_name: str,
        dfn_file_content_function_name: str,
        cmdb_ip_extractor_function_app_name: str,
        cmdb_ip_extractor_function_name: str,
        all_ip_qid_extractor_function_app_name: str,
        all_ip_qid_extractor_function_name: str,
    ) -> Dict[str, str]:

        logger.info(
            "Resolving Remediation-01 Function URLs"
        )

        excel_processing_function_url = (
            self.get_function_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                function_app_name=excel_processing_function_app_name,
                function_name=excel_processing_function_name,
            )
        )

        qualys_qid_option_profile_url = (
            self.get_function_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                function_app_name=qualys_qid_option_profile_function_app_name,
                function_name=qualys_qid_option_profile_function_name,
            )
        )

        dfn_file_content_function_url = (
            self.get_function_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                function_app_name=dfn_file_content_function_app_name,
                function_name=dfn_file_content_function_name,
            )
        )

        cmdb_ip_extractor_function_url = (
            self.get_function_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                function_app_name=cmdb_ip_extractor_function_app_name,
                function_name=cmdb_ip_extractor_function_name,
            )
        )

        all_ip_qid_extractor_function_url = (
            self.get_function_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                function_app_name=all_ip_qid_extractor_function_app_name,
                function_name=all_ip_qid_extractor_function_name,
            )
        )

        return {
            "excel_processing_function_url":
                excel_processing_function_url,
            "qualys_qid_option_profile_url":
                qualys_qid_option_profile_url,
            "dfn_file_content_function_url":
                dfn_file_content_function_url,
            "cmdb_ip_extractor_function_url":
                cmdb_ip_extractor_function_url,
            "all_ip_qid_extractor_function_url":
                all_ip_qid_extractor_function_url,
        }

    # ========================================================
    # GET LOGIC APP CALLBACK URL
    # ========================================================

    def get_logic_app_callback_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        logic_app_name: str,
        trigger_name: str,
    ) -> str:

        logger.info(
            "Resolving Logic App callback URL: app=%s trigger=%s",
            logic_app_name,
            trigger_name,
        )

        url = (
            f"{self.ARM_MANAGEMENT_URL}"
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Logic/workflows/"
            f"{logic_app_name}/triggers/{trigger_name}/"
            f"listCallbackUrl"
            f"?api-version={self.LOGIC_APP_API_VERSION}"
        )

        try:

            result = self._management_request(
                "POST",
                url,
            )

        except Exception as exc:

            logger.exception(
                "Failed to get Logic App callback URL: %s/%s",
                logic_app_name,
                trigger_name,
            )

            raise RuntimeError(
                f"Unable to get callback URL for Logic App "
                f"'{logic_app_name}' trigger "
                f"'{trigger_name}': {exc}"
            ) from exc

        callback_url = result.get("value")

        if not callback_url:
            raise RuntimeError(
                f"No callback URL returned for Logic App "
                f"'{logic_app_name}' trigger "
                f"'{trigger_name}'"
            )

        return callback_url

    # ========================================================
    # SPLIT REMEDIATION SCAN CALLBACK
    # ========================================================

    def split_remediation_scan_callback(
        self,
        callback_url: str,
    ) -> Dict[str, str]:

        parsed = urlparse(callback_url)

        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                "Invalid remediation scan callback URL"
            )

        base_url = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
            f"{parsed.path}"
        )

        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
        )

        sas_token = ""

        if "sig" in query and query["sig"]:
            sas_token = query["sig"][0]

        if not sas_token:
            raise ValueError(
                "Remediation scan callback URL does not contain "
                "a 'sig' SAS parameter"
            )

        return {
            "remediation_scan_url": base_url,
            "remediation_sas_token": sas_token,
        }

    # ========================================================
    # GET REMEDIATION 01 CALLBACK URLS
    # ========================================================

    def get_remediation_01_callback_urls(
        self,
        subscription_id: str,
        resource_group_name: str,
        remediation_scan_logic_app_name: str,
        remediation_scan_trigger_name: str,
        notification_service_logic_app_name: str,
        notification_service_trigger_name: str,
    ) -> Dict[str, str]:

        logger.info(
            "Resolving Remediation-01 Logic App callback URLs"
        )

        remediation_scan_callback = (
            self.get_logic_app_callback_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                logic_app_name=remediation_scan_logic_app_name,
                trigger_name=remediation_scan_trigger_name,
            )
        )

        remediation_scan_parts = (
            self.split_remediation_scan_callback(
                remediation_scan_callback
            )
        )

        notification_service_url = (
            self.get_logic_app_callback_url(
                subscription_id=subscription_id,
                resource_group_name=resource_group_name,
                logic_app_name=notification_service_logic_app_name,
                trigger_name=notification_service_trigger_name,
            )
        )

        return {
            "remediation_scan_url":
                remediation_scan_parts[
                    "remediation_scan_url"
                ],
            "remediation_sas_token":
                remediation_scan_parts[
                    "remediation_sas_token"
                ],
            "notification_service_url":
                notification_service_url,
        }

    # ========================================================
    # GET REMEDIATION 0.5 FUNCTION URLS
    # ========================================================

    def get_remediation_05_function_urls(
        self,
        subscription_id: str,
        resource_group_name: str,
        business_days_function_app_name: str,
        business_days_function_name: str,
        get_next_business_day_function_app_name: str,
        get_next_business_day_function_name: str,
    ) -> Dict[str, str]:

        logger.info(
            "Resolving Remediation-0.5 Function URLs"
        )

        business_days_service_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=business_days_function_app_name,
            function_name=business_days_function_name,
        )

        get_next_business_day_url = self.get_function_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=get_next_business_day_function_app_name,
            function_name=get_next_business_day_function_name,
        )

        return {
            "business_days_service_url": business_days_service_url,
            "get_next_business_day_url": get_next_business_day_url,
        }

    # ========================================================
    # GET REMEDIATION 0.5 LOGIC APP CALLBACK URL
    # ========================================================

    def get_remediation_05_callback_url(
        self,
        subscription_id: str,
        resource_group_name: str,
        business_day_logic_app_name: str,
        business_day_logic_app_trigger_name: str,
    ) -> str:

        logger.info(
            "Resolving Remediation-0.5 Logic App callback URL: "
            "app=%s trigger=%s",
            business_day_logic_app_name,
            business_day_logic_app_trigger_name,
        )

        return self.get_logic_app_callback_url(
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            logic_app_name=business_day_logic_app_name,
            trigger_name=business_day_logic_app_trigger_name,
        )

    # ========================================================
    # LOAD REMEDIATION ARM TEMPLATE
    # ========================================================

    def _load_remediation_template(self) -> Dict[str, Any]:

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

            return json.load(file)

    # ========================================================
    # FILTER REMEDIATION ARM TEMPLATE
    #
    # IMPORTANT:
    # Each Logic App gets ONLY its own ARM parameters.
    #
    # This prevents parameters belonging to Remediation-01
    # from being required during Remediation-02 deployment.
    # ========================================================

    def _filter_template_for_logic_app(
        self,
        template: Dict[str, Any],
        logic_app_parameter_name: str,
        remove_condition_parameter: bool = False,
    ) -> Dict[str, Any]:

        resources = template.get(
            "resources",
            [],
        )

        selected_resources = []

        for resource in resources:

            resource_name = str(
                resource.get("name", "")
            )

            if resource_name == (
                f"[parameters('{logic_app_parameter_name}')]"
            ):

                selected_resources.append(resource)

        if not selected_resources:

            raise ValueError(
                "Unable to find Logic App resource "
                f"using ARM parameter '{logic_app_parameter_name}' "
                "in remediation.json"
            )

        # ----------------------------------------------------
        # Keep ONLY the selected Logic App resource.
        # ----------------------------------------------------

        template["resources"] = selected_resources

        # ----------------------------------------------------
        # Remediation-01 currently contains:
        #
        # "condition": "[parameters('deployRemediation01')]"
        #
        # Backend already decides whether 01 is deployed,
        # so remove this condition from the in-memory resource.
        # ----------------------------------------------------

        if remove_condition_parameter:

            for resource in template["resources"]:

                resource.pop(
                    "condition",
                    None,
                )

        # ----------------------------------------------------
        # IMPORTANT FIX:
        #
        # Keep ONLY parameters required by the selected
        # Logic App.
        #
        # Remediation-02 must NOT contain:
        # - excelProcessingFunctionUrl
        # - qualysQIDOptionProfileUrl
        # - dfnFileContentFunctionUrl
        # - cmdbIpExtractorFunctionUrl
        # - allIpQidExtractorFunctionUrl
        # - etc.
        #
        # Those belong to Remediation-01.
        # ----------------------------------------------------

        remediation_02_parameters = {
            "LA-Remediation-02",
            "location",
            "storageAccountName",
            "auditLogTableName",
            "configServiceUrl",
            "qualysAssetGroupCreationFunctionUrl",
            "qualysScanFunctionUrl",
            "qualysScanStatusQueueName",
            "remediation03LogicAppUrl",
            "$connections",
        }

        
        remediation_01_parameters = {
    "LA-Remediation-01",
    "location",
    "storageAccountName",
    "auditLogTableName",

    "CallbackUri02",

    "configServiceUrl",
    "sharePointSiteUrl",

    "excelProcessingFunctionUrl",
    "qualysQIDOptionProfileUrl",
    "dfnFileContentFunctionUrl",
    "cmdbIpExtractorFunctionUrl",
    "allIpQidExtractorFunctionUrl",

    "remediationScanUrl",
    "remediationSasToken",
    "notificationServiceUrl",

    "dfnPortalUrl",
    "remediation03LogicAppUrl",

    "cyclesTableName",
    "scanStatusTableName",

    "auditLogPartitionKey",
    "cyclePartitionKey",
    "scanStatusPartitionKey",
    "configPartitionKey",

    "defaultCycleId",
    "defaultVulnerabilityFileName",
    "vulnerabilityFolderPath",
    "workflowName",

    "excelProcessingType",
    "cmdbProcessingType",

    "defaultScannerName",
    "scanTitlePrefix",
    "scannerNamePrefix",
    "defaultScanPriority",
    "defaultOptionProfile",
    "scanStatusInitialValue",

    "notificationType",
    "notificationTitle",
    "emailImportance",
    "notificationChannels",

    "remediationWorkflowName",
    "remediationCallbackSecretKey",

    "qualysScanStatusQueueName",

    "$connections",
}

        remediation_05_parameters = {
            "LA-Remediation-0.5",
            "location",
            "storageAccountName",
            "businessDaysServiceUrl",
            "getNextBusinessDayUrl",
            "queueName",
            "BusinessDayLogicAppUrl",
            "$connections",
        }

        if logic_app_parameter_name == "LA-Remediation-02":

            allowed_parameters = remediation_02_parameters

        elif logic_app_parameter_name == "LA-Remediation-01":

            allowed_parameters = remediation_01_parameters

        elif logic_app_parameter_name == "LA-Remediation-0.5":

            allowed_parameters = remediation_05_parameters

        else:

            raise ValueError(
                f"Unsupported Remediation Logic App parameter: "
                f"{logic_app_parameter_name}"
            )

        template_parameters = template.get(
            "parameters",
            {},
        )

        filtered_parameters = {
            key: value
            for key, value in template_parameters.items()
            if key in allowed_parameters
        }

        template["parameters"] = filtered_parameters

        logger.info(
            "Filtered Remediation ARM template: "
            "logic_app=%s resources=%d parameters=%s",
            logic_app_parameter_name,
            len(template["resources"]),
            sorted(
                template.get(
                    "parameters",
                    {}
                ).keys()
            ),
        )

        return template

    # ========================================================
    # DEPLOY REMEDIATION-02
    # ========================================================

    def deploy(
        self,
        request,
        connections: Dict[str, str],
        function_urls: Dict[str, str],
    ) -> Dict[str, Any]:

        logger.info(
            "Starting Remediation-02 deployment: %s",
            request.logic_app_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        # ----------------------------------------------------
        # Load ARM template
        # ----------------------------------------------------

        template = self._load_remediation_template()

        # ----------------------------------------------------
        # FILTER ARM TEMPLATE
        #
        # Only Remediation-02 is sent to ARM.
        # ----------------------------------------------------

        template = self._filter_template_for_logic_app(
            template=template,
            logic_app_parameter_name="LA-Remediation-02",
        )

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
            "Creating Remediation-02 ARM deployment: %s",
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
                "Remediation-02 deployment completed: "
                "name=%s state=%s",
                deployment_name,
                provisioning_state,
            )

            if provisioning_state != "Succeeded":

                return {
                    "success": False,
                    "deployment_name":
                        deployment_name,
                    "provisioning_state":
                        provisioning_state,
                    "error":
                        "ARM deployment did not succeed",
                }

            return {
                "success": True,
                "deployment_name":
                    deployment_name,
                "provisioning_state":
                    provisioning_state,
            }

        except Exception as exc:

            logger.exception(
                "Remediation-02 ARM deployment failed"
            )

            return {
                "success": False,
                "deployment_name":
                    deployment_name,
                "provisioning_state": "Failed",
                "error": str(exc),
            }

    # ========================================================
    # DEPLOY REMEDIATION-01
    # ========================================================

    def deploy_remediation_01(
        self,
        request,
        connections: Dict[str, str],
        function_urls: Dict[str, str],
        callback_urls: Dict[str, str],
        callback_uri_02: str,
    ) -> Dict[str, Any]:

        logger.info(
            "Starting Remediation-01 deployment: %s",
            request.remediation_01_logic_app_name,
        )

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        # ----------------------------------------------------
        # Load ARM template
        # ----------------------------------------------------

        template = self._load_remediation_template()

        # ----------------------------------------------------
        # FILTER ARM TEMPLATE
        #
        # Only Remediation-01 is sent to ARM.
        # ----------------------------------------------------

        template = self._filter_template_for_logic_app(
            template=template,
            logic_app_parameter_name="LA-Remediation-01",
            remove_condition_parameter=True,
        )

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
        # ARM parameters - Remediation 01
        # ----------------------------------------------------

        parameters = {
            "LA-Remediation-01": {
                "value":
                    request.remediation_01_logic_app_name
            },

            "location": {
                "value": request.location
            },

            "storageAccountName": {
                "value": request.storage_account_name
            },

            "configServiceUrl": {
                "value": function_urls[
                    "config_service_url"
                ]
            },

            "sharePointSiteUrl": {
                "value": request.share_point_site_url
            },

            "auditLogTableName": {
                "value": request.audit_log_table_name
            },

            "excelProcessingFunctionUrl": {
                "value": function_urls[
                    "excel_processing_function_url"
                ]
            },

            "qualysQIDOptionProfileUrl": {
                "value": function_urls[
                    "qualys_qid_option_profile_url"
                ]
            },

            "dfnFileContentFunctionUrl": {
                "value": function_urls[
                    "dfn_file_content_function_url"
                ]
            },

            "cmdbIpExtractorFunctionUrl": {
                "value": function_urls[
                    "cmdb_ip_extractor_function_url"
                ]
            },

            "allIpQidExtractorFunctionUrl": {
                "value": function_urls[
                    "all_ip_qid_extractor_function_url"
                ]
            },

            "remediationScanUrl": {
                "value": callback_urls[
                    "remediation_scan_url"
                ]
            },

            "remediationSasToken": {
                "value": callback_urls[
                    "remediation_sas_token"
                ]
            },

            "notificationServiceUrl": {
                "value": callback_urls[
                    "notification_service_url"
                ]
            },

            "CallbackUri02": {
                "value": callback_uri_02
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
            f"remediation-01-{uuid.uuid4().hex[:8]}"
        )

        logger.info(
            "Creating Remediation-01 ARM deployment: %s",
            deployment_name,
        )

        try:

            poller = (
                resource_client.deployments
                .begin_create_or_update(
                    request.resource_group_name,
                    deployment_name,
                    {
                        "properties":
                            deployment_properties
                    },
                )
            )

            deployment_result = poller.result()

            provisioning_state = (
                deployment_result.properties
                .provisioning_state
            )

            logger.info(
                "Remediation-01 deployment completed: "
                "name=%s state=%s",
                deployment_name,
                provisioning_state,
            )

            if provisioning_state != "Succeeded":

                return {
                    "success": False,
                    "deployment_name":
                        deployment_name,
                    "provisioning_state":
                        provisioning_state,
                    "error": (
                        "Remediation-01 ARM deployment "
                        "did not succeed"
                    ),
                }

            return {
                "success": True,
                "deployment_name":
                    deployment_name,
                "provisioning_state":
                    provisioning_state,
            }

        except Exception as exc:

            logger.exception(
                "Remediation-01 ARM deployment failed"
            )

            return {
                "success": False,
                "deployment_name":
                    deployment_name,
                "provisioning_state": "Failed",
                "error": str(exc),
            }

    # ========================================================
    # DEPLOY REMEDIATION-0.5
    # ========================================================

    def deploy_remediation_05(
        self,
        request,
        connections: Dict[str, str],
        function_urls: Dict[str, str],
        business_day_logic_app_url: str,
    ) -> Dict[str, Any]:

        logger.info(
            "Starting Remediation-0.5 deployment"
        )

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        # ----------------------------------------------------
        # Load ARM template
        # ----------------------------------------------------

        template = self._load_remediation_template()

        # ----------------------------------------------------
        # FILTER ARM TEMPLATE
        #
        # Only Remediation-0.5 is sent to ARM.
        # ----------------------------------------------------

        template = self._filter_template_for_logic_app(
            template=template,
            logic_app_parameter_name="LA-Remediation-0.5",
        )

        # ----------------------------------------------------
        # Managed API IDs
        # ----------------------------------------------------

        subscription_id = request.subscription_id
        location = request.location

        azure_queues_api_id = (
            f"/subscriptions/{subscription_id}"
            f"/providers/Microsoft.Web/locations/{location}"
            f"/managedApis/azurequeues"
        )

        # ----------------------------------------------------
        # ARM parameters - Remediation 0.5
        # ----------------------------------------------------

        parameters = {
            "LA-Remediation-0.5": {
                "value": "LA-Remediation-0.5"
            },

            "location": {
                "value": request.location
            },

            "storageAccountName": {
                "value": request.storage_account_name
            },

            "businessDaysServiceUrl": {
                "value": function_urls[
                    "business_days_service_url"
                ]
            },

            "getNextBusinessDayUrl": {
                "value": function_urls[
                    "get_next_business_day_url"
                ]
            },

            "queueName": {
                "value": "remediationweeklyqueue"
            },

            "BusinessDayLogicAppUrl": {
                "value": business_day_logic_app_url
            },

            "$connections": {
                "value": {
                    "azurequeues-1": {
                        "connectionId": connections[
                            "queue_connection_id"
                        ],
                        "connectionName":
                            request.queue_connection_name,
                        "id":
                            azure_queues_api_id,
                    }
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
            f"remediation-05-{uuid.uuid4().hex[:8]}"
        )

        logger.info(
            "Creating Remediation-0.5 ARM deployment: %s",
            deployment_name,
        )

        try:

            poller = (
                resource_client.deployments
                .begin_create_or_update(
                    request.resource_group_name,
                    deployment_name,
                    {
                        "properties":
                            deployment_properties
                    },
                )
            )

            deployment_result = poller.result()

            provisioning_state = (
                deployment_result.properties
                .provisioning_state
            )

            logger.info(
                "Remediation-0.5 deployment completed: "
                "name=%s state=%s",
                deployment_name,
                provisioning_state,
            )

            if provisioning_state != "Succeeded":

                return {
                    "success": False,
                    "deployment_name":
                        deployment_name,
                    "provisioning_state":
                        provisioning_state,
                    "error":
                        "Remediation-0.5 ARM deployment "
                        "did not succeed",
                }

            return {
                "success": True,
                "deployment_name":
                    deployment_name,
                "provisioning_state":
                    provisioning_state,
            }

        except Exception as exc:

            logger.exception(
                "Remediation-0.5 ARM deployment failed"
            )

            return {
                "success": False,
                "deployment_name":
                    deployment_name,
                "provisioning_state": "Failed",
                "error": str(exc),
            }

