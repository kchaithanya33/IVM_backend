

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.scoping import (
    ScopingDeploymentRequest,
    ScopingDeploymentResponse,
)

from app.services.scoping import (
    ScopingDeploymentService,
)


logger = logging.getLogger(__name__)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/scoping",
    tags=["Scoping"],
)


# ============================================================
# SERVICE
# ============================================================

scoping_service = ScopingDeploymentService()


# ============================================================
# DEPLOY SCOPING
# ============================================================

@router.post(
    "/deploy",
    response_model=ScopingDeploymentResponse,
)
def deploy_scoping(
    request: ScopingDeploymentRequest,
) -> ScopingDeploymentResponse:
    """
    Deploy Scoping-00 and Scoping-01 Logic Apps.

    Flow:

        Frontend
            |
            v
        POST /api/scoping/deploy
            |
            v
        ScopingDeploymentRequest
            |
            v
        ScopingDeploymentService
            |
            +--> Resolve Azure Tables connection
            |
            +--> Resolve Azure Queues connection
            |
            +--> Resolve SharePoint connection
            |
            +--> Resolve Azure Function URLs
            |
            +--> Deploy scoping.json
            |
            v
        ScopingDeploymentResponse
            |
            v
        Frontend
    """

    logger.info(
        "Received Scoping deployment request: "
        "subscription=%s resource_group=%s "
        "logic_app=%s scoping01_logic_app=%s",
        request.subscription_id,
        request.resource_group_name,
        request.logic_app_name,
        request.scoping01_logic_app_name,
    )

    try:

        # ====================================================
        # DEPLOYMENT
        # ====================================================

        result = scoping_service.deploy_scoping(
            request=request,
        )

        # ====================================================
        # LOG RESULT
        # ====================================================

        if result.success:

            logger.info(
                "Scoping deployment completed successfully: "
                "deployment=%s state=%s",
                result.deployment_name,
                result.provisioning_state,
            )

        else:

            logger.error(
                "Scoping deployment failed: "
                "deployment=%s state=%s message=%s",
                result.deployment_name,
                result.provisioning_state,
                result.message,
            )

        return result

    # ========================================================
    # EXPECTED VALIDATION ERRORS
    # ========================================================

    except ValueError as exc:

        logger.error(
            "Scoping deployment validation error: %s",
            exc,
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    # ========================================================
    # UNEXPECTED ERRORS
    # ========================================================

    except Exception as exc:

        logger.exception(
            "Unexpected error during Scoping deployment."
        )

        raise HTTPException(
            status_code=500,
            detail="Scoping deployment failed.",
        ) from exc


# ============================================================
# HEALTH CHECK
# ============================================================

@router.get(
    "/health",
)
def scoping_health() -> dict:
    """
    Health check for the Scoping deployment API.
    """

    return {
        "status": "ok",
        "service": "scoping",
    }
