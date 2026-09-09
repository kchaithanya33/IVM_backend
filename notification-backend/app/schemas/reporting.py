from typing import Optional

from pydantic import BaseModel


# ============================================================
# FUNCTION URLS
# ============================================================

class ReportingFunctionUrls(BaseModel):
    """
    Dynamically resolved Azure Function URLs required
    by the Reporting Logic App.
    """

    split_vulnerabilities_function_url: str


# ============================================================
# LOGIC APP URLS
# ============================================================

class ReportingLogicAppUrls(BaseModel):
    """
    Dynamically resolved Logic App callback URLs.
    """

    notification_service_url: str


# ============================================================
# DEPLOYMENT REQUEST
# ============================================================

class ReportingDeploymentRequest(BaseModel):
    """
    Request model for Reporting deployment.

    The backend dynamically resolves:

        notificationServiceUrl
        splitVulnerabilitiesFunctionUrl

    from the supplied Logic App / Function details.
    """

    # --------------------------------------------------------
    # Azure infrastructure
    # --------------------------------------------------------

    subscription_id: str
    resource_group_name: str
    location: str

    # --------------------------------------------------------
    # Reporting Logic App
    # --------------------------------------------------------

    reporting_logic_app_name: str = "LA-reporting-04"

    # --------------------------------------------------------
    # Storage Account
    # --------------------------------------------------------

    storage_account_name: str

    # --------------------------------------------------------
    # SharePoint
    # --------------------------------------------------------

    share_point_site_url: str

    # --------------------------------------------------------
    # Audit Log Table
    # --------------------------------------------------------

    

    # --------------------------------------------------------
    # Notification Logic App
    #
    # These are INPUTS from the user.
    # Backend resolves the callback URL dynamically.
    # --------------------------------------------------------

    notification_logic_app_name: str
    notification_logic_app_trigger_name: str

    # --------------------------------------------------------
    # Split Vulnerabilities Azure Function
    #
    # These are INPUTS from the user.
    # Backend resolves the function URL dynamically.
    # --------------------------------------------------------

    function_app_name: str
    split_vulnerabilities_function_name: str

    # --------------------------------------------------------
    # Existing Azure API Connections
    # --------------------------------------------------------

    azure_tables_connection_name: str = "azuretables-1"
    sharepoint_connection_name: str = "sharepointonline-1"


# ============================================================
# DEPLOYMENT RESPONSE
# ============================================================

class ReportingDeploymentResponse(BaseModel):
    """
    Response returned after Reporting deployment.
    """

    success: bool
    message: str

    # --------------------------------------------------------
    # Azure infrastructure
    # --------------------------------------------------------

    subscription_id: str
    resource_group_name: str
    location: str

    # --------------------------------------------------------
    # Reporting
    # --------------------------------------------------------

    reporting_logic_app_name: str
    storage_account_name: str

    # --------------------------------------------------------
    # ARM deployment
    # --------------------------------------------------------

    deployment_name: Optional[str] = None
    provisioning_state: Optional[str] = None

    # --------------------------------------------------------
    # API connection IDs
    # --------------------------------------------------------

    table_connection_id: Optional[str] = None
    sharepoint_connection_id: Optional[str] = None

    # --------------------------------------------------------
    # Dynamically resolved URLs
    # --------------------------------------------------------

    function_urls: Optional[ReportingFunctionUrls] = None
    logic_app_urls: Optional[ReportingLogicAppUrls] = None