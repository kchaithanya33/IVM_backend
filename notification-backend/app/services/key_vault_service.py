import logging

from app.azure.resources import (
    AzureResourceService,
)

from app.azure.key_vault import (
    KeyVaultSecretManager,
)

from app.schemas.key_vault import (
    KeyVaultSetupRequest,
    KeyVaultSetupResponse,
)


logger = logging.getLogger(__name__)


class KeyVaultSetupService:

    def setup(
        self,
        request: KeyVaultSetupRequest,
    ) -> KeyVaultSetupResponse:

        logger.info(
            "=================================================="
        )

        logger.info(
            "Starting complete Key Vault setup"
        )

        logger.info(
            "=================================================="
        )

        # ====================================================
        # AZURE RESOURCE SERVICE
        # ====================================================

        azure = AzureResourceService(
            subscription_id=request.subscription_id
        )

        # ====================================================
        # 1. GET TENANT ID FROM AZ LOGIN
        # ====================================================

        tenant_id = azure.get_tenant_id()

        logger.info(
            "Tenant ID retrieved successfully."
        )

        # ====================================================
        # 2. GET CURRENT USER OBJECT ID FROM AZ LOGIN
        # ====================================================

        current_user_object_id = (
            azure.get_current_user_object_id()
        )

        logger.info(
            "Current Azure user Object ID retrieved."
        )

        # ====================================================
        # 3. RESOURCE GROUP
        # ====================================================

        azure.get_resource_group(
            request.resource_group_name
        )

        logger.info(
            "Resource Group validated."
        )

        # ====================================================
        # 4. STORAGE ACCOUNT
        # ====================================================

        azure.validate_storage_account(
            request.resource_group_name,
            request.storage_account_name,
        )

        logger.info(
            "Storage Account validated."
        )

        # ====================================================
        # 5. FUNCTION APP
        # ====================================================

        principal_id = (
            azure.get_function_app_principal_id(
                request.resource_group_name,
                request.function_app_name,
            )
        )

        logger.info(
            "Function App Principal ID retrieved."
        )

        # ====================================================
        # 6. CREATE / GET KEY VAULT
        # ====================================================

        (
            key_vault,
            key_vault_created,
        ) = azure.create_key_vault(
            resource_group_name=(
                request.resource_group_name
            ),
            key_vault_name=(
                request.key_vault_name
            ),
            location=request.location,
            tenant_id=tenant_id,
        )

        if not key_vault:

            raise RuntimeError(
                "Key Vault creation/get operation "
                "did not return a resource."
            )

        logger.info(
            "Key Vault is available."
        )

        # ====================================================
        # 7. KEY VAULT ID
        # ====================================================

        key_vault_id = (
            azure.get_key_vault_id(
                request.resource_group_name,
                request.key_vault_name,
            )
        )

        # ====================================================
        # 8. KEY VAULT URL
        # ====================================================

        key_vault_url = (
            azure.get_key_vault_url(
                request.key_vault_name
            )
        )

        # ====================================================
        # 9. CURRENT USER → SECRETS OFFICER
        # ====================================================

        (
            _user_assignment,
            user_role_assigned,
        ) = (
            azure.assign_key_vault_secrets_officer_role(
                key_vault_id=key_vault_id,
                user_object_id=current_user_object_id,
            )
        )

        logger.info(
            "Current Azure user Key Vault role configured."
        )

        # ====================================================
        # 10. FUNCTION APP → SECRETS USER
        # ====================================================

        (
            _function_assignment,
            function_app_role_assigned,
        ) = (
            azure.assign_key_vault_secrets_user_role(
                key_vault_id=key_vault_id,
                principal_id=principal_id,
            )
        )

        logger.info(
            "Function App Key Vault role configured."
        )

        # ====================================================
        # 11. FUNCTION APP → KEY VAULT URL
        # ====================================================

        azure.configure_function_app_key_vault_url(
            resource_group_name=(
                request.resource_group_name
            ),
            function_app_name=(
                request.function_app_name
            ),
            key_vault_url=key_vault_url,
        )

        function_app_key_vault_url_configured = True

        # ====================================================
        # 12. STORE QUALYS SECRETS
        # ====================================================

        logger.info(
            "Storing Qualys credentials in Key Vault..."
        )

        secret_manager = (
            KeyVaultSecretManager(
                key_vault_url=key_vault_url,
                credential=azure.credential,
            )
        )

        secret_manager.store_qualys_secrets(
            username=request.qualys_username,
            password=(
                request.qualys_password.get_secret_value()
            ),
            base_url=request.qualys_base_url,
        )

        secrets_stored = True

        logger.info(
            "Qualys secrets stored successfully."
        )

        # ====================================================
        # 13. COMPLETE
        # ====================================================

        logger.info(
            "=================================================="
        )

        logger.info(
            "KEY VAULT SETUP COMPLETED"
        )

        logger.info(
            "=================================================="
        )

        return KeyVaultSetupResponse(

            status="success",

            subscription_id=(
                request.subscription_id
            ),

            resource_group_name=(
                request.resource_group_name
            ),

            location=request.location,

            function_app_name=(
                request.function_app_name
            ),

            storage_account_name=(
                request.storage_account_name
            ),

            key_vault_name=(
                request.key_vault_name
            ),

            key_vault_url=key_vault_url,

            tenant_id=tenant_id,

            principal_id=principal_id,

            current_user_object_id=(
                current_user_object_id
            ),

            managed_identity_enabled=True,

            key_vault_created=(
                key_vault_created
            ),

            user_role_assigned=(
                user_role_assigned
            ),

            function_app_role_assigned=(
                function_app_role_assigned
            ),

            function_app_key_vault_url_configured=(
                function_app_key_vault_url_configured
            ),

            secrets_stored=secrets_stored,

            secrets=[
                "QualysUsername",
                "QualysPassword",
                "QualysBaseUrl",
            ],
        )