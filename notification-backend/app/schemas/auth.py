from typing import Optional

from pydantic import BaseModel, Field


class AuthScanFunctionUrls(BaseModel):
    config_service_url: str
    business_days_service_url: str
    get_next_business_day_url: str
    qualys_scan_fetch_function_url: str
    qualys_auth_function_url: str
    qualys_auth_failure_analysis_function_url: str


class AuthScanLogicAppUrls(BaseModel):
    notification_service_url: str
    auth_scan02_logic_app_url: str


class AuthScanDeploymentRequest(BaseModel):
    subscription_id: str = Field(
        ...,
        description="Azure subscription ID",
    )
    resource_group_name: str = Field(
        ...,
        description="Azure resource group name",
    )
    location: str = Field(
        ...,
        description="Azure deployment location",
    )

    auth_scan01_logic_app_name: str = Field(
        default="LA-AuthScan-01",
    )
    auth_scan02_logic_app_name: str = Field(
        default="LA-AuthScan-02",
    )
    auth_scan02_logic_app_trigger_name: str = Field(
        default="When_scan_result_processing_request_received",
    )

    storage_account_name: Optional[str] = Field(
        default=None,
        description="Optional storage account name. If omitted, it is discovered from the resource group.",
    )

    authscan_queue_name: str = Field(default="authscan00")
    auth_scan_execution_queue_name: str = Field(
        default="authscanresultshandlerqueue"
    )
    qualys_scan_status_queue_name: str = Field(
        default="qualysscanstatusqueue"
    )
    vulnscan_queue_name: str = Field(default="vulnscan00")

    audit_log_table_name: str = Field(default="NotificationLogs")
    auth_scan_results_table_name: str = Field(default="AuthScanResults")
    cycle_table_name: str = Field(default="Cycles")

    share_point_url: Optional[str] = Field(
        default=None,
        description="Optional SharePoint site URL",
    )

    notification_logic_app_name: str = Field(
        ...,
        description="Existing Notification Logic App name",
    )
    notification_logic_app_trigger_name: str = Field(
        default="When_a_HTTP_request_is_received",
    )

    function_app_name: str = Field(
        ...,
        description="Existing Function App name",
    )
    
    excelipexractor: str = Field(
        ...,
        description="Excel IP Extractor Azure Function name",
    )

    config_service_function_name: str = Field(
        default="GetPartitionConfigs"
    )
    business_days_service_function_name: str = Field(
        default="IsBusinessDayAndHour"
    )
    get_next_business_day_function_name: str = Field(
        default="GetNextBusinessDay"
    )
    qualys_scan_fetch_function_name: str = Field(...)
    qualys_auth_function_name: str = Field(...)
    qualys_auth_failure_analysis_function_name: str = Field(...)

    table_connection_name: str = Field(default="azuretables-1")
    queue_connection_name: str = Field(default="azurequeues-1")
    sharepoint_connection_name: str = Field(default="sharepointonline-1")
    office365_connection_name: str = Field(default="office365-1")

    auth_scan_profile: str = Field(default="Auth check")
    qualys_scanner_name: str = Field(default="defaultscanner")
    scanner_id: str = Field(default="azeunqlsp001")
    mey_diageo_scanner: str = Field(default="MeyDiageo")
    diageo_scanners: str = Field(
        default="azeunqlsp001,azeunqlsp002,DCBVQLS202"
    )

    qualys_api_url: Optional[str] = None
    qualys_dashboard_url: Optional[str] = None
    servicenow_api_url: Optional[str] = None
    mulesoft_api_key: Optional[str] = None
    vuln_scan_trigger_url: Optional[str] = None
    asset_service_url: Optional[str] = None
    key_vault_url: Optional[str] = None


class AuthScanDeploymentResponse(BaseModel):
    success: bool
    message: str

    subscription_id: str
    resource_group_name: str
    location: str

    auth_scan01_logic_app_name: str
    auth_scan02_logic_app_name: str

    storage_account_name: str

    auth_scan02_deployment_name: Optional[str] = None
    auth_scan01_deployment_name: Optional[str] = None

    auth_scan02_provisioning_state: Optional[str] = None
    auth_scan01_provisioning_state: Optional[str] = None

    table_connection_id: Optional[str] = None
    queue_connection_id: Optional[str] = None
    sharepoint_connection_id: Optional[str] = None
    office365_connection_id: Optional[str] = None

    function_urls: Optional[AuthScanFunctionUrls] = None
    logic_app_urls: Optional[AuthScanLogicAppUrls] = None
