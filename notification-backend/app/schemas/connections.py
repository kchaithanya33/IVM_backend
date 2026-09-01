
from typing import List, Optional

from pydantic import BaseModel, Field


# ============================================================
# REQUEST
# ============================================================

class ConnectionSetupRequest(BaseModel):

    subscription_id: str = Field(
        ...,
        min_length=1,
    )

    resource_group_name: str = Field(
        ...,
        min_length=1,
    )

    location: str = Field(
        ...,
        min_length=1,
    )


# ============================================================
# INDIVIDUAL CONNECTION STATUS
# ============================================================

class ConnectionStatus(BaseModel):

    name: str

    connector: str

    authentication_type: str

    exists: bool

    authenticated: bool

    connection_state: Optional[str] = None

    status: Optional[str] = None

    authentication_required: bool = False

    message: str


# ============================================================
# RESPONSE
# ============================================================

class ConnectionSetupResponse(BaseModel):

    status: str

    message: str

    subscription_id: str

    resource_group_name: str

    connections: List[ConnectionStatus]

    pending_connection: Optional[str] = None

    authentication_required: bool = False

    all_connections_ready: bool = False
