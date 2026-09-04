from typing import Dict, Optional

from pydantic import BaseModel, Field


class VulnLogicAppUrls(BaseModel):
    vuln01_5_logic_app_url: str
    notification_logic_app_url: str
    callback_logic_app_url: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 1.55 URLS
    # ------------------------------------------------------------
    completion_logic_app_url: Optional[str] = None
    vuln_scan_chg_approval_callback_url: Optional[str] = None


class VulnFunctionUrls(BaseModel):
    config_service_url: str
    get_next_business_day_url: str
    qualys_integration_url: str
    qualys_asset_group_creation_function_url: str
    business_days_service_url: str


class VulnDeploymentRequest(BaseModel):
    """
    User-provided inputs for Vulnerability Scan Logic App deployment.

    The backend resolves:

      Function App + Function:
        - configServiceUrl
        - getNextBusinessDayUrl
        - qualysIntegrationUrl
        - qualysAssetGroupCreationFunctionUrl
        - businessDaysServiceUrl

      Logic App + HTTP Trigger:
        - notificationLogicAppUrl
        - callbackUri
        - httpEndpointUrl from LA-VulnScan-01.5/manual

      Vuln 1.55:
        - completionLogicAppUrl is resolved from:
            completion_logic_app_name
            completion_http_action_name

        - vulnScanChgApprovalCallbackUrl is resolved from:
            vuln_scan_chg_approval_logic_app_name
            vuln_scan_chg_approval_http_action_name

      Azure API connection IDs:
        - table connection
        - queue connection
        - SharePoint connection
    """

    # ------------------------------------------------------------
    # AZURE DEPLOYMENT
    # ------------------------------------------------------------

    subscription_id: str = Field(
        ...,
        description="Azure subscription ID",
    )

    resource_group_name: str = Field(
        ...,
        description="Existing Azure resource group name",
    )

    location: str = Field(
        ...,
        description="Azure deployment location. Used for the Logic Apps.",
    )

    storage_account_name: str = Field(
        ...,
        description="Storage account used by the Vulnerability Scan Logic Apps.",
    )

    # ------------------------------------------------------------
    # FIRST LOGIC APP - VULN 1.5
    # ------------------------------------------------------------

    vuln15_logic_app_name: str = Field(
        default="LA-VulnScan-01.5",
        description="Vulnerability Scan 01.5 Logic App name.",
    )

    vuln15_logic_app_trigger_name: str = Field(
        default="manual",
        description="HTTP trigger of LA-VulnScan-01.5.",
    )

    # ------------------------------------------------------------
    # SECOND LOGIC APP
    # ------------------------------------------------------------

    vuln01_logic_app_name: str = Field(
        default="LA-VulnScan-01",
        description="Vulnerability Scan 01 Logic App name.",
    )

    # ------------------------------------------------------------
    # VULN 04 LOGIC APP
    # ------------------------------------------------------------

    vuln04_logic_app_name: str = Field(
        default="LA-VulnScan-04",
        description="Vulnerability Scan 04 Logic App name.",
    )

    # ------------------------------------------------------------
    # VULN 1.55 LOGIC APP
    # ------------------------------------------------------------

    vuln155_logic_app_name: str = Field(
        default="LA-VulnScan-01.55",
        description="Vulnerability Scan 01.55 Logic App name.",
    )

    # ------------------------------------------------------------
    # VULN 1.55 - COMPLETION LOGIC APP URL RESOLUTION
    # ------------------------------------------------------------
    #
    # These two values are used by the backend to find the
    # existing Logic App HTTP action and resolve completionLogicAppUrl.
    #
    # They are NOT the URL itself.
    # ------------------------------------------------------------

    completion_logic_app_name: str = Field(
        default="",
        description=(
            "Existing Logic App name used to resolve "
            "completionLogicAppUrl."
        ),
    )

    completion_http_action_name: str = Field(
        default="",
        description=(
            "HTTP action/trigger name in the completion Logic App "
            "used to resolve completionLogicAppUrl."
        ),
    )

    # ------------------------------------------------------------
    # VULN 1.55 - CHANGE APPROVAL CALLBACK URL RESOLUTION
    # ------------------------------------------------------------
    #
    # These two values are used by the backend to find the
    # existing Logic App HTTP action and resolve
    # vulnScanChgApprovalCallbackUrl.
    #
    # They are NOT the URL itself.
    # ------------------------------------------------------------

    vuln_scan_chg_approval_logic_app_name: str = Field(
        default="",
        description=(
            "Existing Logic App name used to resolve "
            "vulnScanChgApprovalCallbackUrl."
        ),
    )

    vuln_scan_chg_approval_http_action_name: str = Field(
        default="",
        description=(
            "HTTP action/trigger name in the Change Approval Logic App "
            "used to resolve vulnScanChgApprovalCallbackUrl."
        ),
    )

    # ------------------------------------------------------------
    # FUNCTION APP - CONFIG SERVICE
    # ------------------------------------------------------------

    config_service_function_app_name: str = Field(
        default="function-app-chai",
        description="Function App containing the configuration function.",
    )

    config_service_function_name: str = Field(
        default="GetPartitionConfigs",
        description="Function name used to obtain configServiceUrl.",
    )

    # ------------------------------------------------------------
    # FUNCTION APP - GET NEXT BUSINESS DAY
    # ------------------------------------------------------------

    get_next_business_day_function_app_name: str = Field(
        default="function-app-chai",
        description="Function App containing the Get Next Business Day function.",
    )

    get_next_business_day_function_name: str = Field(
        default="GetNextBusinessDay",
        description="Function name used to obtain getNextBusinessDayUrl.",
    )

    # ------------------------------------------------------------
    # FUNCTION APP - QUALYS INTEGRATION
    # ------------------------------------------------------------

    qualys_integration_function_app_name: str = Field(
        default="function-app-chai",
        description="Function App containing the Qualys integration function.",
    )

    qualys_integration_function_name: str = Field(
        default="QualysAuthScan",
        description="Function name used to obtain qualysIntegrationUrl.",
    )

    # ------------------------------------------------------------
    # FUNCTION APP - QUALYS ASSET GROUP CREATION
    # ------------------------------------------------------------

    qualys_asset_group_creation_function_app_name: str = Field(
        default="function-app-chai",
        description="Function App containing the Qualys asset group creation function.",
    )

    qualys_asset_group_creation_function_name: str = Field(
        default="QualysAssetGrouping",
        description="Function name used to obtain qualysAssetGroupCreationFunctionUrl.",
    )

    # ------------------------------------------------------------
    # FUNCTION APP - BUSINESS DAYS SERVICE
    # ------------------------------------------------------------

    business_days_service_function_app_name: str = Field(
        default="function-app-chai",
        description="Function App containing the Business Days service function.",
    )

    business_days_service_function_name: str = Field(
        default="IsBusinessDayAndHour",
        description="Function name used to obtain businessDaysServiceUrl.",
    )

    # ------------------------------------------------------------
    # NOTIFICATION LOGIC APP
    # ------------------------------------------------------------

    notification_logic_app_name: str = Field(
        default="notification-logic-chai",
        description="Existing Notification Logic App name.",
    )

    notification_logic_app_trigger_name: str = Field(
        default="When_a_HTTP_request_is_received",
        description="HTTP trigger name in the Notification Logic App.",
    )

    # ------------------------------------------------------------
    # CALLBACK LOGIC APP
    # ------------------------------------------------------------

    callback_logic_app_name: str = Field(
        default="notification-logic-chai",
        description="Logic App whose HTTP trigger will receive the vulnerability scan callback.",
    )

    callback_logic_app_trigger_name: str = Field(
        default="When_a_HTTP_request_is_received",
        description="HTTP trigger name in the callback Logic App.",
    )

    # ------------------------------------------------------------
    # API CONNECTION NAMES
    # ------------------------------------------------------------

    table_connection_name: str = Field(
        default="azuretables-1",
        description="Azure Tables API connection resource name.",
    )

    queue_connection_name: str = Field(
        default="azurequeues-1",
        description="Azure Queues API connection resource name.",
    )

    sharepoint_connection_name: str = Field(
        default="sharepointonline-1",
        description="SharePoint API connection resource name.",
    )


