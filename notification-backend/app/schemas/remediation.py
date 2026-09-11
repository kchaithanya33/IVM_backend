from typing import Optional

from pydantic import BaseModel


# ============================================================
# REMEDIATION FUNCTION URLS
# ============================================================

class RemediationFunctionUrls(BaseModel):
    config_service_url: str
    qualys_asset_group_creation_function_url: str
    qualys_scan_function_url: str


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
    # Logic App
    # --------------------------------------------------------

    logic_app_name: str = "LA-Remediation-02"

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
    # Function 1
    # Configuration Service
    # --------------------------------------------------------

    config_function_app_name: str
    config_function_name: str

    # --------------------------------------------------------
    # Function 2
    # Qualys Asset Group Creation
    # --------------------------------------------------------

    qualys_asset_group_function_app_name: str
    qualys_asset_group_function_name: str

    # --------------------------------------------------------
    # Function 3
    # Qualys Scan
    # --------------------------------------------------------

    qualys_scan_function_app_name: str
    qualys_scan_function_name: str

    # --------------------------------------------------------
    # Azure API Connections
    # These are handled by backend.
    # User does not need to provide connection IDs.
    # --------------------------------------------------------

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

    logic_app_name: str
    storage_account_name: str

    deployment_name: Optional[str] = None
    provisioning_state: Optional[str] = None

    table_connection_id: Optional[str] = None
    queue_connection_id: Optional[str] = None

    function_urls: Optional[RemediationFunctionUrls] = None