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
    # ============================================================
    # Azure Infrastructure Details
    # ============================================================

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

    # ============================================================
    # Auth Scan Logic Apps
    # ============================================================

    auth_scan01_logic_app_name: str = Field(
        default="LA-AuthScan-01",
    )

    auth_scan02_logic_app_name: str = Field(
        default="LA-AuthScan-02",
    )

    auth_scan02_logic_app_trigger_name: str = Field(
        default="When_scan_result_processing_request_received",
    )

    # ============================================================
    # Storage Account
    # ============================================================

    storage_account_name: Optional[str] = Field(
        default="armstoragechai3",
        description="Storage account name",
    )

    # ============================================================
    # Queues
    # ============================================================

    authscan_queue_name: str = Field(
        default="authscan00",
    )

    auth_scan_execution_queue_name: str = Field(
        default="authscanresultshandlerqueue",
    )

    qualys_scan_status_queue_name: str = Field(
        default="qualysscanstatusqueue",
    )

    vulnscan_queue_name: str = Field(
        default="vulnscan00",
    )

    # ============================================================
    # Azure Tables
    # ============================================================

    audit_log_table_name: str = Field(
        default="NotificationLogs",
    )

    auth_scan_results_table_name: str = Field(
        default="AuthScanResults",
    )

    cycle_table_name: str = Field(
        default="Cycles",
    )

    # ============================================================
    # SharePoint
    # ============================================================

    share_point_url: Optional[str] = Field(
        default=None,
        description="Optional SharePoint site URL",
    )

    # ============================================================
    # Notification Logic App
    # ============================================================

    notification_logic_app_name: str = Field(
        default="notification-logic-chai",
    )

    notification_logic_app_trigger_name: str = Field(
        default="When_a_HTTP_request_is_received",
    )

    # ============================================================
    # Function App
    # ============================================================

    function_app_name: str = Field(
        default="function-app-chai",
    )

    # ============================================================
    # Function Names
    # ============================================================

    excelipexractor: str = Field(
        default="ExcelIPExtractor",
        description="Excel IP Extractor Azure Function name",
    )

    config_service_function_name: str = Field(
        default="GetPartitionConfigs",
    )

    business_days_service_function_name: str = Field(
        default="IsBusinessDayAndHour",
    )

    get_next_business_day_function_name: str = Field(
        default="GetNextBusinessDay",
    )

    qualys_scan_fetch_function_name: str = Field(
        default="QualysScanFetch",
    )

    qualys_auth_function_name: str = Field(
        default="QualysAuthScan",
    )

    qualys_auth_failure_analysis_function_name: str = Field(
        default="QualysAuthFailureAnalysis",
    )

    # ============================================================
    # API Connections
    # ============================================================

    table_connection_name: str = Field(
        default="azuretables-1",
    )

    queue_connection_name: str = Field(
        default="azurequeues-1",
    )

    sharepoint_connection_name: str = Field(
        default="sharepointonline-1",
    )

    office365_connection_name: str = Field(
        default="office365-1",
    )

    # ============================================================
    # Qualys Configuration
    # ============================================================

    auth_scan_profile: str = Field(
        default="Auth check",
    )

    qualys_scanner_name: str = Field(
        default="defaultscanner",
    )

    scanner_id: str = Field(
        default="azeunqlsp001",
    )

    mey_diageo_scanner: str = Field(
        default="MeyDiageo",
    )

    diageo_scanners: str = Field(
        default="azeunqlsp001,azeunqlsp002,DCBVQLS202",
    )

    qualys_api_url: str = Field(
        default="https://qualysapi.qg1.apps.qualys.in",
    )

    qualys_dashboard_url: str = Field(
        default="https://qualysapi.qg1.apps.qualys.in",
    )

    # ============================================================
    # Optional External Services
    # ============================================================

    servicenow_api_url: Optional[str] = Field(
        default=None,
    )

    mulesoft_api_key: Optional[str] = Field(
        default=None,
    )


class AuthScanDeploymentResponse(BaseModel):
    # ============================================================
    # Deployment Status
    # ============================================================

    success: bool
    message: str

    # ============================================================
    # Azure Infrastructure Details
    # ============================================================

    subscription_id: str
    resource_group_name: str
    location: str

    # ============================================================
    # Logic Apps
    # ============================================================

    auth_scan01_logic_app_name: str
    auth_scan02_logic_app_name: str

    # ============================================================
    # Storage Account
    # ============================================================

    storage_account_name: str

    # ============================================================
    # Deployment Names
    # ============================================================

    auth_scan02_deployment_name: Optional[str] = None
    auth_scan01_deployment_name: Optional[str] = None

    # ============================================================
    # Provisioning States
    # ============================================================

    auth_scan02_provisioning_state: Optional[str] = None
    auth_scan01_provisioning_state: Optional[str] = None

    # ============================================================
    # API Connection IDs
    # ============================================================

    table_connection_id: Optional[str] = None
    queue_connection_id: Optional[str] = None
    sharepoint_connection_id: Optional[str] = None
    office365_connection_id: Optional[str] = None

    # ============================================================
    # Function URLs
    # ============================================================

    function_urls: Optional[AuthScanFunctionUrls] = None

    # ============================================================
    # Logic App URLs
    # ============================================================

    logic_app_urls: Optional[AuthScanLogicAppUrls] = None