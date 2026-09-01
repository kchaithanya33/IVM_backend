
import json
import logging
from pathlib import Path
from typing import Any, Dict

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient

from app.schemas.scoping import (
    ScopingDeploymentRequest,
    ScopingDeploymentResponse,
)


logger = logging.getLogger(__name__)


class ScopingDeploymentService:
    """
    Handles deployment of the Scoping Logic Apps using
    the existing scoping.json ARM template.

    Resource Group creation is NOT handled here.
    The Resource Group must already exist.
    """

    def __init__(self):
        self.credential = DefaultAzureCredential()

    # ============================================================
    # ARM TEMPLATE
    # ============================================================

    def _get_arm_template_path(self) -> Path:
        """
        Resolve the scoping.json path.

        Project structure:

        notification-backend/
        ├── app/
        │   └── services/
        │       └── scoping_deployment_service.py
        │
        └── arm/
            └── scoping.json
        """

        project_root = Path(__file__).resolve().parents[2]

        template_path = (
            project_root
            / "arm"
            / "scoping.json"
        )

        return template_path

    def _load_arm_template(self) -> Dict[str, Any]:
        """
        Load and validate scoping.json.
        """

        template_path = self._get_arm_template_path()

        logger.info(
            "Checking ARM template: %s",
            template_path,
        )

        if not template_path.exists():
            raise FileNotFoundError(
                f"ARM template '{template_path}' was not found."
            )

        try:
            with open(
                template_path,
                "r",
                encoding="utf-8",
            ) as file:

                template = json.load(file)

        except json.JSONDecodeError as exc:

            raise ValueError(
                f"Invalid ARM template JSON: {exc}"
            ) from exc

        logger.info(
            "ARM template found."
        )

        return template

    # ============================================================
    # RESOURCE MANAGEMENT CLIENT
    # ============================================================

    def _get_resource_client(
        self,
        subscription_id: str,
    ) -> ResourceManagementClient:

        return ResourceManagementClient(
            credential=self.credential,
            subscription_id=subscription_id,
        )

    # ============================================================
    # STORAGE ACCOUNT
    # ============================================================

    def _check_storage_account(
        self,
        request: ScopingDeploymentRequest,
    ) -> None:

        logger.info(
            "Checking Storage Account: %s",
            request.storage_account_name,
        )

        storage_client = StorageManagementClient(
            credential=self.credential,
            subscription_id=request.subscription_id,
        )

        try:

            storage_client.storage_accounts.get_properties(
                request.resource_group_name,
                request.storage_account_name,
            )

        except Exception as exc:

            raise RuntimeError(
                f"Storage Account "
                f"'{request.storage_account_name}' "
                f"was not found in Resource Group "
                f"'{request.resource_group_name}'."
            ) from exc

        logger.info(
            "Storage Account found."
        )

    # ============================================================
    # API CONNECTION
    # ============================================================

    def _get_api_connection_id(
        self,
        request: ScopingDeploymentRequest,
        connection_name: str,
    ) -> str:

        logger.info(
            "Checking API Connection: %s",
            connection_name,
        )

        resource_client = self._get_resource_client(
            request.subscription_id
        )

        resource_id = (
            f"/subscriptions/"
            f"{request.subscription_id}"
            f"/resourceGroups/"
            f"{request.resource_group_name}"
            f"/providers/Microsoft.Web/connections/"
            f"{connection_name}"
        )

        try:

            resource = (
                resource_client.resources.get_by_id(
                    resource_id,
                    "2016-06-01",
                )
            )

        except Exception as exc:

            raise RuntimeError(
                f"API Connection "
                f"'{connection_name}' was not found "
                f"in Resource Group "
                f"'{request.resource_group_name}'."
            ) from exc

        if resource is None:

            raise RuntimeError(
                f"API Connection "
                f"'{connection_name}' was not found."
            )

        logger.info(
            "API Connection found: %s",
            resource.id,
        )

        return resource.id

    # ============================================================
    # BUILD $connections
    # ============================================================

    def _build_connections(
        self,
        request: ScopingDeploymentRequest,
        table_connection_id: str,
        queue_connection_id: str,
        sharepoint_connection_id: str,
    ) -> Dict[str, Any]:

        connections = {
            "azuretables-1": {
                "connectionId": table_connection_id,
                "connectionName": (
                    request.table_connection_name
                ),
                "id": (
                    f"/subscriptions/"
                    f"{request.subscription_id}"
                    f"/providers/Microsoft.Web/"
                    f"locations/{request.location}"
                    f"/managedApis/azuretables"
                ),
            },

            "azurequeues-1": {
                "connectionId": queue_connection_id,
                "connectionName": (
                    request.queue_connection_name
                ),
                "id": (
                    f"/subscriptions/"
                    f"{request.subscription_id}"
                    f"/providers/Microsoft.Web/"
                    f"locations/{request.location}"
                    f"/managedApis/azurequeues"
                ),
            },

            "sharepointonline-1": {
                "connectionId": sharepoint_connection_id,
                "connectionName": (
                    request.sharepoint_connection_name
                ),
                "id": (
                    f"/subscriptions/"
                    f"{request.subscription_id}"
                    f"/providers/Microsoft.Web/"
                    f"locations/{request.location}"
                    f"/managedApis/sharepointonline"
                ),
            },
        }

        return connections

    # ============================================================
    # DEPLOY ARM TEMPLATE
    # ============================================================

    def _deploy_template(
        self,
        request: ScopingDeploymentRequest,
        template: Dict[str, Any],
        connections: Dict[str, Any],
    ):
        """
        Deploy the Scoping ARM template to the existing
        Resource Group.

        Resource Group creation is NOT performed here.
        """

        resource_client = self._get_resource_client(
            request.subscription_id
        )

        deployment_name = (
            f"scoping-deployment-"
            f"{request.logic_app_name}"
        )

        # ========================================================
        # ARM PARAMETERS
        # ========================================================

        parameters = {
            "logicAppName": {
                "value": request.logic_app_name
            },

            "scoping01LogicAppName": {
                "value": request.scoping01_logic_app_name
            },

            "scoping02LogicAppName": {
                "value": request.scoping02_logic_app_name
            },

            "location": {
                "value": request.location
            },

            "storageAccountName": {
                "value": request.storage_account_name
            },

            "scopingScheduleQueueName": {
                "value": request.queue_name
            },

            "notificationLogTableName": {
                "value": request.notification_log_table_name
            },

            "NotificationStatus": {
                "value": request.notification_status_table_name
            },

            "callbackSecretKey": {
                "value": request.callback_secret_key
            },

            "completionLogicAppUrl": {
                "value": request.completion_logic_app_url
            },

            "sharePointUrl": {
                "value": request.sharepoint_url
            },

            "authscanQueueName": {
                "value": request.authscan_queue_name
            },

            "$connections": {
                "value": connections
            },
        }

        # ========================================================
        # ARM DEPLOYMENT REQUEST
        # ========================================================
        #
        # Azure Resource Manager expects the deployment body:
        #
        # {
        #     "properties": {
        #         "mode": "Incremental",
        #         "template": {...},
        #         "parameters": {...}
        #     }
        # }
        #
        # ========================================================

        deployment_properties = {
            "properties": {
                "mode": "Incremental",
                "template": template,
                "parameters": parameters,
            }
        }

        logger.info(
            "Starting ARM deployment: %s",
            deployment_name,
        )

        logger.info(
            "Resource Group: %s",
            request.resource_group_name,
        )

        # ========================================================
        # START DEPLOYMENT
        # ========================================================

        deployment = (
            resource_client.deployments
            .begin_create_or_update(
                request.resource_group_name,
                deployment_name,
                deployment_properties,
            )
        )

        # ========================================================
        # WAIT FOR DEPLOYMENT
        # ========================================================

        result = deployment.result()

        logger.info(
            "ARM deployment completed: %s",
            deployment_name,
        )

        return deployment_name, result

    # ============================================================
    # MAIN DEPLOYMENT
    # ============================================================

    def deploy(
        self,
        request: ScopingDeploymentRequest,
    ) -> ScopingDeploymentResponse:

        logger.info(
            "=========================================="
        )

        logger.info(
            "Scoping Logic App Deployment"
        )

        logger.info(
            "=========================================="
        )

        logger.info(
            "Resource Group       : %s",
            request.resource_group_name,
        )

        logger.info(
            "Location             : %s",
            request.location,
        )

        logger.info(
            "Logic App            : %s",
            request.logic_app_name,
        )

        logger.info(
            "Storage Account      : %s",
            request.storage_account_name,
        )

        logger.info(
            "Table Connection     : %s",
            request.table_connection_name,
        )

        logger.info(
            "Queue Name           : %s",
            request.queue_name,
        )

        logger.info(
            "Queue Connection     : %s",
            request.queue_connection_name,
        )

        logger.info(
            "SharePoint Connection: %s",
            request.sharepoint_connection_name,
        )

        logger.info(
            "Scoping-01 Logic App : %s",
            request.scoping01_logic_app_name,
        )

        logger.info(
            "Scoping-02 Logic App : %s",
            request.scoping02_logic_app_name,
        )

        try:

            # ----------------------------------------------------
            # 1. CHECK ARM TEMPLATE
            # ----------------------------------------------------

            template = self._load_arm_template()

            # ----------------------------------------------------
            # 2. CHECK STORAGE ACCOUNT
            # ----------------------------------------------------

            self._check_storage_account(
                request
            )

            # ----------------------------------------------------
            # 3. GET TABLE CONNECTION
            # ----------------------------------------------------

            table_connection_id = (
                self._get_api_connection_id(
                    request,
                    request.table_connection_name,
                )
            )

            # ----------------------------------------------------
            # 4. GET SHAREPOINT CONNECTION
            # ----------------------------------------------------

            sharepoint_connection_id = (
                self._get_api_connection_id(
                    request,
                    request.sharepoint_connection_name,
                )
            )

            # ----------------------------------------------------
            # 5. GET QUEUE CONNECTION
            # ----------------------------------------------------

            queue_connection_id = (
                self._get_api_connection_id(
                    request,
                    request.queue_connection_name,
                )
            )

            # ----------------------------------------------------
            # 6. BUILD $connections
            # ----------------------------------------------------

            connections = self._build_connections(
                request=request,
                table_connection_id=table_connection_id,
                queue_connection_id=queue_connection_id,
                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),
            )

            # ----------------------------------------------------
            # 7. DEPLOY SCOPING ARM TEMPLATE
            # ----------------------------------------------------

            (
                deployment_name,
                result,
            ) = self._deploy_template(
                request=request,
                template=template,
                connections=connections,
            )

            # ----------------------------------------------------
            # 8. GET DEPLOYMENT STATE
            # ----------------------------------------------------

            provisioning_state = None

            if result is not None:

                properties = getattr(
                    result,
                    "properties",
                    None,
                )

                if properties:

                    provisioning_state = getattr(
                        properties,
                        "provisioning_state",
                        None,
                    )

            # ----------------------------------------------------
            # 9. SUCCESS RESPONSE
            # ----------------------------------------------------

            return ScopingDeploymentResponse(
                success=True,

                message=(
                    "Scoping Logic App deployment "
                    "completed successfully."
                ),

                subscription_id=(
                    request.subscription_id
                ),

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                logic_app_name=(
                    request.logic_app_name
                ),

                scoping01_logic_app_name=(
                    request.scoping01_logic_app_name
                ),

                scoping02_logic_app_name=(
                    request.scoping02_logic_app_name
                ),

                storage_account_name=(
                    request.storage_account_name
                ),

                table_connection_id=(
                    table_connection_id
                ),

                queue_connection_id=(
                    queue_connection_id
                ),

                sharepoint_connection_id=(
                    sharepoint_connection_id
                ),

                deployment_name=(
                    deployment_name
                ),

                provisioning_state=(
                    provisioning_state
                ),
            )

        except Exception as exc:

            logger.exception(
                "Scoping deployment failed."
            )

            # ----------------------------------------------------
            # FAILURE RESPONSE
            # ----------------------------------------------------

            return ScopingDeploymentResponse(
                success=False,

                message=(
                    f"Scoping deployment failed: "
                    f"{str(exc)}"
                ),

                subscription_id=(
                    request.subscription_id
                ),

                resource_group_name=(
                    request.resource_group_name
                ),

                location=request.location,

                logic_app_name=(
                    request.logic_app_name
                ),

                scoping01_logic_app_name=(
                    request.scoping01_logic_app_name
                ),

                scoping02_logic_app_name=(
                    request.scoping02_logic_app_name
                ),

                storage_account_name=(
                    request.storage_account_name
                ),
            )
