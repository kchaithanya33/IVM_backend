import logging
from typing import Any, Dict

from app.azure.auth import AuthScanAzureService
from app.schemas.auth import (
    AuthScanDeploymentRequest,
    AuthScanDeploymentResponse,
)

logger = logging.getLogger(__name__)


class AuthScanService:
    """
    Application/service layer for AuthScan deployment.
    Azure-specific work is delegated to AuthScanAzureService.
    """

    def __init__(
        self,
        azure_service: AuthScanAzureService | None = None,
    ) -> None:
        self.azure_service = azure_service or AuthScanAzureService()

    def deploy(
        self,
        request: AuthScanDeploymentRequest,
    ) -> AuthScanDeploymentResponse:
        logger.info(
            "AuthScan deployment requested: rg=%s auth01=%s auth02=%s",
            request.resource_group_name,
            request.auth_scan01_logic_app_name,
            request.auth_scan02_logic_app_name,
        )

        result: Dict[str, Any] = self.azure_service.deploy(request)
        return AuthScanDeploymentResponse(**result)