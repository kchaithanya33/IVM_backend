
import logging

from app.azure.connection import AzureConnectionService
from app.schemas.connection import (
    ConnectionRequest,
    ConnectionResponse,
)


logger = logging.getLogger(__name__)


class ConnectionService:

    def __init__(self) -> None:
        self.azure_connection_service = (
            AzureConnectionService()
        )

    # =========================================================
    # CREATE CONNECTIONS
    # =========================================================

    def create_connections(
        self,
        request: ConnectionRequest,
    ) -> ConnectionResponse:

        logger.info(
            "Creating Azure connections for resource group '%s'",
            request.resource_group_name,
        )

        result = (
            self.azure_connection_service.deploy_connections(
                request
            )
        )

        # -----------------------------------------------------
        # Build response
        # -----------------------------------------------------

        return ConnectionResponse(
            status="success",
            message=(
                "Azure connection deployment completed. "
                "Connection authentication status checked."
            ),
            deployment_name=result["deployment_name"],
            resource_group_name=request.resource_group_name,
            provisioning_state=result["provisioning_state"],
            connections=result["connections"],
            unauthorized_connections=result[
                "unauthorized_connections"
            ],
        )
