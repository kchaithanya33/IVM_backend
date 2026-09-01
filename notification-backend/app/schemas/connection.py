
from typing import Any

from pydantic import BaseModel, Field


class ConnectionRequest(BaseModel):
    subscription_id: str = Field(
        ...,
        description="Azure subscription ID",
    )

    resource_group_name: str = Field(
        ...,
        description="Azure resource group containing the connections",
    )

    storage_account_name: str = Field(
        ...,
        description="Storage account used by Azure Tables and Azure Queues connections",
    )

    location: str = Field(
        ...,
        description="Azure resource location",
    )


class ConnectionStatus(BaseModel):
    name: str
    created: bool
    authenticated: bool
    status: str
    statuses: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ConnectionResponse(BaseModel):
    status: str
    message: str
    deployment_name: str
    resource_group_name: str
    provisioning_state: str | None = None
    connections: list[ConnectionStatus]
    unauthorized_connections: list[str] = Field(default_factory=list)