class VulnDeploymentResponse(BaseModel):
    success: bool
    message: str

    subscription_id: str
    resource_group_name: str
    location: str

    vuln15_logic_app_name: str
    vuln01_logic_app_name: str
    vuln04_logic_app_name: str

    # ------------------------------------------------------------
    # VULN 1.55
    # ------------------------------------------------------------

    vuln155_logic_app_name: Optional[str] = None

    notification_logic_app_name: str

    callback_logic_app_name: Optional[str] = None

    storage_account_name: str

    vuln15_deployment_name: Optional[str] = None
    vuln01_deployment_name: Optional[str] = None
    vuln04_deployment_name: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 1.55 DEPLOYMENT
    # ------------------------------------------------------------

    vuln155_deployment_name: Optional[str] = None

    vuln15_provisioning_state: Optional[str] = None
    vuln01_provisioning_state: Optional[str] = None
    vuln04_provisioning_state: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 1.55 PROVISIONING STATE
    # ------------------------------------------------------------

    vuln155_provisioning_state: Optional[str] = None

    table_connection_id: Optional[str] = None
    queue_connection_id: Optional[str] = None
    sharepoint_connection_id: Optional[str] = None

    function_urls: Optional[VulnFunctionUrls] = None
    logic_app_urls: Optional[VulnLogicAppUrls] = None

    # ------------------------------------------------------------
    # EXISTING RESOLVED URLS
    # ------------------------------------------------------------

    http_endpoint_url: Optional[str] = None
    notification_logic_app_url: Optional[str] = None
    callback_uri: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 1.55 RESOLVED URLS
    # ------------------------------------------------------------

    completion_logic_app_url: Optional[str] = None
    vuln_scan_chg_approval_callback_url: Optional[str] = None

    # ------------------------------------------------------------
    # ARM CONNECTION OBJECT
    # ------------------------------------------------------------

    arm_connections: Optional[Dict[str, Dict[str, str]]] = None