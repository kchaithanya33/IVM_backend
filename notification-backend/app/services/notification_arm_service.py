import logging
from typing import Dict, Any

from app.azure.arm_deployment_manager import (
    ARMDeploymentManager,
)


logger = logging.getLogger(__name__)


class NotificationARMService:
    """
    High-level Notification Service deployment.

    This replaces the notification deployment shell script.
    """

    def __init__(
        self,
        arm_template_path: str,
    ):

        self.arm_template_path = (
            arm_template_path
        )

    def deploy(
        self,
        *,
        subscription_id: str,
        resource_group_name: str,
        location: str,
        storage_account_name: str,
        logic_app_name: str,
        completion_logic_app_name: str,
        notification_followup_logic_app_name: str,
        followup_queue_name: str,
        notification_log_table_name: str,
        notification_status_table_name: str,
        azure_tables_connection_name: str,
        azure_queues_connection_name: str,
        office365_connection_name: str,
        teams_connection_name: str,
        callback_secret_key: str,
    ) -> Dict[str, Any]:

        logger.info(
            "Starting Notification ARM deployment"
        )

        # =====================================================
        # 1. Azure ARM Manager
        # =====================================================

        arm_manager = ARMDeploymentManager(
            subscription_id=subscription_id
        )

        # =====================================================
        # 2. Resource Group
        # =====================================================

        resource_group = (
            arm_manager.ensure_resource_group(
                resource_group_name=
                    resource_group_name,
                location=location,
            )
        )

        logger.info(
            "Resource Group ready: %s",
            resource_group.name,
        )

        # =====================================================
        # 3. ARM PARAMETERS
        # =====================================================

        parameters = {

            "storageAccountName":
                storage_account_name,

            "location":
                location,

            "logicAppName":
                logic_app_name,

            "notificationFollowupLogicAppName":
                notification_followup_logic_app_name,

            "completionLogicAppName":
                completion_logic_app_name,

            "notificationLogTableName":
                notification_log_table_name,

            "NotificationStatus":
                notification_status_table_name,

            "azureTablesConnectionName":
                azure_tables_connection_name,

            "azureQueuesConnectionName":
                azure_queues_connection_name,

            "office365ConnectionName":
                office365_connection_name,

            "teamsConnectionName":
                teams_connection_name,

            "followupQueueName":
                followup_queue_name,

            "callbackSecretKey":
                callback_secret_key,
        }

        # =====================================================
        # 4. ARM DEPLOYMENT
        # =====================================================

        deployment_result = (
            arm_manager.deploy_arm_template(
                resource_group_name=
                    resource_group_name,

                template_path=
                    self.arm_template_path,

                parameters=parameters,
            )
        )

        # =====================================================
        # 5. LIST DEPLOYED RESOURCES
        # =====================================================

        resources = (
            arm_manager
            .list_resource_group_resources(
                resource_group_name
            )
        )

        # =====================================================
        # 6. Extract relevant resources
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

                logic_apps.append(
                    resource
                )

            if resource_type.lower() == (
                "microsoft.web/connections"
            ).lower():

                connections.append(
                    resource
                )

        # =====================================================
        # 7. Final response
        # =====================================================

        return {

            "success": True,

            "resource_group":
                resource_group_name,

            "location":
                location,

            "deployment":
                deployment_result,

            "logic_apps":
                logic_apps,

            "connections":
                connections,

            "resources":
                resources,
        }