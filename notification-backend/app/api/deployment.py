from fastapi import APIRouter, HTTPException

from app.schemas.deployment import (
    FunctionAppDeploymentRequest,
    FunctionAppDeploymentResponse,
)

from app.services.function_app_deployment_service import (
    FunctionAppDeploymentService,
)


router = APIRouter(
    prefix="/api/deployment",
    tags=["Deployment"],
)


@router.post(
    "/function-app",
    response_model=FunctionAppDeploymentResponse,
)
def deploy_function_app(
    request: FunctionAppDeploymentRequest,
):

    try:

        service = (
            FunctionAppDeploymentService()
        )

        return service.deploy(request)

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )