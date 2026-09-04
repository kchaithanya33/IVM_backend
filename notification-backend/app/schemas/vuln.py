from typing import Dict, Optional

from pydantic import BaseModel, Field


class VulnLogicAppUrls(BaseModel):
    vuln01_5_logic_app_url: str
    notification_logic_app_url: str


class VulnFunctionUrls(BaseModel):
    config_service_url: str


class VulnDeploymentRequest(BaseModel):
    """
    User-provided inputs for Vulnerability Scan Logic App deployment.

    The backend resolves:
      - configServiceUrl from the Function App/function
      - notificationLogicAppUrl from the Notification Logic App trigger
      - httpEndpointUrl from LA-VulnScan-01.5/manual
      - Azure API connection IDs from connection names
    """

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
        description="Azure deployment location. Used for both Logic Apps.",
    )

    storage_account_name: str = Field(
        ...,
        description="Storage account used by the Vulnerability Scan Logic Apps.",
    )

    # ------------------------------------------------------------
    # FIRST LOGIC APP
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
    # FUNCTION APP
    # ------------------------------------------------------------

    function_app_name: str = Field(
        ...,
        description="Existing Function App containing the configuration function.",
    )

    config_service_function_name: str = Field(
        ...,
        description="Function name used to obtain configServiceUrl.",
    )

    # ------------------------------------------------------------
    # NOTIFICATION LOGIC APP
    # ------------------------------------------------------------

    notification_logic_app_name: str = Field(
        ...,
        description="Existing Notification Logic App name.",
    )

    notification_logic_app_trigger_name: str = Field(
        ...,
        description="Trigger name in the Notification Logic App.",
    )

    # ------------------------------------------------------------
    # API CONNECTION NAMES
    # ------------------------------------------------------------

    table_connection_name: str = Field(
        ...,
        description="Azure Tables API connection resource name.",
    )

    queue_connection_name: str = Field(
        ...,
        description="Azure Queues API connection resource name.",
    )

    sharepoint_connection_name: str = Field(
        ...,
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

    notification_logic_app_name: str

    storage_account_name: str

    vuln15_deployment_name: Optional[str] = None
    vuln01_deployment_name: Optional[str] = None

    vuln15_provisioning_state: Optional[str] = None
    vuln01_provisioning_state: Optional[str] = None

    table_connection_id: Optional[str] = None
    queue_connection_id: Optional[str] = None
    sharepoint_connection_id: Optional[str] = None

    function_urls: Optional[VulnFunctionUrls] = None
    logic_app_urls: Optional[VulnLogicAppUrls] = None

    # Useful for debugging/confirmation from frontend.
    http_endpoint_url: Optional[str] = None
    notification_logic_app_url: Optional[str] = None

    # ARM connection object actually supplied to deployment.
    arm_connections: Optional[Dict[str, Dict[str, str]]] = None