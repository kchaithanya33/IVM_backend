from app.azure.tables import (
    set_subscription,
    create_resource_group,
    create_storage_account,
    get_storage_account_key,
    create_tables,
    create_queues,
)

from app.azure.function_app import (
    create_app_service_plan,
    create_function_app,
)

from app.azure.resources import (
    AzureResourceService,
)


class NotificationDeployment:

    def __init__(
        self,
        subscription_id: str,
        resource_group_name: str,
        resource_group_location: str,
        storage_account_name: str,
        storage_account_location: str,
        function_app_name: str,
        table_names: list[str],
        queue_names: list[str],
    ):

        self.subscription_id = (
            subscription_id
        )

        self.resource_group_name = (
            resource_group_name
        )

        self.resource_group_location = (
            resource_group_location
        )

        self.storage_account_name = (
            storage_account_name
        )

        self.storage_account_location = (
            storage_account_location
        )

        # ----------------------------------------------------
        # Function App name
        # ----------------------------------------------------

        self.function_app_name = (
            function_app_name
        )

        # ----------------------------------------------------
        # App Service Plan name
        #
        # User does NOT provide this.
        # It is generated automatically.
        # ----------------------------------------------------

        self.function_app_plan_name = (
            f"{function_app_name}-plan"
        )

        # ----------------------------------------------------
        # Key Vault name
        #
        # User does NOT provide this.
        # It is generated automatically.
        # ----------------------------------------------------

        self.key_vault_name = (
            f"{function_app_name}-kv"
        )

        # ----------------------------------------------------
        # Tables
        # ----------------------------------------------------

        self.table_names = (
            table_names
        )

        # ----------------------------------------------------
        # Queues
        # ----------------------------------------------------

        self.queue_names = (
            queue_names
        )

    # ========================================================
    # DEPLOY
    # ========================================================

    def deploy(self):

        # ----------------------------------------------------
        # 1. Set subscription
        # ----------------------------------------------------

        set_subscription(
            self.subscription_id
        )

        # ----------------------------------------------------
        # 2. Create Resource Group
        # ----------------------------------------------------

        resource_group = create_resource_group(
            self.resource_group_name,
            self.resource_group_location
        )

        # ----------------------------------------------------
        # 3. Create Storage Account
        # ----------------------------------------------------

        storage_account = create_storage_account(
            self.resource_group_name,
            self.storage_account_name,
            self.storage_account_location
        )

        # ----------------------------------------------------
        # 4. Get Storage Account Key
        # ----------------------------------------------------

        storage_account_key = (
            get_storage_account_key(
                self.resource_group_name,
                self.storage_account_name
            )
        )

        if not storage_account_key:

            raise RuntimeError(
                "Could not obtain Storage Account key."
            )

        storage_account_key = (
            str(storage_account_key).strip()
        )

        # ----------------------------------------------------
        # 5. Create Tables
        #
        # This creates the tables, including:
        #
        # NotificationTemplates
        #
        # BUT it does NOT import NotificationTemplates.csv.
        # The content import will happen in the next flow.
        # ----------------------------------------------------

        tables = create_tables(
            self.storage_account_name,
            storage_account_key,
            self.table_names
        )

        # ----------------------------------------------------
        # 6. Create Queues
        # ----------------------------------------------------

        queues = create_queues(
            self.storage_account_name,
            storage_account_key,
            self.queue_names
        )

        # ----------------------------------------------------
        # 7. Create App Service Plan
        # ----------------------------------------------------

        app_service_plan = (
            create_app_service_plan(
                subscription_id=(
                    self.subscription_id
                ),

                resource_group_name=(
                    self.resource_group_name
                ),

                plan_name=(
                    self.function_app_plan_name
                ),

                location=(
                    self.resource_group_location
                )
            )
        )

        # ----------------------------------------------------
        # 8. Create Function App
        # ----------------------------------------------------

        function_app = (
            create_function_app(
                subscription_id=(
                    self.subscription_id
                ),

                resource_group_name=(
                    self.resource_group_name
                ),

                function_app_name=(
                    self.function_app_name
                ),

                storage_account_name=(
                    self.storage_account_name
                ),

                storage_account_key=(
                    storage_account_key
                ),

                app_service_plan_name=(
                    self.function_app_plan_name
                ),

                location=(
                    self.resource_group_location
                )
            )
        )

        # ====================================================
        # KEY VAULT SETUP
        # ====================================================

        # ----------------------------------------------------
        # 9. Initialize Azure Resource Service
        # ----------------------------------------------------

        azure_resource_service = (
            AzureResourceService(
                subscription_id=(
                    self.subscription_id
                )
            )
        )

        # ----------------------------------------------------
        # 10. Get Function App Managed Identity
        # ----------------------------------------------------

        function_app_principal_id = (
            azure_resource_service
            .get_function_app_principal_id(
                resource_group_name=(
                    self.resource_group_name
                ),

                function_app_name=(
                    self.function_app_name
                )
            )
        )

        # ----------------------------------------------------
        # 11. Get Azure Tenant ID
        # ----------------------------------------------------

        tenant_id = (
            azure_resource_service
            .get_tenant_id()
        )

        # ----------------------------------------------------
        # 12. Create / Get Key Vault
        # ----------------------------------------------------

        (
            key_vault,
            key_vault_created,
        ) = (
            azure_resource_service
            .create_key_vault(
                resource_group_name=(
                    self.resource_group_name
                ),

                key_vault_name=(
                    self.key_vault_name
                ),

                location=(
                    self.resource_group_location
                ),

                tenant_id=(
                    tenant_id
                )
            )
        )

        if not key_vault:

            raise RuntimeError(
                "Key Vault creation/get operation "
                "did not return a resource."
            )

        # ----------------------------------------------------
        # 13. Get Key Vault ID
        # ----------------------------------------------------

        key_vault_id = (
            azure_resource_service
            .get_key_vault_id(
                resource_group_name=(
                    self.resource_group_name
                ),

                key_vault_name=(
                    self.key_vault_name
                )
            )
        )

        # ----------------------------------------------------
        # 14. Get Key Vault URL
        # ----------------------------------------------------

        key_vault_url = (
            azure_resource_service
            .get_key_vault_url(
                self.key_vault_name
            )
        )

        # ----------------------------------------------------
        # 15. Assign Key Vault Secrets User Role
        #
        # Allows the Function App Managed Identity
        # to read secrets from Key Vault.
        # ----------------------------------------------------

        (
            _function_app_role_assignment,
            function_app_role_assigned,
        ) = (
            azure_resource_service
            .assign_key_vault_secrets_user_role(
                key_vault_id=(
                    key_vault_id
                ),

                principal_id=(
                    function_app_principal_id
                )
            )
        )

        # ----------------------------------------------------
        # 16. Configure KEY_VAULT_URL
        # ----------------------------------------------------

        azure_resource_service \
            .configure_function_app_key_vault_url(
                resource_group_name=(
                    self.resource_group_name
                ),

                function_app_name=(
                    self.function_app_name
                ),

                key_vault_url=(
                    key_vault_url
                )
            )

        function_app_key_vault_url_configured = (
            True
        )

        # ====================================================
        # DEPLOYMENT COMPLETE
        # ====================================================
        #
        # IMPORTANT:
        #
        # NotificationTemplates.csv is NOT imported here.
        #
        # The NotificationTemplates table itself has already
        # been created in step 5.
        #
        # The CSV/content import will be handled by the
        # next workflow.
        #
        # ====================================================

        return {

            "status": "success",

            "subscription_id":
                self.subscription_id,

            "resource_group": {

                "name":
                    self.resource_group_name,

                "location":
                    self.resource_group_location
            },

            "storage_account": {

                "name":
                    self.storage_account_name,

                "location":
                    self.storage_account_location
            },

            "app_service_plan": {

                "name":
                    self.function_app_plan_name,

                "location":
                    self.resource_group_location
            },

            "function_app": {

                "name":
                    self.function_app_name,

                "location":
                    self.resource_group_location,

                "app_service_plan":
                    self.function_app_plan_name,

                "managed_identity": {

                    "enabled": True,

                    "principal_id":
                        function_app_principal_id
                }
            },

            "key_vault": {

                "name":
                    self.key_vault_name,

                "url":
                    key_vault_url,

                "tenant_id":
                    tenant_id,

                "created":
                    key_vault_created,

                "function_app_role_assigned":
                    function_app_role_assigned,

                "function_app_key_vault_url_configured":
                    function_app_key_vault_url_configured
            },

            "tables":
                tables,

            "queues":
                queues,
        }