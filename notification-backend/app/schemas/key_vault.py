from typing import List

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
)


# ============================================================
# KEY VAULT SETUP REQUEST
# ============================================================

class KeyVaultSetupRequest(BaseModel):

    subscription_id: str = Field(
        ...,
        description="Azure Subscription ID",
    )

    resource_group_name: str = Field(
        ...,
        description="Azure Resource Group name",
    )

    location: str = Field(
        ...,
        description="Azure region for Key Vault",
    )

    function_app_name: str = Field(
        ...,
        description="Azure Function App name",
    )

    storage_account_name: str = Field(
        ...,
        description="Azure Storage Account name",
    )

    key_vault_name: str = Field(
        ...,
        description="Azure Key Vault name",
    )

    # ========================================================
    # QUALYS CREDENTIALS
    # ========================================================

    qualys_username: str = Field(
        ...,
        min_length=1,
        description="Qualys username",
    )

    qualys_password: SecretStr = Field(
        ...,
        min_length=1,
        description="Qualys password",
    )

    qualys_base_url: str = Field(
        ...,
        min_length=1,
        description="Qualys API base URL",
    )


# ============================================================
# KEY VAULT SETUP RESPONSE
# ============================================================

class KeyVaultSetupResponse(BaseModel):

    status: str

    subscription_id: str

    resource_group_name: str

    location: str

    function_app_name: str

    storage_account_name: str

    key_vault_name: str

    key_vault_url: str

    tenant_id: str

    principal_id: str

    current_user_object_id: str

    managed_identity_enabled: bool

    key_vault_created: bool

    user_role_assigned: bool

    function_app_role_assigned: bool

    function_app_key_vault_url_configured: bool

    secrets_stored: bool

    secrets: List[str]