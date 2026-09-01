from fastapi import APIRouter, HTTPException

from app.schemas.workflow import DeploymentRequest
from app.services.workflow_service import WorkflowService


router = APIRouter(
    prefix="/api/workflow",
    tags=["Workflow"]
)


service = WorkflowService()


@router.post("/deploy")
def deploy(
    request: DeploymentRequest
):

    try:

        result = service.deploy(request)

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )