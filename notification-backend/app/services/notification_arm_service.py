

import logging
from typing import Any, Dict

from app.azure.arm_deployment_manager import (
    ARMDeploymentManager,
)


logger = logging.getLogger(__name__)


class NotificationARMService:
    """
    High-level Notification ARM deployment service.

    Deployment flow:

        1. Create/verify Resource Group.
        2. Resolve existing Qualys Function URL.
        3. Resolve Notification Service Logic App HTTP trigger URL.
        4. Pass both URLs explicitly to ARM:
              - qualysIntegrationUrl
              - notificationServiceUrl
        5. Deploy ARM template.
        6. Return deployed resources.

    IMPORTANT:
        auditLogTableName and qualysDashboardUrl are intentionally
        not used anymore.
    """

    def __init__(
        self,
        arm_template_path: str,
    ):
        self.arm_template_path = arm_template_path

    def deploy(
        self,
        *,
        subscription_id: str,
        resource_group_name: str,
        location: str,
        storage_account_name: str,

        # -----------------------------------------------------
        # Existing Notification Logic Apps
        # -----------------------------------------------------

        logic_app_name: str,
        completion_logic_app_name: str,
        notification_followup_logic_app_name: str,

        # -----------------------------------------------------
        # Notification Service Logic App trigger
        # -----------------------------------------------------

        notification_logic_app_name: str,
        notification_trigger_name: str,

        # -----------------------------------------------------
        # Queue
        # -----------------------------------------------------

        followup_queue_name: str,
        qualys_scan_status_queue_name: str,

        # -----------------------------------------------------
        # Tables
        # -----------------------------------------------------

        notification_log_table_name: str,
        notification_status_table_name: str,
        scan_status_log_table_name: str,
        scan_completion_log_table_name: str,

        # -----------------------------------------------------
        # API Connections
        # -----------------------------------------------------

        azure_tables_connection_name: str,
        azure_queues_connection_name: str,
        office365_connection_name: str,
        teams_connection_name: str,

        # -----------------------------------------------------
        # Qualys Function App
        # -----------------------------------------------------

        qualys_function_app_name: str,
        qualys_function_name: str,

        # -----------------------------------------------------
        # Callback secret
        # -----------------------------------------------------

        callback_secret_key: str,
    ) -> Dict[str, Any]:

        logger.info(
            "Starting Notification ARM deployment"
        )

        # =====================================================
        # 1. ARM MANAGER
        # =====================================================

        arm_manager = ARMDeploymentManager(
            subscription_id=subscription_id
        )

        # =====================================================
        # 2. RESOURCE GROUP
        # =====================================================

        resource_group = (
            arm_manager.ensure_resource_group(
                resource_group_name=resource_group_name,
                location=location,
            )
        )

        logger.info(
            "Resource Group ready: %s",
            resource_group.name,
        )

        # =====================================================
        # 3. VALIDATE QUALYS FUNCTION
        # =====================================================

        if not qualys_function_app_name:
            raise ValueError(
                "qualys_function_app_name is required"
            )

        if not qualys_function_name:
            raise ValueError(
                "qualys_function_name is required"
            )

        # =====================================================
        # 4. GET QUALYS FUNCTION URL
        # =====================================================

        logger.info(
            "Resolving Qualys Function URL. "
            "Function App: %s, Function: %s",
            qualys_function_app_name,
            qualys_function_name,
        )

        qualys_integration_url = (
            arm_manager.get_function_url(
                resource_group_name=resource_group_name,
                function_app_name=qualys_function_app_name,
                function_name=qualys_function_name,
            )
        )

        if not qualys_integration_url:
            raise RuntimeError(
                "Unable to resolve Qualys Integration Function URL"
            )

        logger.info(
            "Qualys Function URL resolved successfully"
        )

        # =====================================================
        # 5. GET NOTIFICATION SERVICE CALLBACK URL
        # =====================================================

        if not notification_logic_app_name:
            raise ValueError(
                "notification_logic_app_name is required"
            )

        if not notification_trigger_name:
            raise ValueError(
                "notification_trigger_name is required"
            )

        logger.info(
            "Resolving Notification Service callback URL. "
            "Logic App: %s, Trigger: %s",
            notification_logic_app_name,
            notification_trigger_name,
        )

        notification_service_url = (
            arm_manager.get_logic_app_trigger_callback_url(
                resource_group_name=resource_group_name,
                logic_app_name=notification_logic_app_name,
                trigger_name=notification_trigger_name,
            )
        )

        if not notification_service_url:
            raise RuntimeError(
                "Unable to resolve Notification Service "
                "Logic App callback URL"
            )

        logger.info(
            "Notification Service callback URL resolved successfully"
        )

        # =====================================================
        # 6. ARM PARAMETERS
        #
        # IMPORTANT:
        #
        # The ARM template contains:
        #
        #     qualysIntegrationUrl
        #
        # Therefore we MUST send exactly:
        #
        #     "qualysIntegrationUrl":
        #         qualys_integration_url
        #
        # This fixes:
        #
        # InvalidTemplate:
        # The value for template parameter
        # 'qualysIntegrationUrl' is not provided.
        # =====================================================

        parameters = {

            # -------------------------------------------------
            # Storage
            # -------------------------------------------------

            "storageAccountName":
                storage_account_name,

            "location":
                location,

            # -------------------------------------------------
            # Notification Logic Apps
            # -------------------------------------------------

            "logicAppName":
                logic_app_name,

            "completionLogicAppName":
                completion_logic_app_name,

            "notificationFollowupLogicAppName":
                notification_followup_logic_app_name,

            # -------------------------------------------------
            # Queue
            # -------------------------------------------------

            "followupQueueName":
                followup_queue_name,

            "qualysScanStatusQueueName":
                qualys_scan_status_queue_name,

            # -------------------------------------------------
            # Tables
            # -------------------------------------------------

            "notificationLogTableName":
                notification_log_table_name,

            "NotificationStatus":
                notification_status_table_name,

            "scanStatusLogTableName":
                scan_status_log_table_name,

            "scanCompletionLogTableName":
                scan_completion_log_table_name,

            # -------------------------------------------------
            # API Connections
            # -------------------------------------------------

            "azureTablesConnectionName":
                azure_tables_connection_name,

            "azureQueuesConnectionName":
                azure_queues_connection_name,

            "office365ConnectionName":
                office365_connection_name,

            "teamsConnectionName":
                teams_connection_name,

            # -------------------------------------------------
            # Callback
            # -------------------------------------------------

            "callbackSecretKey":
                callback_secret_key,

            # -------------------------------------------------
            # Qualys Scan Status Logic App
            # -------------------------------------------------

            "qualysScanStatusLogicAppName":
                "LA-QualysScan-Status",

            # -------------------------------------------------
            # CRITICAL:
            # Backend-resolved Qualys Function URL
            # -------------------------------------------------

            "qualysIntegrationUrl":
                qualys_integration_url,

            # -------------------------------------------------
            # CRITICAL:
            # Backend-resolved Notification Service URL
            # -------------------------------------------------

            "notificationServiceUrl":
                notification_service_url,
        }

        logger.info(
            "ARM parameters prepared successfully"
        )

        # Debug only the parameter names.
        # Do NOT log the actual URLs because they may contain
        # SAS/function keys.

        logger.info(
            "ARM parameter names: %s",
            list(parameters.keys()),
        )

        # =====================================================
        # 7. DEPLOY ARM TEMPLATE
        # =====================================================

        deployment_result = (
            arm_manager.deploy_arm_template(
                resource_group_name=resource_group_name,
                template_path=self.arm_template_path,
                parameters=parameters,
            )
        )

        logger.info(
            "Notification ARM deployment completed successfully"
        )

        # =====================================================
        # 8. LIST RESOURCES
        # =====================================================

        resources = (
            arm_manager.list_resource_group_resources(
                resource_group_name
            )
        )

        # =====================================================
        # 9. EXTRACT LOGIC APPS
        # =====================================================

        logic_apps = []

        connections = []

        for resource in resources:

            resource_type = (
                resource.get("type", "")
            )

            if resource_type.lower() == (
                "microsoft.logic/workflows"
            ).lower():

                logic_apps.append(resource)

            elif resource_type.lower() == (
                "microsoft.web/connections"
            ).lower():

                connections.append(resource)

        # =====================================================
        # 10. FIND QUALYS STATUS LOGIC APP
        # =====================================================

        qualys_logic_app = None

        for logic_app in logic_apps:

            if logic_app.get("name") == (
                "LA-QualysScan-Status"
            ):

                qualys_logic_app = logic_app
                break

        # =====================================================
        # 11. FINAL RESPONSE
        # =====================================================

        return {

            "success": True,

            "resource_group":
                resource_group_name,

            "location":
                location,

            "deployment":
                deployment_result,

            "qualys_function_app_name":
                qualys_function_app_name,

            "qualys_function_name":
                qualys_function_name,

            "qualys_integration_url":
                qualys_integration_url,

            "notification_logic_app_name":
                notification_logic_app_name,

            "notification_trigger_name":
                notification_trigger_name,

            "notification_service_url":
                notification_service_url,

            "qualys_logic_app":
                qualys_logic_app,

            "logic_apps":
                logic_apps,

            "connections":
                connections,

            "resources":
                resources,
        }