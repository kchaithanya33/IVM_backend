
from pydantic import BaseModel, Field


class DeploymentRequest(BaseModel):

    # ========================================================
    # AZURE SUBSCRIPTION
    # ========================================================

    subscription_id: str = Field(
        ...,
        description="Azure Subscription ID"
    )

    # ========================================================
    # RESOURCE GROUP
    # ========================================================

    resource_group_name: str = Field(
        ...,
        min_length=1,
        description="Resource Group name"
    )

    resource_group_location: str = Field(
        ...,
        min_length=1,
        description="Azure location for Resource Group"
    )

    # ========================================================
    # STORAGE ACCOUNT
    # ========================================================

    storage_account_name: str = Field(
        ...,
        min_length=3,
        max_length=24,
        description="Azure Storage Account name"
    )

    storage_account_location: str = Field(
        ...,
        min_length=1,
        description="Azure location for Storage Account"
    )

    # ========================================================
    # FUNCTION APP
    # ========================================================

    function_app_name: str = Field(
        ...,
        min_length=1,
        description="Azure Function App name"
    )
