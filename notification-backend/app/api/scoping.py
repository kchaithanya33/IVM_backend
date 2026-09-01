import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.scoping import (
    ScopingDeploymentRequest,
    ScopingDeploymentResponse,
)
from app.services.scoping_deployment_service import (
    ScopingDeploymentService,
)

logger = logging.getLogger(__name__)

router = APIRouter()

scoping_service = ScopingDeploymentService()


@router.post(
    "/deploy",
    response_model=ScopingDeploymentResponse,
    status_code=status.HTTP_200_OK,
)
def deploy_scoping(
    request: ScopingDeploymentRequest,
):
    """
    Deploy the Scoping Logic Apps using scoping.json.

    Equivalent to the original Bash deployment script.
    """

    logger.info(
        "Received Scoping deployment request for Logic App: %s",
        request.logic_app_name,
    )

    try:
        result = scoping_service.deploy(request)

        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message,
            )

        return result

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Unexpected error during Scoping deployment."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scoping deployment failed: {str(exc)}",
        ) from exc