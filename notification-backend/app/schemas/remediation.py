from typing import Optional

from pydantic import BaseModel


# ============================================================
# REMEDIATION FUNCTION URLS
# ============================================================

class RemediationFunctionUrls(BaseModel):
    config_service_url: str
    qualys_asset_group_creation_function_url: str
    qualys_scan_function_url: str

    # --------------------------------------------------------
    # Remediation 01 Function URLs
    # --------------------------------------------------------

    excel_processing_function_url: Optional[str] = None
    qualys_qid_option_profile_url: Optional[str] = None
    dfn_file_content_function_url: Optional[str] = None
    cmdb_ip_extractor_function_url: Optional[str] = None
    all_ip_qid_extractor_function_url: Optional[str] = None

    # --------------------------------------------------------
    # Remediation 0.5 Function URLs
    # --------------------------------------------------------

    business_days_service_url: Optional[str] = None
    get_next_business_day_url: Optional[str] = None

    # --------------------------------------------------------
    # Remediation 00 Function URLs
    # --------------------------------------------------------

    row_counter_function_url: Optional[str] = None


# ============================================================
# REMEDIATION DEPLOYMENT REQUEST
# ============================================================

class RemediationDeploymentRequest(BaseModel):

    # --------------------------------------------------------
    # Azure
    # --------------------------------------------------------

    subscription_id: str
    resource_group_name: str
    location: str = "canadacentral"

    # --------------------------------------------------------
    # Logic App - Remediation 02
    # Existing logic untouched
    # --------------------------------------------------------

    logic_app_name: str = "LA-Remediation-02"

    # --------------------------------------------------------
    # Logic App - Remediation 01
    # --------------------------------------------------------

    remediation_01_logic_app_name: str = "LA-Remediation-01"
    remediation_05_logic_app_name: str = "LA-Remediation-0.5"

    # --------------------------------------------------------
    # Logic App - Remediation 00
    # --------------------------------------------------------

    remediation_00_logic_app_name: str = "LA-Remediation-00"

    # --------------------------------------------------------
    # Storage
    # --------------------------------------------------------

    storage_account_name: str

    # --------------------------------------------------------
    # Audit table
    # --------------------------------------------------------

    audit_log_table_name: str = "NotificationLogs"

    # --------------------------------------------------------
    # Qualys scan status queue
    # --------------------------------------------------------

    qualys_scan_status_queue_name: str = "qualysscanstatusqueue"

    # --------------------------------------------------------
    # SharePoint
    # Used by Remediation 01
    # --------------------------------------------------------

    share_point_site_url: str

    # --------------------------------------------------------
    # Function 1
    # Configuration Service
    # Existing Remediation 02 logic
    # --------------------------------------------------------

    config_function_app_name: str
    config_function_name: str

    # --------------------------------------------------------
    # Function 2
    # Qualys Asset Group Creation
    # Existing Remediation 02 logic
    # --------------------------------------------------------

    qualys_asset_group_function_app_name: str
    qualys_asset_group_function_name: str

    # --------------------------------------------------------
    # Function 3
    # Qualys Scan
    # Existing Remediation 02 logic
    # --------------------------------------------------------

    qualys_scan_function_app_name: str
    qualys_scan_function_name: str

    # ========================================================
    # REMEDIATION 01 FUNCTIONS
    # ========================================================

    # --------------------------------------------------------
    # Function 4
    # Excel Processing
    # --------------------------------------------------------

    excel_processing_function_app_name: Optional[str] = None
    excel_processing_function_name: Optional[str] = None

    # --------------------------------------------------------
    # Function 5
    # Qualys QID Option Profile
    # --------------------------------------------------------

    qualys_qid_option_profile_function_app_name: Optional[str] = None
    qualys_qid_option_profile_function_name: Optional[str] = None

    # --------------------------------------------------------
    # Function 6
    # DFN File Content
    # --------------------------------------------------------

    dfn_file_content_function_app_name: Optional[str] = None
    dfn_file_content_function_name: Optional[str] = None

    # --------------------------------------------------------
    # Function 7
    # CMDB IP Extractor
    # --------------------------------------------------------

    cmdb_ip_extractor_function_app_name: Optional[str] = None
    cmdb_ip_extractor_function_name: Optional[str] = None

    # --------------------------------------------------------
    # Function 8
    # All IP/QID Extractor
    # --------------------------------------------------------

    all_ip_qid_extractor_function_app_name: Optional[str] = None
    all_ip_qid_extractor_function_name: Optional[str] = None

    # ========================================================
    # REMEDIATION 01 LOGIC APP CALLBACKS
    # ========================================================

    # --------------------------------------------------------
    # Remediation Scan Logic App
    # Used to generate remediationScanUrl
    # --------------------------------------------------------

    remediation_scan_logic_app_name: Optional[str] = None
    remediation_scan_trigger_name: Optional[str] = None

    # --------------------------------------------------------
    # Notification Service Logic App
    # --------------------------------------------------------

    notification_service_logic_app_name: Optional[str] = None
    notification_service_trigger_name: Optional[str] = None

    # ========================================================
    # REMEDIATION 0.5
    # ========================================================

    # --------------------------------------------------------
    # Function 9
    # Business Days Service
    # Used to generate businessDaysServiceUrl
    # --------------------------------------------------------

    business_days_function_app_name: Optional[str] = None
    business_days_function_name: Optional[str] = None

    # --------------------------------------------------------
    # Function 10
    # Get Next Business Day
    # Used to generate getNextBusinessDayUrl
    # --------------------------------------------------------

    get_next_business_day_function_app_name: Optional[str] = None
    get_next_business_day_function_name: Optional[str] = None

  
   

    # ========================================================
    # REMEDIATION 00
    # ========================================================

    # --------------------------------------------------------
    # Function 11
    # Row Counter Function
    # Used to generate rowCounterFunctionUrl
    # --------------------------------------------------------

    row_counter_function_app_name: Optional[str] = None
    row_counter_function_name: Optional[str] = None

    # --------------------------------------------------------
    # DFN Portal
    # Passed directly to LA-Remediation-00
    # --------------------------------------------------------

    dfn_portal_url: Optional[str] = None

    # ========================================================
    # Azure API Connections
    # These are handled by backend.
    # User does not need to provide connection IDs.
    # ========================================================

    table_connection_name: str = "azuretables-1"
    queue_connection_name: str = "azurequeues-1"


