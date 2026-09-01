from pydantic import BaseModel, Field


class NotificationARMDeploymentRequest(BaseModel):
    """
    Request model used to deploy the Notification Service
    ARM template.
    """

    # ---------------------------------------------------------
    # Azure
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Storage
    # ---------------------------------------------------------

    storage_account_name: str = Field(
        ...,
        min_length=3,
        description="Azure Storage Account name",
    )

    # ---------------------------------------------------------
    # Logic Apps
    # ---------------------------------------------------------

    logic_app_name: str = Field(
        ...,
        min_length=1,
        description="Main Notification Logic App name",
    )

    completion_logic_app_name: str = Field(
        ...,
        min_length=1,
        description="Completion Logic App name",
    )

    notification_followup_logic_app_name: str = Field(
        ...,
        min_length=1,
        description="Notification Follow-up Logic App name",
    )

    # ---------------------------------------------------------
    # Queue
    # ---------------------------------------------------------

    followup_queue_name: str = Field(
        ...,
        min_length=1,
        description="Follow-up queue name",
    )

    # ---------------------------------------------------------
    # Tables
    # ---------------------------------------------------------

    notification_log_table_name: str = Field(
        ...,
        min_length=1,
        description="Notification Logs table name",
    )

    notification_status_table_name: str = Field(
        ...,
        min_length=1,
        description="Notification Status table name",
    )

    # ---------------------------------------------------------
    # API Connections
    # ---------------------------------------------------------

    azure_tables_connection_name: str = Field(
        ...,
        min_length=1,
        description="Azure Tables API connection name",
    )

    azure_queues_connection_name: str = Field(
        ...,
        min_length=1,
        description="Azure Queues API connection name",
    )

    office365_connection_name: str = Field(
        ...,
        min_length=1,
        description="Office 365 API connection name",
    )

    teams_connection_name: str = Field(
        ...,
        min_length=1,
        description="Microsoft Teams API connection name",
    )