

from pydantic import BaseModel, Field


class NotificationARMDeploymentRequest(BaseModel):
    """
    Request model for Notification ARM deployment.

    Only the values that are environment-specific or need to be
    selected by the user are required.

    All Notification/Qualys resource names that have agreed defaults
    are defaulted here.
    """

    # =========================================================
    # AZURE
    # =========================================================

    subscription_id: str = Field(
        ...,
        min_length=1,
        description="Azure Subscription ID",
    )

    resource_group_name: str = Field(
        ...,
        min_length=1,
        description="Azure Resource Group name",
    )

    location: str = Field(
        ...,
        min_length=1,
        description="Azure region",
    )

    # =========================================================
    # STORAGE
    # =========================================================

    storage_account_name: str = Field(
        ...,
        min_length=3,
        description="Azure Storage Account name",
    )

    # =========================================================
    # NOTIFICATION LOGIC APP
    #
    # These are user supplied because the Notification Service
    # Logic App must already exist/be deployed before its callback
    # URL can be obtained.
    # =========================================================

    notification_logic_app_name: str = Field(
        "Notification-service",
        min_length=1,
        description="Notification Service Logic App name",
    )

    notification_trigger_name: str = Field(
        "When_a_HTTP_request_is_received",
        min_length=1,
        description="HTTP request trigger name of Notification Service Logic App",
    )

    # =========================================================
    # QUALYS FUNCTION APP
    # =========================================================

    qualys_function_app_name: str = Field(
        ...,
        min_length=1,
        description="Existing Qualys Function App name",
    )

    qualys_function_name: str = Field(
        ...,
        min_length=1,
        description="Existing Qualys Function name",
    )

    # =========================================================
    # EXISTING NOTIFICATION LOGIC APPS
    # =========================================================

    logic_app_name: str = Field(
        "Notification-service",
        min_length=1,
        description="Main Notification Logic App name",
    )

    completion_logic_app_name: str = Field(
        "Completion-logic",
        min_length=1,
        description="Completion Logic App name",
    )

    notification_followup_logic_app_name: str = Field(
        "Notification-Followup-01",
        min_length=1,
        description="Notification Follow-up Logic App name",
    )

    # =========================================================
    # QUEUE
    # =========================================================

    followup_queue_name: str = Field(
        "taskreminder",
        min_length=1,
        description="Notification follow-up queue name",
    )

    qualys_scan_status_queue_name: str = Field(
        "qualysscanstatusqueue",
        min_length=1,
        description="Qualys Scan Status queue name",
    )

    # =========================================================
    # TABLES
    #
    # IMPORTANT:
    # audit_log_table_name has intentionally been removed.
    # =========================================================

    notification_log_table_name: str = Field(
        "NotificationLogs",
        min_length=1,
        description="Notification Logs table name",
    )

    notification_status_table_name: str = Field(
        "NotificationStatus",
        min_length=1,
        description="Notification Status table name",
    )

    scan_status_log_table_name: str = Field(
        "ScanStatusLog",
        min_length=1,
        description="Scan Status Log table name",
    )

    scan_completion_log_table_name: str = Field(
        "ScanCompletionLog",
        min_length=1,
        description="Scan Completion Log table name",
    )

    # =========================================================
    # API CONNECTIONS
    # =========================================================

    azure_tables_connection_name: str = Field(
        "azuretables-1",
        min_length=1,
        description="Azure Tables API connection name",
    )

    azure_queues_connection_name: str = Field(
        "azurequeues-1",
        min_length=1,
        description="Azure Queues API connection name",
    )

    office365_connection_name: str = Field(
        "office365-1",
        min_length=1,
        description="Office 365 API connection name",
    )

    teams_connection_name: str = Field(
        "teams-1",
        min_length=1,
        description="Microsoft Teams API connection name",
    )