# ============================================================
# REMEDIATION DEPLOYMENT RESPONSE
# ============================================================

class RemediationDeploymentResponse(BaseModel):

    success: bool
    message: str

    subscription_id: str
    resource_group_name: str
    location: str

    # --------------------------------------------------------
    # Remediation 02
    # Existing response fields untouched
    # --------------------------------------------------------

    logic_app_name: str
    storage_account_name: str

    # --------------------------------------------------------
    # Remediation 01
    # --------------------------------------------------------

    remediation_01_logic_app_name: Optional[str] = None

    deployment_name: Optional[str] = None
    provisioning_state: Optional[str] = None

    table_connection_id: Optional[str] = None
    queue_connection_id: Optional[str] = None

    function_urls: Optional[RemediationFunctionUrls] = None

    # --------------------------------------------------------
    # Remediation 01 callback URLs
    # --------------------------------------------------------

    remediation_scan_url: Optional[str] = None
    remediation_sas_token: Optional[str] = None
    notification_service_url: Optional[str] = None
    callback_uri_02: Optional[str] = None

    # --------------------------------------------------------
    # Remediation 0.5 callback URL
    # --------------------------------------------------------

   

    # --------------------------------------------------------
    # Remediation 00
    # --------------------------------------------------------

    remediation_00_logic_app_name: Optional[str] = None
    callback_uri_05: Optional[str] = None
    dfn_portal_url: Optional[str] = None