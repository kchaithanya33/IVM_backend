

from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# SCOPING DEPLOYMENT REQUEST
# ============================================================

class ScopingDeploymentRequest(BaseModel):
    """
    Request model for deploying:

        LA-Scoping-00
        LA-Scoping-01
        LA-Scoping-02

    Function URLs and Logic App callback URLs are resolved
    dynamically by the backend.

    Frontend supplies:
        - Azure resource names
        - Logic App names
        - Logic App trigger names
        - Function App name
        - Function names
        - configuration values

    Frontend does NOT supply Function URLs.
    Frontend does NOT supply Logic App callback URLs.
    """

    # ========================================================
    # AZURE
    # ========================================================

    subscription_id: str = Field(
        ...,
        min_length=1,
    )

    resource_group_name: str = Field(
        ...,
        min_length=1,
    )

    location: str = Field(
        ...,
        min_length=1,
    )

    # ========================================================
    # LOGIC APPS
    # ========================================================

    logic_app_name: str = Field(
        default="LA-Scoping-00",
    )

    scoping01_logic_app_name: str = Field(
        default="LA-Scoping-01",
    )

    scoping02_logic_app_name: str = Field(
        default="LA-Scoping-02",
    )

    # ========================================================
    # STORAGE / QUEUE / TABLE
    # ========================================================

    storage_account_name: str = Field(
        ...,
        min_length=1,
    )

    scoping_schedule_queue_name: str = Field(
        ...,
        min_length=1,
    )

    notification_log_table_name: str = Field(
        ...,
        min_length=1,
    )

    # ========================================================
    # SHAREPOINT
    # ========================================================

    share_point_url: str = Field(
        ...,
        min_length=1,
    )

    sharepoint_connection_name: str = Field(
        default="sharepointonline-1",
    )

    # ========================================================
    # COMPLETION CALLBACK
    # ========================================================

    completion_logic_app_name: str = Field(
        ...,
        min_length=1,
    )

    completion_logic_app_trigger_name: str = Field(
        ...,
        min_length=1,
    )

    callback_secret_key: str = Field(
        ...,
        min_length=1,
    )

    # ========================================================
    # NOTIFICATION
    # ========================================================

    notification_logic_app_name: str = Field(
        ...,
        min_length=1,
    )

    notification_logic_app_trigger_name: str = Field(
        ...,
        min_length=1,
    )

    notification_status: str = Field(
        ...,
        min_length=1,
    )

    # ========================================================
    # FUNCTION APP
    # ========================================================

    function_app_name: str = Field(
        ...,
        min_length=1,
    )

    # ========================================================
    # EXISTING FUNCTION NAMES
    # ========================================================

    config_function_name: str = Field(
        default="GetPartitionConfigs",
    )

    business_day_hour_status_function_name: str = Field(
        default="IsBusinessDayAndHour",
    )

    get_next_business_day_function_name: str = Field(
        default="GetNextBusinessDay",
    )

    call_azure_function_name: str = Field(
        default="ProcessAzureIPData",
    )

    # ========================================================
    # SCOPING-02 FUNCTION NAMES
    #
    # These names are supplied by the frontend.
    # Backend resolves their actual URLs.
    # ========================================================

    process_asset_data_function_name: str = Field(
        ...,
        min_length=1,
    )

    create_asset_groups_function_name: str = Field(
        ...,
        min_length=1,
    )

    error_processor_function_name: str = Field(
        ...,
        min_length=1,
    )

    check_working_hours_function_name: str = Field(
        ...,
        min_length=1,
    )

    # ========================================================
    # API CONNECTIONS
    # ========================================================

    table_connection_name: str = Field(
        default="azuretables-1",
    )

    queue_connection_name: str = Field(
        default="azurequeues-1",
    )


# ============================================================
# FUNCTION URL INFORMATION
# ============================================================

class ScopingFunctionUrls(BaseModel):
    """
    Azure Function URLs resolved dynamically by backend.
    """

    # Existing Scoping functions

    config_service_url: Optional[str] = None

    business_day_hour_status_url: Optional[str] = None

    get_next_business_day_url: Optional[str] = None

    call_azure_function_url: Optional[str] = None

    # Scoping-02 functions

    process_asset_data_url: Optional[str] = None

    create_asset_groups_url: Optional[str] = None

    error_processor_url: Optional[str] = None

    check_working_hours_url: Optional[str] = None


# ============================================================
# LOGIC APP URL INFORMATION
# ============================================================

class ScopingLogicAppUrls(BaseModel):
    """
    Logic App callback URLs resolved dynamically by backend.
    """

    notification_service_url: Optional[str] = None

    completion_logic_app_url: Optional[str] = None


# ============================================================
# DEPLOYMENT RESPONSE
# ============================================================

class ScopingDeploymentResponse(BaseModel):
    """
    Response returned after Scoping deployment.
    """

    success: bool

    message: str

    # ========================================================
    # AZURE
    # ========================================================

    subscription_id: str

    resource_group_name: str

    location: str

    # ========================================================
    # LOGIC APPS
    # ========================================================

    logic_app_name: str

    scoping01_logic_app_name: str

    scoping02_logic_app_name: Optional[str] = None

    # ========================================================
    # STORAGE
    # ========================================================

    storage_account_name: str

    # ========================================================
    # DEPLOYMENT
    # ========================================================

    deployment_name: Optional[str] = None

    provisioning_state: Optional[str] = None

    # ========================================================
    # API CONNECTIONS
    # ========================================================

    table_connection_id: Optional[str] = None

    queue_connection_id: Optional[str] = None

    sharepoint_connection_id: Optional[str] = None

    # ========================================================
    # FUNCTION URLS
    # ========================================================

    function_urls: Optional[ScopingFunctionUrls] = None

    # ========================================================
    # LOGIC APP URLS
    # ========================================================

    logic_app_urls: Optional[ScopingLogicAppUrls] = None
