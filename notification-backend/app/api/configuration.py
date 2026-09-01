import logging

from fastapi import APIRouter, HTTPException

from app.schemas.configuration_import import (
    ConfigurationDeploymentRequest
)

from app.services.configuration_import_service import (
    ConfigurationImportService
)

from app.azure.tables import (
    get_table_storage_service
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/configuration",
    tags=["Configuration"]
)


# ============================================================
# DEPENDENCY
# ============================================================

def get_configuration_import_service(
    request: ConfigurationDeploymentRequest
):

    # --------------------------------------------------------
    # Storage details come from workflow deployment phase
    # --------------------------------------------------------

    storage_account_name = (
        request.storage_account_name
    )

    resource_group_name = (
        request.resource_group_name
    )

    if not storage_account_name:

        raise HTTPException(
            status_code=400,
            detail="storage_account_name is required."
        )

    if not resource_group_name:

        raise HTTPException(
            status_code=400,
            detail="resource_group_name is required."
        )

    # --------------------------------------------------------
    # Create storage service
    # --------------------------------------------------------

    table_storage_service = (
        get_table_storage_service(
            resource_group_name=resource_group_name,
            storage_account_name=storage_account_name
        )
    )

    return ConfigurationImportService(
        table_storage_service
    )


# ============================================================
# DEPLOY CONFIGURATION
# ============================================================

@router.post("/deploy")
def deploy_configuration(
    request: ConfigurationDeploymentRequest
):

    try:

        logger.info(
            "Starting configuration deployment"
        )

        # ----------------------------------------------------
        # CREATE SERVICE
        # ----------------------------------------------------

        service = get_configuration_import_service(
            request
        )

        result = {}

        # ----------------------------------------------------
        # APP CONFIGURATION
        # ----------------------------------------------------

        if request.app_configuration:

            result["AppConfiguration"] = (
                service.process_app_configuration(
                    request.app_configuration
                )
            )

        # ----------------------------------------------------
        # EMAIL CONFIGURATION
        # ----------------------------------------------------

        if request.email_configuration:

            result["EmailRecipientConfiguration"] = (
                service.process_email_configuration(
                    request.email_configuration
                )
            )

        # ----------------------------------------------------
        # NOTIFICATION TEMPLATES
        #
        # No user input required.
        #
        # Data comes directly from:
        #
        # data/NotificationTemplates.csv
        #
        # The service reads the CSV and uploads the
        # entities in batches of 15.
        # ----------------------------------------------------

        logger.info(
            "Importing NotificationTemplates.csv"
        )

        result["NotificationTemplates"] = (
            service.process_notification_templates()
        )

        # ----------------------------------------------------
        # NOTIFICATION CONFIGURATION
        # ----------------------------------------------------

        if request.notification_configuration:

            result["NotificationConfiguration"] = (
                service.process_notification_configuration(
                    request.notification_configuration
                )
            )

        # ----------------------------------------------------
        # TEAMS CONFIGURATION
        # ----------------------------------------------------

        if request.teams_configuration:

            result["TeamsRecipientConfiguration"] = (
                service.process_teams_configuration(
                    request.teams_configuration
                )
            )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        logger.info(
            "Configuration deployment completed successfully"
        )

        return {
            "success": True,
            "message": (
                "Configuration deployment completed successfully."
            ),
            "results": result
        }

    # ========================================================
    # VALIDATION ERROR
    # ========================================================

    except ValueError as error:

        logger.error(
            "Configuration validation failed: %s",
            error
        )

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    # ========================================================
    # OTHER ERROR
    # ========================================================

    except Exception as error:

        logger.exception(
            "Configuration deployment failed"
        )

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )