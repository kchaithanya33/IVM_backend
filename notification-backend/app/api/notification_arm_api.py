

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.notification_arm_schema import (
    NotificationARMDeploymentRequest,
)

from app.services.notification_arm_service import (
    NotificationARMService,
)

from app.core.config import settings


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/notification-arm",
    tags=["Notification ARM Deployment"],
)


notification_arm_service = (
    NotificationARMService(
        arm_template_path=
            settings.notification_arm_template
    )
)


@router.post("/deploy")
def deploy_notification_service(
    request: NotificationARMDeploymentRequest,
):

    logger.info(
        "Notification ARM deployment requested"
    )

    try:

        result = (
            notification_arm_service.deploy(

                # =================================================
                # AZURE
                # =================================================

                subscription_id=
                    request.subscription_id,

                resource_group_name=
                    request.resource_group_name,

                location=
                    request.location,

                # =================================================
                # STORAGE
                # =================================================

                storage_account_name=
                    request.storage_account_name,

                # =================================================
                # NOTIFICATION LOGIC APPS
                # =================================================

                logic_app_name=
                    request.logic_app_name,

                completion_logic_app_name=
                    request.completion_logic_app_name,

                notification_followup_logic_app_name=
                    request.notification_followup_logic_app_name,

                # =================================================
                # NOTIFICATION SERVICE CALLBACK
                # =================================================

                notification_logic_app_name=
                    request.notification_logic_app_name,

                notification_trigger_name=
                    request.notification_trigger_name,

                # =================================================
                # QUEUES
                # =================================================

                followup_queue_name=
                    request.followup_queue_name,

                qualys_scan_status_queue_name=
                    request.qualys_scan_status_queue_name,

                # =================================================
                # TABLES
                # =================================================

                notification_log_table_name=
                    request.notification_log_table_name,

                notification_status_table_name=
                    request.notification_status_table_name,

                scan_status_log_table_name=
                    request.scan_status_log_table_name,

                scan_completion_log_table_name=
                    request.scan_completion_log_table_name,

                # =================================================
                # API CONNECTIONS
                # =================================================

                azure_tables_connection_name=
                    request.azure_tables_connection_name,

                azure_queues_connection_name=
                    request.azure_queues_connection_name,

                office365_connection_name=
                    request.office365_connection_name,

                teams_connection_name=
                    request.teams_connection_name,

                # =================================================
                # QUALYS FUNCTION
                # =================================================

                qualys_function_app_name=
                    request.qualys_function_app_name,

                qualys_function_name=
                    request.qualys_function_name,

                # =================================================
                # CALLBACK SECRET
                # =================================================

                callback_secret_key=
                    settings.callback_secret_key,
            )
        )

        return result

    except FileNotFoundError as exc:

        logger.exception(
            "Notification ARM template not found"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    except ValueError as exc:

        logger.exception(
            "Invalid Notification ARM deployment request"
        )

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        logger.exception(
            "Notification ARM deployment failed"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )
