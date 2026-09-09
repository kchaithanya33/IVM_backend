from typing import Optional

from pydantic import BaseModel


# ============================================================
# FUNCTION URLS
# ============================================================

class ReportingFunctionUrls(BaseModel):
    """
    Dynamically resolved Azure Function URLs required
    by Reporting 03 and Reporting 04.
    """

    split_vulnerabilities_function_url: str
    after_scoping_triaging_url: Optional[str] = None
    triaging_validator_url: Optional[str] = None


# ============================================================
# LOGIC APP URLS
# ============================================================

class ReportingLogicAppUrls(BaseModel):
    """
    Dynamically resolved Logic App URLs.
    """

    # Notification Logic App callback URL.
    notification_service_url: str

    # Completion Logic App callback URL without query string.
    completion_url: Optional[str] = None

    # Raw 'sig' value from the completion Logic App callback URL.
    completion_sas_token: Optional[str] = None


# ============================================================
# DEPLOYMENT REQUEST
# ============================================================

class ReportingDeploymentRequest(BaseModel):
    """
    Request model for Reporting deployment.

    Deployment order:

        1. Reporting 04
        2. Resolve Reporting 04 callback URL
        3. Resolve Completion Logic App callback URL
        4. Resolve Function URLs
        5. Reporting 03

    Reporting 04 callback URL becomes callbackUrl
    for Reporting 03.
    """

    # --------------------------------------------------------
    # Azure infrastructure
    # --------------------------------------------------------

    subscription_id: str
    resource_group_name: str
    location: str

    # --------------------------------------------------------
    # Reporting Logic Apps
    # --------------------------------------------------------

    # Reporting 04 - deployed first.
    reporting_logic_app_name: str = "LA-reporting-04"

    # Reporting 03 - deployed second.
    reporting_03_logic_app_name: str = "LA-reporting-03"

    # --------------------------------------------------------
    # Storage Account
    # --------------------------------------------------------

    storage_account_name: str

    # --------------------------------------------------------
    # SharePoint
    # --------------------------------------------------------

    share_point_site_url: str

    # --------------------------------------------------------
    # Notification Logic App
    # --------------------------------------------------------

    # User provides the Logic App and trigger.
    # Backend dynamically resolves its callback URL.
    notification_logic_app_name: str
    notification_logic_app_trigger_name: str

    # --------------------------------------------------------
    # Completion Logic App
    # --------------------------------------------------------

    # User provides the Logic App and trigger.
    #
    # Backend calls Azure listCallbackUrl and extracts:
    #
    #   completion_url
    #   completion_sas_token
    #
    # The /complete/{taskId}/{workflowName}/{token}
    # path is constructed by Reporting 03 at runtime.
    # --------------------------------------------------------

    completion_logic_app_name: str
    completion_logic_app_trigger_name: str

    # --------------------------------------------------------
    # Split Vulnerabilities Azure Function
    # --------------------------------------------------------

    function_app_name: str
    split_vulnerabilities_function_name: str

    # --------------------------------------------------------
    # After Scoping Triaging Azure Function
    # --------------------------------------------------------

    after_scoping_triaging_function_app_name: Optional[str] = None
    after_scoping_triaging_function_name: Optional[str] = None

    # --------------------------------------------------------
    # Triaging Validator Azure Function
    # --------------------------------------------------------

    triaging_validator_function_app_name: Optional[str] = None
    triaging_validator_function_name: Optional[str] = None

    # --------------------------------------------------------
    # Callback Secret
    # --------------------------------------------------------

    # Used by Reporting 03 to generate the completion token.
    callback_secret_key: str

    # --------------------------------------------------------
    # Azure API Connections
    # --------------------------------------------------------

    # Azure Tables
    azure_tables_connection_name: str = "azuretables-1"

    # SharePoint Online
    sharepoint_connection_name: str = "sharepointonline-1"

    # Azure Queue
    azure_queue_connection_name: str = "azurequeues-1"


# ============================================================
# DEPLOYMENT RESPONSE
# ============================================================

class ReportingDeploymentResponse(BaseModel):
    """
    Response returned after Reporting 04 and Reporting 03
    deployment.
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
    # Reporting Logic Apps
    # --------------------------------------------------------

    # Reporting 04
    reporting_logic_app_name: str

    # Reporting 03
    reporting_03_logic_app_name: Optional[str] = None

    # --------------------------------------------------------
    # Storage
    # --------------------------------------------------------

    storage_account_name: str

    # --------------------------------------------------------
    # Reporting 04 deployment
    # --------------------------------------------------------

    deployment_name: Optional[str] = None
    provisioning_state: Optional[str] = None

    # --------------------------------------------------------
    # Reporting 03 deployment
    # --------------------------------------------------------

    reporting_03_deployment_name: Optional[str] = None
    reporting_03_provisioning_state: Optional[str] = None

    # --------------------------------------------------------
    # API connection IDs
    # --------------------------------------------------------

    table_connection_id: Optional[str] = None

    sharepoint_connection_id: Optional[str] = None

    # Azure Queue connection ID
    queue_connection_id: Optional[str] = None

    # --------------------------------------------------------
    # Reporting 04 callback URL
    #
    # This is dynamically resolved after Reporting 04
    # deployment and passed to Reporting 03 as:
    #
    #     callbackUrl
    # --------------------------------------------------------

    callback_url: Optional[str] = None

    # --------------------------------------------------------
    # Dynamically resolved Function URLs
    # --------------------------------------------------------

    function_urls: Optional[ReportingFunctionUrls] = None

    # --------------------------------------------------------
    # Dynamically resolved Logic App URLs
    # --------------------------------------------------------

    logic_app_urls: Optional[ReportingLogicAppUrls] = None

    # --------------------------------------------------------
    # Completion callback values
    # --------------------------------------------------------

    # Base callback URL without query string.
    completion_url: Optional[str] = None

    # Raw sig value extracted from listCallbackUrl response.
    completion_sas_token: Optional[str] = None