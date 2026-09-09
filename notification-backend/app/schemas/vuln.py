from typing import Dict, Optional

from pydantic import BaseModel, Field


class VulnLogicAppUrls(BaseModel):
    vuln01_5_logic_app_url: str
    notification_logic_app_url: str

    # ------------------------------------------------------------
    # VULN 1.55 URLS
    # ------------------------------------------------------------
    completion_logic_app_url: Optional[str] = None
    vuln_scan_chg_approval_callback_url: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 03 URL
    # ------------------------------------------------------------
    vuln03_callback_url: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 05 URL
    # ------------------------------------------------------------
    callback_uri_05: Optional[str] = None


class VulnFunctionUrls(BaseModel):
    config_service_url: str
    get_next_business_day_url: str
    qualys_integration_url: str
    qualys_asset_group_creation_function_url: str
    business_days_service_url: str

    # ------------------------------------------------------------
    # VULN 03 URLS
    # ------------------------------------------------------------
    excel_diageo_ip_url: Optional[str] = None
    asset_group_batch_processor_url: Optional[str] = None
    excel_mey_diageo_ip_url: Optional[str] = None
    qualys_asset_grouping_url: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 05 URL
    # ------------------------------------------------------------
    qualys_scan_function_url: Optional[str] = None


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
        - httpEndpointUrl from LA-VulnScan-01.5/manual

      Vuln 1.55:
        - completionLogicAppUrl
        - vulnScanChgApprovalCallbackUrl

      Vuln 03:
        - excelDiageoIpUrl
        - assetGroupBatchProcessorUrl
        - excelMeyDiageoIpUrl
        - qualysAssetGroupingUrl
        - vuln03CallbackUrl

      Vuln 02:
        - vulnScanAssetGroupManagerUrl is resolved from Vuln 03
          HTTP callback URL and passed during Vuln 02 deployment.

      MeyDiageo 03.5:
        - meyDiageoLogicAppName is provided by the user.
        - qualysIntegrationUrl is reused from the already resolved
          Qualys Integration Function URL.
        - vulnScanProfile3.5 uses the ARM default value.
        - scannerId3.5 uses the ARM default value.

      Vuln Auth Failure Detection:
        - qualysLaunchReportUrl
        - qualysCheckReportUrl
        - qualysDownloadReportUrl
        - authFailureAnalysisUrl

      Vuln 05:
        - qualysScanFunctionUrl is resolved from the supplied
          Function App name + Function name.
        - callbackUri05 is resolved from the Auth Failure Detection
          Logic App (06) manual HTTP trigger after 06 deployment.

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
    # SECOND LOGIC APP - VULN 01
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
    # VULN 03 LOGIC APP
    # ------------------------------------------------------------

    vuln03_logic_app_name: str = Field(
        default="LA-VulnScan-03",
        description="Vulnerability Scan 03 Logic App name.",
    )

    vuln03_logic_app_trigger_name: str = Field(
        default="manual",
        description="HTTP trigger of the Vuln-03 Logic App.",
    )

    # ------------------------------------------------------------
    # VULN 02 - CHANGE APPROVAL LOGIC APP
    # ------------------------------------------------------------

    vuln02_logic_app_name: str = Field(
        default="LA-VulnScan-02",
        description="Vulnerability Scan 02 / Change Approval Logic App name.",
    )

    # ------------------------------------------------------------
    # MEYDIAGEO 03.5 LOGIC APP
    # ------------------------------------------------------------

    mey_diageo_logic_app_name: str = Field(
        default="LA-VulnScan-MeyDiageo-03.5",
        description="MeyDiageo Vulnerability Scan 03.5 Logic App name.",
    )

    # ------------------------------------------------------------
    # VULN AUTH FAILURE DETECTION LOGIC APP
    # ------------------------------------------------------------

    vuln_scan_auth_failure_logic_app_name: str = Field(
        default="LA-VulnScan-AuthFailureDetection",
        description="Vulnerability Scan Authentication Failure Detection Logic App name.",
    )

    # ------------------------------------------------------------
    # VULN 05 LOGIC APP
    # ------------------------------------------------------------

    vuln05_logic_app_name: str = Field(
        default="LA-VulnScan-05",
        description="Vulnerability Scan 05 Logic App name.",
    )

    # ------------------------------------------------------------
    # VULN 1.55 - COMPLETION LOGIC APP URL RESOLUTION
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
    # VULN 03 - FUNCTION APP - DIAGEO IP EXCEL
    # ------------------------------------------------------------

    excel_diageo_ip_function_app_name: str = Field(
        default="",
        description="Function App containing the Diageo IP Excel extraction function.",
    )

    excel_diageo_ip_function_name: str = Field(
        default="",
        description="Function name used to obtain excelDiageoIpUrl.",
    )

    # ------------------------------------------------------------
    # VULN 03 - FUNCTION APP - ASSET GROUP BATCH PROCESSOR
    # ------------------------------------------------------------

    asset_group_batch_processor_function_app_name: str = Field(
        default="",
        description="Function App containing the Asset Group Batch Processor function.",
    )

    asset_group_batch_processor_function_name: str = Field(
        default="",
        description="Function name used to obtain assetGroupBatchProcessorUrl.",
    )

    # ------------------------------------------------------------
    # VULN 03 - FUNCTION APP - MEYDIAGEO IP EXCEL
    # ------------------------------------------------------------

    excel_mey_diageo_ip_function_app_name: str = Field(
        default="",
        description="Function App containing the MeyDiageo IP Excel extraction function.",
    )

    excel_mey_diageo_ip_function_name: str = Field(
        default="",
        description="Function name used to obtain excelMeyDiageoIpUrl.",
    )

    # ------------------------------------------------------------
    # VULN 03 - FUNCTION APP - QUALYS ASSET GROUPING
    # ------------------------------------------------------------

    qualys_asset_grouping_function_app_name: str = Field(
        default="",
        description="Function App containing the Qualys asset grouping function.",
    )

    qualys_asset_grouping_function_name: str = Field(
        default="",
        description="Function name used to obtain qualysAssetGroupingUrl.",
    )

    # ------------------------------------------------------------
    # VULN AUTH FAILURE DETECTION - FUNCTION APP -
    # QUALYS LAUNCH REPORT
    # ------------------------------------------------------------

    qualys_launch_report_function_app_name: str = Field(
        default="",
        description="Function App containing the Qualys launch report function.",
    )

    qualys_launch_report_function_name: str = Field(
        default="",
        description="Function name used to obtain qualysLaunchReportUrl.",
    )

    # ------------------------------------------------------------
    # VULN AUTH FAILURE DETECTION - FUNCTION APP -
    # QUALYS CHECK REPORT
    # ------------------------------------------------------------

    qualys_check_report_function_app_name: str = Field(
        default="",
        description="Function App containing the Qualys check report function.",
    )

    qualys_check_report_function_name: str = Field(
        default="",
        description="Function name used to obtain qualysCheckReportUrl.",
    )

    # ------------------------------------------------------------
    # VULN AUTH FAILURE DETECTION - FUNCTION APP -
    # QUALYS DOWNLOAD REPORT
    # ------------------------------------------------------------

    qualys_download_report_function_app_name: str = Field(
        default="",
        description="Function App containing the Qualys download report function.",
    )

    qualys_download_report_function_name: str = Field(
        default="",
        description="Function name used to obtain qualysDownloadReportUrl.",
    )

    # ------------------------------------------------------------
    # VULN AUTH FAILURE DETECTION - FUNCTION APP -
    # AUTH FAILURE ANALYSIS
    # ------------------------------------------------------------

    auth_failure_analysis_function_app_name: str = Field(
        default="",
        description="Function App containing the authentication failure analysis function.",
    )

    auth_failure_analysis_function_name: str = Field(
        default="",
        description="Function name used to obtain authFailureAnalysisUrl.",
    )

    # ------------------------------------------------------------
    # VULN 05 - FUNCTION APP - QUALYS SCAN
    # ------------------------------------------------------------

    qualys_scan_function_app_name: str = Field(
        default="",
        description="Function App containing the Qualys scan function.",
    )

    qualys_scan_function_name: str = Field(
        default="",
        description="Function name used to obtain qualysScanFunctionUrl.",
    )

    # ------------------------------------------------------------
    # VULN 03 - SHAREPOINT SITE
    # ------------------------------------------------------------

    sharepoint_site_url: str = Field(
        ...,
        description="SharePoint site URL containing the CMDB report.",
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

    # ------------------------------------------------------------
    # LOGIC APP NAMES
    # ------------------------------------------------------------

    vuln15_logic_app_name: str
    vuln01_logic_app_name: str
    vuln02_logic_app_name: Optional[str] = None
    vuln04_logic_app_name: str
    vuln155_logic_app_name: Optional[str] = None
    vuln03_logic_app_name: Optional[str] = None

    # ------------------------------------------------------------
    # MEYDIAGEO 03.5 LOGIC APP
    # ------------------------------------------------------------

    mey_diageo_logic_app_name: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 05 LOGIC APP
    # ------------------------------------------------------------

    vuln05_logic_app_name: Optional[str] = None

    notification_logic_app_name: str

    storage_account_name: str

    # ------------------------------------------------------------
    # DEPLOYMENT NAMES
    # ------------------------------------------------------------

    vuln15_deployment_name: Optional[str] = None
    vuln01_deployment_name: Optional[str] = None
    vuln02_deployment_name: Optional[str] = None
    vuln04_deployment_name: Optional[str] = None
    vuln155_deployment_name: Optional[str] = None
    vuln03_deployment_name: Optional[str] = None

    # ------------------------------------------------------------
    # MEYDIAGEO 03.5 DEPLOYMENT
    # ------------------------------------------------------------

    mey_diageo_deployment_name: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 05 DEPLOYMENT
    # ------------------------------------------------------------

    vuln05_deployment_name: Optional[str] = None

    # ------------------------------------------------------------
    # PROVISIONING STATES
    # ------------------------------------------------------------

    vuln15_provisioning_state: Optional[str] = None
    vuln01_provisioning_state: Optional[str] = None
    vuln02_provisioning_state: Optional[str] = None
    vuln04_provisioning_state: Optional[str] = None
    vuln155_provisioning_state: Optional[str] = None
    vuln03_provisioning_state: Optional[str] = None

    # ------------------------------------------------------------
    # MEYDIAGEO 03.5 PROVISIONING STATE
    # ------------------------------------------------------------

    mey_diageo_provisioning_state: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 05 PROVISIONING STATE
    # ------------------------------------------------------------

    vuln05_provisioning_state: Optional[str] = None

    # ------------------------------------------------------------
    # API CONNECTION IDS
    # ------------------------------------------------------------

    table_connection_id: Optional[str] = None
    queue_connection_id: Optional[str] = None
    sharepoint_connection_id: Optional[str] = None

    # ------------------------------------------------------------
    # RESOLVED FUNCTION URLS
    # ------------------------------------------------------------

    function_urls: Optional[VulnFunctionUrls] = None

    # ------------------------------------------------------------
    # RESOLVED LOGIC APP URLS
    # ------------------------------------------------------------

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
    # VULN 03 RESOLVED URLS
    # ------------------------------------------------------------

    excel_diageo_ip_url: Optional[str] = None
    asset_group_batch_processor_url: Optional[str] = None
    excel_mey_diageo_ip_url: Optional[str] = None
    qualys_asset_grouping_url: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 03 CALLBACK URL
    # This is passed to Vuln 02 as:
    # vulnScanAssetGroupManagerUrl
    # ------------------------------------------------------------

    vuln03_callback_url: Optional[str] = None

    # ------------------------------------------------------------
    # VULN 05 RESOLVED URL
    # ------------------------------------------------------------

    qualys_scan_function_url: Optional[str] = None
    callback_uri_05: Optional[str] = None

    # ------------------------------------------------------------
    # ARM CONNECTION OBJECT
    # ------------------------------------------------------------

    arm_connections: Optional[Dict[str, Dict[str, str]]] = None