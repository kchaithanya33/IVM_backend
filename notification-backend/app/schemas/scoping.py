

from typing import Optional

from pydantic import BaseModel


# ============================================================
# FUNCTION URLS
# ============================================================

class ScopingFunctionUrls(BaseModel):

    config_service_url: str

    business_day_hour_status_url: str

    get_next_business_day_url: str

    call_azure_function_url: str

    # Scoping-02
    process_asset_data_url: str

    create_asset_groups_url: str

    error_processor_url: str

    check_working_hours_url: str


# ============================================================
# LOGIC APP URLS
# ============================================================

class ScopingLogicAppUrls(BaseModel):

    notification_service_url: str

    completion_logic_app_url: str

    # This URL is obtained only AFTER Scoping-02 is deployed.
    scoping02_logic_app_url: Optional[str] = None


# ============================================================
# DEPLOYMENT REQUEST
# ============================================================

class ScopingDeploymentRequest(BaseModel):

    # --------------------------------------------------------
    # AZURE
    # --------------------------------------------------------

    subscription_id: str

    resource_group_name: str

    location: str

    # --------------------------------------------------------
    # SCOPING LOGIC APPS
    # --------------------------------------------------------

    logic_app_name: str = "LA-Scoping-00"

    scoping01_logic_app_name: str = "LA-Scoping-01"

    scoping02_logic_app_name: str = "LA-Scoping-02"

    # --------------------------------------------------------
    # STORAGE
    # --------------------------------------------------------

    storage_account_name: str

    scoping_schedule_queue_name: str

    notification_log_table_name: str

    # --------------------------------------------------------
    # SHAREPOINT
    # --------------------------------------------------------

    share_point_url: str

    sharepoint_connection_name: str = "sharepointonline-1"

    # --------------------------------------------------------
    # COMPLETION LOGIC APP
    # --------------------------------------------------------

    completion_logic_app_name: str

    completion_logic_app_trigger_name: str

    # --------------------------------------------------------
    # SCOPING-02 LOGIC APP
    # --------------------------------------------------------

    scoping02_logic_app_trigger_name: str

    # --------------------------------------------------------
    # CALLBACK
    # --------------------------------------------------------

    callback_secret_key: str

    # --------------------------------------------------------
    # NOTIFICATION LOGIC APP
    # --------------------------------------------------------

    notification_logic_app_name: str

    notification_logic_app_trigger_name: str

    notification_status: str

    # --------------------------------------------------------
    # FUNCTION APP
    # --------------------------------------------------------

    function_app_name: str

    # Existing functions

    config_function_name: str = "GetPartitionConfigs"

    business_day_hour_status_function_name: str = (
        "IsBusinessDayAndHour"
    )

    get_next_business_day_function_name: str = (
        "GetNextBusinessDay"
    )

    call_azure_function_name: str = (
        "ProcessAzureIPData"
    )

    # --------------------------------------------------------
    # SCOPING-02 FUNCTIONS
    # --------------------------------------------------------

    process_asset_data_function_name: str

    create_asset_groups_function_name: str

    error_processor_function_name: str

    check_working_hours_function_name: str

    # --------------------------------------------------------
    # API CONNECTIONS
    # --------------------------------------------------------

    table_connection_name: str = "azuretables-1"

    queue_connection_name: str = "azurequeues-1"


# ============================================================
# DEPLOYMENT RESPONSE
# ============================================================

class ScopingDeploymentResponse(BaseModel):

    success: bool

    message: str

    subscription_id: str

    resource_group_name: str

    location: str

    logic_app_name: str

    scoping01_logic_app_name: str

    scoping02_logic_app_name: str

    storage_account_name: str

    # Final deployment names
    deployment_name: Optional[str] = None

    # Optional individual deployment names
    scoping02_deployment_name: Optional[str] = None

    scoping00_01_deployment_name: Optional[str] = None

    provisioning_state: Optional[str] = None

    scoping02_provisioning_state: Optional[str] = None

    scoping00_01_provisioning_state: Optional[str] = None

    table_connection_id: Optional[str] = None

    queue_connection_id: Optional[str] = None

    sharepoint_connection_id: Optional[str] = None

    function_urls: Optional[
        ScopingFunctionUrls
    ] = None

    logic_app_urls: Optional[
        ScopingLogicAppUrls
    ] = None
