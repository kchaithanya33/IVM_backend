

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.identity import DefaultAzureCredential

from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.logic import LogicManagementClient


logger = logging.getLogger(__name__)


class ARMDeploymentManager:
    """
    Handles Azure Resource Manager operations.

    Responsibilities:

        - Resource Group operations
        - ARM template loading/deployment
        - Resource listing
        - Function App URL resolution
        - Logic App trigger callback URL resolution
    """

    def __init__(
        self,
        subscription_id: str,
    ):

        self.subscription_id = subscription_id

        logger.info(
            "Initializing ARM clients for subscription: %s",
            subscription_id,
        )

        self.credential = DefaultAzureCredential()

        # =====================================================
        # Resource Manager
        # =====================================================

        self.client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        # =====================================================
        # Web / Function Apps
        # =====================================================

        self.web_client = WebSiteManagementClient(
            self.credential,
            subscription_id,
        )

        # =====================================================
        # Logic Apps
        # =====================================================

        self.logic_client = LogicManagementClient(
            self.credential,
            subscription_id,
        )

    # =========================================================
    # RESOURCE GROUP
    # =========================================================

    def resource_group_exists(
        self,
        resource_group_name: str,
    ) -> bool:

        logger.info(
            "Checking Resource Group: %s",
            resource_group_name,
        )

        return self.client.resource_groups.check_existence(
            resource_group_name
        )

    def ensure_resource_group(
        self,
        resource_group_name: str,
        location: str,
    ):

        exists = self.resource_group_exists(
            resource_group_name
        )

        if exists:

            logger.info(
                "Resource Group already exists: %s",
                resource_group_name,
            )

            return self.client.resource_groups.get(
                resource_group_name
            )

        logger.info(
            "Creating Resource Group: %s",
            resource_group_name,
        )

        return self.client.resource_groups.create_or_update(
            resource_group_name,
            {
                "location": location
            },
        )

    # =========================================================
    # ARM TEMPLATE
    # =========================================================

    @staticmethod
    def load_arm_template(
        template_path: str,
    ) -> Dict[str, Any]:

        path = Path(template_path)

        if not path.exists():

            raise FileNotFoundError(
                f"ARM template not found: {path}"
            )

        logger.info(
            "Loading ARM template: %s",
            path,
        )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    # =========================================================
    # ARM DEPLOYMENT
    # =========================================================

    def deploy_arm_template(
        self,
        resource_group_name: str,
        template_path: str,
        parameters: Dict[str, Any],
        deployment_name: Optional[str] = None,
    ) -> Dict[str, Any]:

        template = self.load_arm_template(
            template_path
        )

        # -----------------------------------------------------
        # Deployment name
        # -----------------------------------------------------

        if not deployment_name:

            timestamp = datetime.utcnow().strftime(
                "%Y%m%d%H%M%S"
            )

            deployment_name = (
                f"notification-deployment-{timestamp}"
            )

        logger.info(
            "Starting ARM deployment: %s",
            deployment_name,
        )

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # ARM SDK requires:
        #
        # {
        #     "parameterName": {
        #         "value": value
        #     }
        # }
        # -----------------------------------------------------

        arm_parameters = {
            key: {
                "value": value
            }
            for key, value in parameters.items()
        }

        deployment_payload = {
            "properties": {
                "mode": "Incremental",
                "template": template,
                "parameters": arm_parameters,
            }
        }

        logger.info(
            "Submitting ARM deployment to Resource Group: %s",
            resource_group_name,
        )

        poller = (
            self.client.deployments
            .begin_create_or_update(
                resource_group_name,
                deployment_name,
                deployment_payload,
            )
        )

        deployment = poller.result()

        provisioning_state = (
            deployment.properties.provisioning_state
        )

        logger.info(
            "ARM deployment state: %s",
            provisioning_state,
        )

        if provisioning_state != "Succeeded":

            deployment_error = None

            if deployment.properties.error:

                deployment_error = (
                    deployment.properties.error
                )

            logger.error(
                "ARM deployment failed: %s",
                deployment_error,
            )

            raise RuntimeError(
                "ARM deployment failed. "
                f"State: {provisioning_state}. "
                f"Error: {deployment_error}"
            )

        return {
            "deployment_name": deployment_name,
            "provisioning_state": provisioning_state,
        }

    # =========================================================
    # GET DEPLOYMENT
    # =========================================================

    def get_deployment_status(
        self,
        resource_group_name: str,
        deployment_name: str,
    ) -> Dict[str, Any]:

        deployment = (
            self.client.deployments.get(
                resource_group_name,
                deployment_name,
            )
        )

        properties = deployment.properties

        return {
            "deployment_name":
                deployment_name,

            "provisioning_state":
                properties.provisioning_state,
        }

    # =========================================================
    # FUNCTION URL
    # =========================================================

    def get_function_url(
        self,
        resource_group_name: str,
        function_app_name: str,
        function_name: str,
    ) -> str:
        """
        Resolve the HTTP invocation URL for an Azure Function.

        Resolution order:

            1. Get the function resource.
            2. Use its invoke_url_template when available.
            3. Try function-specific key.
            4. Fall back to host key.
            5. If no key exists, return the invocation URL without
               a key.

        This prevents the old failure:

            No function keys returned for
            'function-app/FunctionName'
        """

        if not function_app_name:
            raise ValueError(
                "function_app_name is required"
            )

        if not function_name:
            raise ValueError(
                "function_name is required"
            )

        logger.info(
            "Getting Function information. "
            "App: %s, Function: %s",
            function_app_name,
            function_name,
        )

        # =====================================================
        # 1. Get function resource
        # =====================================================

        function = (
            self.web_client.web_apps.get_function(
                resource_group_name,
                function_app_name,
                function_name,
            )
        )

        properties = (
            getattr(function, "properties", None)
        )

        invoke_url = None

        if properties:

            invoke_url = getattr(
                properties,
                "invoke_url_template",
                None,
            )

        # =====================================================
        # 2. Fallback URL construction
        # =====================================================

        if not invoke_url:

            site = (
                self.web_client.web_apps.get(
                    resource_group_name,
                    function_app_name,
                )
            )

            hostname = (
                getattr(site, "default_host_name", None)
            )

            if not hostname:

                raise RuntimeError(
                    "Unable to determine default hostname "
                    f"for Function App '{function_app_name}'"
                )

            invoke_url = (
                f"https://{hostname}/api/{function_name}"
            )

        logger.info(
            "Function invocation URL found"
        )

        # =====================================================
        # 3. Try function-specific key
        # =====================================================

        function_key = None

        try:

            keys = (
                self.web_client.web_apps
                .list_function_keys(
                    resource_group_name,
                    function_app_name,
                    function_name,
                )
            )

            key_values = (
                getattr(
                    keys,
                    "additional_properties",
                    None,
                )
                or {}
            )

            if not key_values:

                key_values = {
                    key: getattr(
                        keys,
                        key,
                        None,
                    )
                    for key in (
                        "default",
                        "key",
                    )
                    if getattr(
                        keys,
                        key,
                        None
                    )
                }

            function_key = (
                key_values.get("default")
                or key_values.get("key")
            )

        except Exception as exc:

            logger.warning(
                "Unable to retrieve function-specific "
                "key for %s/%s: %s",
                function_app_name,
                function_name,
                exc,
            )

        # =====================================================
        # 4. Fall back to host key
        # =====================================================

        if not function_key:

            try:

                host_keys = (
                    self.web_client.web_apps
                    .list_host_keys(
                        resource_group_name,
                        function_app_name,
                    )
                )

                host_key_values = (
                    getattr(
                        host_keys,
                        "additional_properties",
                        None,
                    )
                    or {}
                )

                if not host_key_values:

                    host_key_values = {
                        key: getattr(
                            host_keys,
                            key,
                            None,
                        )
                        for key in (
                            "masterKey",
                            "functionKey",
                        )
                        if getattr(
                            host_keys,
                            key,
                            None
                        )
                    }

                function_key = (
                    host_key_values.get(
                        "functionKey"
                    )
                    or host_key_values.get(
                        "masterKey"
                    )
                )

            except Exception as exc:

                logger.warning(
                    "Unable to retrieve host keys "
                    "for Function App '%s': %s",
                    function_app_name,
                    exc,
                )

        # =====================================================
        # 5. Add function key if available
        # =====================================================

        if function_key:

            separator = (
                "&" if "?" in invoke_url else "?"
            )

            final_url = (
                f"{invoke_url}"
                f"{separator}"
                f"code={function_key}"
            )

            logger.info(
                "Function URL resolved with authorization key"
            )

            return final_url

        # =====================================================
        # 6. No key available
        #
        # This can be valid when the function is configured for
        # anonymous authorization.
        # =====================================================

        logger.warning(
            "No function/host key was available for "
            "%s/%s. Returning invocation URL without code.",
            function_app_name,
            function_name,
        )

        return invoke_url

    # =========================================================
    # LOGIC APP TRIGGER CALLBACK URL
    # =========================================================

    def get_logic_app_trigger_callback_url(
        self,
        resource_group_name: str,
        logic_app_name: str,
        trigger_name: str,
    ) -> str:
        """
        Get the HTTP callback URL for a Logic App trigger.

        Example:

            Logic App:
                Notification-service

            Trigger:
                When_a_HTTP_request_is_received

        The URL is returned by Azure and normally contains the
        required SAS query parameters.
        """

        if not logic_app_name:

            raise ValueError(
                "logic_app_name is required"
            )

        if not trigger_name:

            raise ValueError(
                "trigger_name is required"
            )

        logger.info(
            "Getting Logic App trigger callback URL. "
            "Logic App: %s, Trigger: %s",
            logic_app_name,
            trigger_name,
        )

        callback = (
            self.logic_client.workflow_triggers
            .list_callback_url(
                resource_group_name,
                logic_app_name,
                trigger_name,
            )
        )

        callback_url = (
            getattr(
                callback,
                "value",
                None,
            )
        )

        if not callback_url:

            raise RuntimeError(
                "Azure returned no callback URL for "
                f"Logic App '{logic_app_name}' "
                f"trigger '{trigger_name}'"
            )

        logger.info(
            "Logic App trigger callback URL resolved successfully"
        )

        return callback_url

    # =========================================================
    # LIST RESOURCES
    # =========================================================

    def list_resource_group_resources(
        self,
        resource_group_name: str,
    ) -> List[Dict[str, Any]]:

        logger.info(
            "Listing resources in Resource Group: %s",
            resource_group_name,
        )

        resources = (
            self.client.resources
            .list_by_resource_group(
                resource_group_name
            )
        )

        result = []

        for resource in resources:

            result.append(
                {
                    "name":
                        resource.name,

                    "type":
                        resource.type,

                    "location":
                        resource.location,

                    "id":
                        resource.id,
                }
            )

        return result

    # =========================================================
    # GET RESOURCE
    # =========================================================

    def get_resource_by_id(
        self,
        resource_id: str,
        api_version: str,
    ):

        logger.info(
            "Getting Azure resource: %s",
            resource_id,
        )

        return self.client.resources.get_by_id(
            resource_id,
            api_version,
        )
