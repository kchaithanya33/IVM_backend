import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.auth import (
    AuthScanDeploymentRequest,
    AuthScanDeploymentResponse,
)
from app.services.auth import AuthScanService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["AuthScan"],
)

service = AuthScanService()


@router.post(
    "/scoping/deploy",
    response_model=AuthScanDeploymentResponse,
    status_code=status.HTTP_200_OK,
)
def deploy_authscan(
    request: AuthScanDeploymentRequest,
):
    """
    Deployment order is strictly:

        1. Deploy AuthScan-02
        2. Wait for ARM deployment to succeed
        3. Get AuthScan-02 HTTP trigger callback URL
        4. Deploy AuthScan-01 using that URL
    """
    try:
        return service.deploy(request)

    except Exception as exc:
        logger.exception("AuthScan deployment failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AuthScan deployment failed: {exc}",
        ) from exc
