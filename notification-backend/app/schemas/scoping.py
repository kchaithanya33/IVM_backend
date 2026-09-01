from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# SCOPING DEPLOYMENT REQUEST
# ============================================================

class ScopingDeploymentRequest(BaseModel):
    """
    Request received from the frontend for Scoping-00 deployment.

    Function App name and function names are supplied by the user.
    The backend dynamically resolves the actual Function URLs.
    """

    # --------------------------------------------------------
    # Azure infrastructure
    # --------------------------------------------------------

    subscription_id: str = Field(..., min_length=1)

    resource_group_name: str = Field(..., min_length=1)

    location: str = Field(..., min_length=1)

    # --------------------------------------------------------
    # Logic App
    # --------------------------------------------------------

    logic_app_name: str = Field(
        default="LA-Scoping-00",
        min_length=1,
    )

    # --------------------------------------------------------
    # Storage
    # --------------------------------------------------------

    storage_account_name: str = Field(..., min_length=1)

    scoping_schedule_queue_name: str = Field(..., min_length=1)

    notification_log_table_name: str = Field(..., min_length=1)

    # --------------------------------------------------------
    # Completion callback
    # --------------------------------------------------------

    completion_logic_app_url: str = Field(..., min_length=1)

    callback_secret_key: str = Field(..., min_length=1)

    # --------------------------------------------------------
    # Notification service
    # --------------------------------------------------------

    notification_service_url: str = Field(..., min_length=1)

    # --------------------------------------------------------
    # Function App
    # --------------------------------------------------------

    function_app_name: str = Field(..., min_length=1)

    # --------------------------------------------------------
    # Function names
    # --------------------------------------------------------

    config_function_name: str = Field(
        default="config",
        min_length=1,
    )

    business_day_hour_status_function_name: str = Field(
        default="businessdayhourstatus",
        min_length=1,
    )

    get_next_business_day_function_name: str = Field(
        default="GetNextBusinessDay",
        min_length=1,
    )

    # --------------------------------------------------------
    # Logic App API connection names
    # --------------------------------------------------------

    table_connection_name: str = Field(
        default="azuretables-1",
        min_length=1,
    )

    queue_connection_name: str = Field(
        default="azurequeues-1",
        min_length=1,
    )


# ============================================================
# SCOPING DEPLOYMENT RESPONSE
# ============================================================

class ScopingDeploymentResponse(BaseModel):
    success: bool

    message: str

    subscription_id: str

    resource_group_name: str

    location: str

    logic_app_name: str

    storage_account_name: str

    # --------------------------------------------------------
    # Resolved connection IDs
    # --------------------------------------------------------

    table_connection_id: Optional[str] = None

    queue_connection_id: Optional[str] = None

    # --------------------------------------------------------
    # Dynamically resolved Function URLs
    # --------------------------------------------------------

    config_service_url: Optional[str] = None

    business_day_hour_status_url: Optional[str] = None

    get_next_business_day_url: Optional[str] = None

    # --------------------------------------------------------
    # ARM deployment information
    # --------------------------------------------------------

    deployment_name: Optional[str] = None

    provisioning_state: Optional[str] = None