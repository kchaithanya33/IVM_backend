from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ScopingDeploymentRequest(BaseModel):
    """
    Request model for Scoping Logic App deployment.
    """

    subscription_id: str = Field(..., min_length=1)
    resource_group_name: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)

    storage_account_name: str = Field(..., min_length=3)

    sharepoint_url: str = Field(..., min_length=1)

    logic_app_name: str = Field(..., min_length=1)
    scoping01_logic_app_name: str = Field(..., min_length=1)
    scoping02_logic_app_name: str = Field(..., min_length=1)

    callback_secret_key: str = Field(..., min_length=1)

    table_connection_name: str = Field(..., min_length=1)
    queue_connection_name: str = Field(..., min_length=1)
    sharepoint_connection_name: str = Field(..., min_length=1)

    notification_log_table_name: str = Field(..., min_length=1)
    notification_status_table_name: str = Field(..., min_length=1)

    queue_name: str = Field(..., min_length=1)
    authscan_queue_name: str = Field(..., min_length=1)

    completion_logic_app_url: str = Field(..., min_length=1)


class ScopingDeploymentResponse(BaseModel):
    success: bool
    message: str

    subscription_id: Optional[str] = None
    resource_group_name: Optional[str] = None
    location: Optional[str] = None

    logic_app_name: Optional[str] = None
    scoping01_logic_app_name: Optional[str] = None
    scoping02_logic_app_name: Optional[str] = None

    storage_account_name: Optional[str] = None

    table_connection_id: Optional[str] = None
    queue_connection_id: Optional[str] = None
    sharepoint_connection_id: Optional[str] = None

    deployment_name: Optional[str] = None
    provisioning_state: Optional[str] = None