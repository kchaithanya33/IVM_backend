import logging

from fastapi import (
    APIRouter,
    HTTPException,
)

from app.schemas.key_vault import (
    KeyVaultSetupRequest,
    KeyVaultSetupResponse,
)

from app.services.key_vault_service import (
    KeyVaultSetupService,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/key-vault",
    tags=["Key Vault"],
)


# ============================================================
# KEY VAULT SETUP
# ============================================================

@router.post(
    "/setup",
    response_model=KeyVaultSetupResponse,
)
def setup_key_vault(
    request: KeyVaultSetupRequest,
):

    try:

        logger.info(
            "Received Key Vault setup request."
        )

        service = KeyVaultSetupService()

        response = service.setup(
            request
        )

        logger.info(
            "Key Vault setup completed successfully."
        )

        return response

    except ValueError as exc:

        logger.exception(
            "Key Vault setup validation error."
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:

        logger.exception(
            "Key Vault setup runtime error."
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    except Exception as exc:

        logger.exception(
            "Unexpected Key Vault setup error."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc