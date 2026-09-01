import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient


logger = logging.getLogger(__name__)


class ARMDeploymentManager:
    """
    Handles Azure Resource Manager operations.

    This class replaces the Azure CLI commands used by
    the notification deployment shell script.
    """

    def __init__(
        self,
        subscription_id: str,
    ):
        self.subscription_id = subscription_id

        logger.info(
            "Initializing ARM client for subscription: %s",
            subscription_id,
        )

        self.credential = DefaultAzureCredential()

        self.client = ResourceManagementClient(
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
        # Convert parameters
        #
        # ARM SDK expects:
        #
        # {
        #     "parameterName": {
        #         "value": "something"
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

        # -----------------------------------------------------
        # Wait for ARM deployment
        # -----------------------------------------------------

        deployment = poller.result()

        provisioning_state = (
            deployment.properties.provisioning_state
        )

        logger.info(
            "ARM deployment state: %s",
            provisioning_state,
        )

        # -----------------------------------------------------
        # Failure
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # Success
        # -----------------------------------------------------

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
            "deployment_name": deployment_name,
            "provisioning_state":
                properties.provisioning_state,
        }

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
                    "name": resource.name,
                    "type": resource.type,
                    "location": resource.location,
                    "id": resource.id,
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