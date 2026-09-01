
import json
import logging
from pathlib import Path
from typing import Any

from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.resources.models import (
    Deployment,
    DeploymentProperties,
)

from app.schemas.connection import ConnectionRequest


logger = logging.getLogger(__name__)


class AzureConnectionService:

    # =========================================================
    # FIXED CONNECTION NAMES
    # =========================================================

    AZURE_TABLES_CONNECTION = "azuretables-1"
    AZURE_QUEUES_CONNECTION = "azurequeues-1"
    SHAREPOINT_CONNECTION = "sharepointonline-1"
    OFFICE365_CONNECTION = "office365-1"
    TEAMS_CONNECTION = "teams-1"

    # =========================================================
    # ARM DEPLOYMENT NAME
    # =========================================================

    DEPLOYMENT_NAME = "notification-connections"

    def __init__(self) -> None:
        self.credential = DefaultAzureCredential()

    # =========================================================
    # CREATE ALL CONNECTIONS
    # =========================================================

    def deploy_connections(
        self,
        request: ConnectionRequest,
    ) -> dict[str, Any]:

        # -----------------------------------------------------
        # Locate connections.json
        # -----------------------------------------------------

        template_path = (
            Path(__file__).resolve().parents[2]
            / "arm"
            / "connections.json"
        )

        if not template_path.exists():
            raise FileNotFoundError(
                f"Connections ARM template not found: {template_path}"
            )

        logger.info(
            "Loading connections ARM template: %s",
            template_path,
        )

        # -----------------------------------------------------
        # Load ARM template
        # -----------------------------------------------------

        with template_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            template = json.load(file)

        # -----------------------------------------------------
        # Azure Resource Management client
        # -----------------------------------------------------

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # connections.json only requires:
        #
        # storageAccountName
        # location
        #
        # The five connection names are already fixed inside
        # connections.json.
        # -----------------------------------------------------

        parameters = {
            "storageAccountName": {
                "value": request.storage_account_name,
            },
            "location": {
                "value": request.location,
            },
        }

        # -----------------------------------------------------
        # ARM deployment properties
        # -----------------------------------------------------

        deployment_properties = DeploymentProperties(
            mode="Incremental",
            template=template,
            parameters=parameters,
        )

        deployment = Deployment(
            properties=deployment_properties,
        )

        logger.info(
            "Starting ARM connection deployment '%s'",
            self.DEPLOYMENT_NAME,
        )

        # -----------------------------------------------------
        # Start deployment
        # -----------------------------------------------------

        poller = (
            resource_client.deployments.begin_create_or_update(
                request.resource_group_name,
                self.DEPLOYMENT_NAME,
                deployment,
            )
        )

        # -----------------------------------------------------
        # Wait until deployment completes
        # -----------------------------------------------------

        result = poller.result()

        provisioning_state = None

        if result.properties:
            provisioning_state = (
                result.properties.provisioning_state
            )

        logger.info(
            "Connection ARM deployment completed with state: %s",
            provisioning_state,
        )

        # -----------------------------------------------------
        # Deployment itself must succeed
        # -----------------------------------------------------

        if provisioning_state != "Succeeded":
            raise RuntimeError(
                "Connection ARM deployment failed. "
                f"Provisioning state: {provisioning_state}"
            )

        # -----------------------------------------------------
        # NOW CHECK THE FIVE CONNECTIONS
        # -----------------------------------------------------

        connections = self.check_connections(request)

        # -----------------------------------------------------
        # Find connections that are not authenticated
        # -----------------------------------------------------

        unauthorized_connections = [
            connection["name"]
            for connection in connections
            if not connection["authenticated"]
        ]

        # -----------------------------------------------------
        # Return complete result
        # -----------------------------------------------------

        return {
            "deployment_name": self.DEPLOYMENT_NAME,
            "provisioning_state": provisioning_state,
            "connections": connections,
            "unauthorized_connections": unauthorized_connections,
        }

    # =========================================================
    # CHECK ALL FIVE CONNECTIONS
    # =========================================================

    def check_connections(
        self,
        request: ConnectionRequest,
    ) -> list[dict[str, Any]]:

        connection_names = [
            self.AZURE_TABLES_CONNECTION,
            self.AZURE_QUEUES_CONNECTION,
            self.SHAREPOINT_CONNECTION,
            self.OFFICE365_CONNECTION,
            self.TEAMS_CONNECTION,
        ]

        results: list[dict[str, Any]] = []

        for connection_name in connection_names:

            logger.info(
                "Checking Azure connection: %s",
                connection_name,
            )

            result = self._check_single_connection(
                request=request,
                connection_name=connection_name,
            )

            results.append(result)

        return results

    # =========================================================
    # CHECK ONE CONNECTION
    # =========================================================

    def _check_single_connection(
        self,
        request: ConnectionRequest,
        connection_name: str,
    ) -> dict[str, Any]:

        resource_client = ResourceManagementClient(
            self.credential,
            request.subscription_id,
        )

        # -----------------------------------------------------
        # Microsoft.Web/connections resource ID
        # -----------------------------------------------------

        connection_resource_id = (
            f"/subscriptions/"
            f"{request.subscription_id}"
            f"/resourceGroups/"
            f"{request.resource_group_name}"
            f"/providers/Microsoft.Web/connections/"
            f"{connection_name}"
        )

        try:

            # -------------------------------------------------
            # Get connection resource
            # -------------------------------------------------

            connection = (
                resource_client.resources.get_by_id(
                    connection_resource_id,
                    "2016-06-01",
                )
            )

            properties = connection.properties or {}

            logger.info(
                "Connection resource found: %s",
                connection_name,
            )

            # -------------------------------------------------
            # Azure connector status
            #
            # Microsoft.Web/connections commonly exposes
            # connector status information through `statuses`.
            # -------------------------------------------------

            statuses = properties.get(
                "statuses",
                [],
            )

            # -------------------------------------------------
            # Determine authentication state
            # -------------------------------------------------

            authenticated = self._is_authenticated(
                statuses
            )

            # -------------------------------------------------
            # Convert Azure status information into a clean
            # response object.
            # -------------------------------------------------

            status_details: list[dict[str, Any]] = []

            for status in statuses:

                if isinstance(status, dict):

                    status_details.append(
                        {
                            "status": status.get("status"),
                            "target": status.get("target"),
                            "error": status.get("error"),
                        }
                    )

            # -------------------------------------------------
            # Determine readable status
            # -------------------------------------------------

            if authenticated:
                readable_status = "Connected"
            else:
                readable_status = "Not Authorized"

            logger.info(
                "Connection '%s': %s",
                connection_name,
                readable_status,
            )

            return {
                "name": connection_name,
                "created": True,
                "authenticated": authenticated,
                "status": readable_status,
                "statuses": status_details,
                "error": None,
            }

        except HttpResponseError as exc:

            logger.error(
                "Azure error while checking connection '%s': %s",
                connection_name,
                exc,
            )

            return {
                "name": connection_name,
                "created": False,
                "authenticated": False,
                "status": "Not Authorized",
                "statuses": [],
                "error": str(exc),
            }

        except Exception as exc:

            logger.exception(
                "Unexpected error while checking connection '%s'",
                connection_name,
            )

            return {
                "name": connection_name,
                "created": False,
                "authenticated": False,
                "status": "Not Authorized",
                "statuses": [],
                "error": str(exc),
            }

    # =========================================================
    # AUTHENTICATION CHECK
    # =========================================================

    @staticmethod
    def _is_authenticated(
        statuses: list[Any],
    ) -> bool:

        # -----------------------------------------------------
        # No status means we cannot confirm authentication.
        #
        # Therefore treat it as NOT AUTHENTICATED.
        # -----------------------------------------------------

        if not statuses:
            return False

        # -----------------------------------------------------
        # Check all returned statuses.
        # -----------------------------------------------------

        for status in statuses:

            if not isinstance(status, dict):
                return False

            status_value = status.get("status")

            if not status_value:
                return False

            normalized_status = (
                str(status_value)
                .strip()
                .lower()
            )

            # -------------------------------------------------
            # Successful Azure connection states
            # -------------------------------------------------

            if normalized_status not in {
                "connected",
                "authenticated",
                "succeeded",
                "success",
            }:
                return False

        return True
