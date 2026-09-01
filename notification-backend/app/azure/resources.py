import logging
import shutil
import subprocess
from uuid import NAMESPACE_URL, uuid5

from azure.core.exceptions import (
    HttpResponseError,
    ResourceNotFoundError,
)

from azure.identity import DefaultAzureCredential

from azure.mgmt.authorization import (
    AuthorizationManagementClient,
)

from azure.mgmt.keyvault import (
    KeyVaultManagementClient,
)

from azure.mgmt.resource.resources import (
    ResourceManagementClient,
)

from azure.mgmt.web import (
    WebSiteManagementClient,
)

from azure.mgmt.web.models import (
    ManagedServiceIdentity,
)


logger = logging.getLogger(__name__)


class AzureResourceService:

    # ========================================================
    # BUILT-IN ROLE IDS
    # ========================================================

    KEY_VAULT_SECRETS_USER_ROLE_ID = (
        "4633458b-17de-408a-b874-0445c86b69e6"
    )

    KEY_VAULT_SECRETS_OFFICER_ROLE_ID = (
        "b86a8fe4-44ce-4948-aee5-eccb2c155cd7"
    )

    # ========================================================
    # STORAGE TABLE DATA CONTRIBUTOR
    # ========================================================

    STORAGE_TABLE_DATA_CONTRIBUTOR_ROLE_ID = (
        "0a9a7e1f-b9d0-4cc4-a60d-0316b1fca009"
    )

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        subscription_id: str,
    ):

        self.subscription_id = subscription_id

        # ====================================================
        # AZURE CREDENTIAL
        # ====================================================

        self.credential = DefaultAzureCredential()

        # ====================================================
        # RESOURCE MANAGEMENT
        # ====================================================

        self.resource_client = ResourceManagementClient(
            credential=self.credential,
            subscription_id=subscription_id,
        )

        # ====================================================
        # WEB / FUNCTION APP
        # ====================================================

        self.web_client = WebSiteManagementClient(
            credential=self.credential,
            subscription_id=subscription_id,
        )

        # ====================================================
        # KEY VAULT MANAGEMENT
        # ====================================================

        self.key_vault_client = KeyVaultManagementClient(
            credential=self.credential,
            subscription_id=subscription_id,
        )

        # ====================================================
        # AUTHORIZATION / RBAC
        # ====================================================

        self.authorization_client = AuthorizationManagementClient(
            credential=self.credential,
            subscription_id=subscription_id,
        )

    # ========================================================
    # AZURE CLI
    # ========================================================

    def _run_az_command(
        self,
        arguments: list[str],
    ) -> str:
        """
        Execute Azure CLI command.

        This uses the SAME Azure CLI login session created by:

            az login

        No tenant ID or user object ID needs to be supplied
        by the frontend.
        """

        az_path = shutil.which("az")

        if not az_path:
            raise RuntimeError(
                "Azure CLI is not available in PATH. "
                "Please run 'az login' from a terminal where "
                "Azure CLI is installed."
            )

        command = [
            az_path,
            *arguments,
        ]

        logger.info(
            "Executing Azure CLI command: az %s",
            " ".join(arguments),
        )

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )

        except FileNotFoundError as exc:

            raise RuntimeError(
                "Azure CLI could not be executed. "
                "Please verify that Azure CLI is installed."
            ) from exc

        except subprocess.CalledProcessError as exc:

            stderr = (
                exc.stderr.strip()
                if exc.stderr
                else ""
            )

            stdout = (
                exc.stdout.strip()
                if exc.stdout
                else ""
            )

            message = (
                stderr
                or stdout
                or "Unknown Azure CLI error."
            )

            raise RuntimeError(
                f"Azure CLI command failed: {message}"
            ) from exc

        value = result.stdout.strip()

        if not value:

            raise RuntimeError(
                "Azure CLI returned an empty response."
            )

        return value

    # ========================================================
    # TENANT ID
    # ========================================================

    def get_tenant_id(self) -> str:
        """
        Get the Tenant ID from the currently logged-in
        Azure CLI account.
        """

        logger.info(
            "Retrieving Azure Tenant ID..."
        )

        tenant_id = self._run_az_command(
            [
                "account",
                "show",
                "--subscription",
                self.subscription_id,
                "--query",
                "tenantId",
                "-o",
                "tsv",
            ]
        )

        logger.info(
            "Tenant ID retrieved successfully: %s",
            tenant_id,
        )

        return tenant_id

    # ========================================================
    # CURRENT USER OBJECT ID
    # ========================================================

    def get_current_user_object_id(self) -> str:
        """
        Get the Object ID of the currently authenticated
        Azure CLI user.
        """

        logger.info(
            "Retrieving current Azure user Object ID..."
        )

        object_id = self._run_az_command(
            [
                "ad",
                "signed-in-user",
                "show",
                "--query",
                "id",
                "-o",
                "tsv",
            ]
        )

        logger.info(
            "Current Azure user Object ID retrieved."
        )

        return object_id

    # ========================================================
    # RESOURCE GROUP
    # ========================================================

    def get_resource_group(
        self,
        resource_group_name: str,
    ):

        try:

            return (
                self.resource_client
                .resource_groups
                .get(
                    resource_group_name
                )
            )

        except ResourceNotFoundError as exc:

            raise ValueError(
                f"Resource Group "
                f"'{resource_group_name}' "
                "was not found."
            ) from exc

    # ========================================================
    # RESOURCE GROUP LOCATION
    # ========================================================

    def get_resource_group_location(
        self,
        resource_group_name: str,
    ) -> str:

        resource_group = (
            self.get_resource_group(
                resource_group_name
            )
        )

        if not resource_group.location:

            raise RuntimeError(
                f"Could not determine location "
                f"of Resource Group "
                f"'{resource_group_name}'."
            )

        return resource_group.location

    # ========================================================
    # FUNCTION APP
    # ========================================================

    def get_function_app(
        self,
        resource_group_name: str,
        function_app_name: str,
    ):

        try:

            return (
                self.web_client
                .web_apps
                .get(
                    resource_group_name,
                    function_app_name,
                )
            )

        except ResourceNotFoundError as exc:

            raise ValueError(
                f"Function App "
                f"'{function_app_name}' "
                f"was not found in Resource Group "
                f"'{resource_group_name}'."
            ) from exc

    # ========================================================
    # ENABLE SYSTEM-ASSIGNED MANAGED IDENTITY
    # ========================================================

    def enable_function_app_managed_identity(
        self,
        resource_group_name: str,
        function_app_name: str,
    ):

        function_app = (
            self.get_function_app(
                resource_group_name,
                function_app_name,
            )
        )

        # ----------------------------------------------------
        # Already enabled
        # ----------------------------------------------------

        if (
            function_app.identity
            and function_app.identity.principal_id
        ):

            logger.info(
                "System Assigned Managed Identity "
                "already enabled."
            )

            logger.info(
                "Principal ID: %s",
                function_app.identity.principal_id,
            )

            return function_app

        # ----------------------------------------------------
        # Enable identity
        # ----------------------------------------------------

        logger.info(
            "Enabling System Assigned Managed Identity "
            "on Function App '%s'...",
            function_app_name,
        )

        function_app.identity = ManagedServiceIdentity(
            type="SystemAssigned"
        )

        try:

            updated = (
                self.web_client
                .web_apps
                .begin_create_or_update(
                    resource_group_name,
                    function_app_name,
                    function_app,
                )
                .result()
            )

        except HttpResponseError as exc:

            raise RuntimeError(
                "Failed to enable System Assigned "
                f"Managed Identity on Function App "
                f"'{function_app_name}': {exc}"
            ) from exc

        if (
            not updated.identity
            or not updated.identity.principal_id
        ):

            raise RuntimeError(
                "Managed Identity was enabled but "
                "Principal ID could not be retrieved."
            )

        logger.info(
            "System Assigned Managed Identity "
            "enabled successfully."
        )

        logger.info(
            "Principal ID: %s",
            updated.identity.principal_id,
        )

        return updated

    # ========================================================
    # GET FUNCTION APP PRINCIPAL ID
    # ========================================================

    def get_function_app_principal_id(
        self,
        resource_group_name: str,
        function_app_name: str,
    ) -> str:

        function_app = (
            self.enable_function_app_managed_identity(
                resource_group_name,
                function_app_name,
            )
        )

        if (
            not function_app.identity
            or not function_app.identity.principal_id
        ):

            raise RuntimeError(
                "Function App Principal ID "
                "could not be obtained."
            )

        return function_app.identity.principal_id

    # ========================================================
    # STORAGE ACCOUNT
    # ========================================================

    def validate_storage_account(
        self,
        resource_group_name: str,
        storage_account_name: str,
    ):

        resource_id = (
            f"/subscriptions/"
            f"{self.subscription_id}"
            f"/resourceGroups/"
            f"{resource_group_name}"
            f"/providers/"
            f"Microsoft.Storage/"
            f"storageAccounts/"
            f"{storage_account_name}"
        )

        try:

            return (
                self.resource_client
                .resources
                .get_by_id(
                    resource_id,
                    api_version="2023-01-01",
                )
            )

        except ResourceNotFoundError as exc:

            raise ValueError(
                f"Storage Account "
                f"'{storage_account_name}' "
                f"was not found in Resource Group "
                f"'{resource_group_name}'."
            ) from exc

    # ========================================================
    # GET STORAGE ACCOUNT RESOURCE ID
    # ========================================================

    def get_storage_account_id(
        self,
        resource_group_name: str,
        storage_account_name: str,
    ) -> str:
        """
        Get the full Azure Resource ID of the Storage Account.
        """

        storage_account = (
            self.validate_storage_account(
                resource_group_name,
                storage_account_name,
            )
        )

        if not storage_account.id:

            raise RuntimeError(
                "Storage Account resource ID "
                "could not be retrieved."
            )

        return storage_account.id

    # ========================================================
    # ASSIGN STORAGE TABLE DATA CONTRIBUTOR
    # ========================================================

    def assign_storage_table_data_contributor_role(
        self,
        storage_account_id: str,
        principal_id: str,
    ):
        """
        Assign the Storage Table Data Contributor role
        to the Function App Managed Identity.

        This allows the Function App to:

            - Read Azure Table entities
            - Add entities
            - Update entities
            - Delete entities
            - Create/update table data

        Scope:
            Storage Account
        """

        role_definition_id = (
            f"/subscriptions/"
            f"{self.subscription_id}"
            f"/providers/"
            f"Microsoft.Authorization/"
            f"roleDefinitions/"
            f"{self.STORAGE_TABLE_DATA_CONTRIBUTOR_ROLE_ID}"
        )

        # ----------------------------------------------------
        # Deterministic role assignment ID
        # ----------------------------------------------------

        assignment_uuid = str(
            uuid5(
                NAMESPACE_URL,
                f"{storage_account_id}/"
                f"{principal_id}/"
                f"{self.STORAGE_TABLE_DATA_CONTRIBUTOR_ROLE_ID}",
            )
        )

        # ----------------------------------------------------
        # Check existing assignment
        # ----------------------------------------------------

        try:

            existing = (
                self.authorization_client
                .role_assignments
                .get(
                    storage_account_id,
                    assignment_uuid,
                )
            )

            if existing:

                logger.info(
                    "Storage Table Data Contributor role "
                    "already exists for Function App."
                )

                return existing, False

        except ResourceNotFoundError:

            pass

        except HttpResponseError:

            pass

        # ----------------------------------------------------
        # Role assignment parameters
        # ----------------------------------------------------

        parameters = {
            "role_definition_id": role_definition_id,
            "principal_id": principal_id,
            "principal_type": "ServicePrincipal",
        }

        # ----------------------------------------------------
        # Create role assignment
        # ----------------------------------------------------

        try:

            assignment = (
                self.authorization_client
                .role_assignments
                .create(
                    storage_account_id,
                    assignment_uuid,
                    parameters,
                )
            )

            logger.info(
                "Storage Table Data Contributor role "
                "assigned to Function App Managed Identity."
            )

            return assignment, True

        except HttpResponseError as exc:

            if exc.status_code == 409:

                logger.info(
                    "Storage Table Data Contributor role "
                    "assignment already exists."
                )

                return None, False

            raise RuntimeError(
                "Failed to assign Storage Table Data "
                "Contributor role: "
                f"{exc}"
            ) from exc

    # ========================================================
    # GET KEY VAULT
    # ========================================================

    def get_key_vault(
        self,
        resource_group_name: str,
        key_vault_name: str,
    ):

        try:

            return (
                self.key_vault_client
                .vaults
                .get(
                    resource_group_name,
                    key_vault_name,
                )
            )

        except ResourceNotFoundError:

            return None

    # ========================================================
    # CREATE KEY VAULT
    # ========================================================

    def create_key_vault(
        self,
        resource_group_name: str,
        key_vault_name: str,
        location: str,
        tenant_id: str,
    ):

        existing = self.get_key_vault(
            resource_group_name,
            key_vault_name,
        )

        if existing:

            logger.info(
                "Key Vault '%s' already exists.",
                key_vault_name,
            )

            return existing, False

        logger.info(
            "Creating Key Vault '%s'...",
            key_vault_name,
        )

        parameters = {
            "location": location,
            "properties": {
                "tenantId": tenant_id,

                "sku": {
                    "family": "A",
                    "name": "standard",
                },

                "enableRbacAuthorization": True,

                "enabledForDeployment": False,

                "enabledForDiskEncryption": False,

                "enabledForTemplateDeployment": False,

                "publicNetworkAccess": "Enabled",
            },
        }

        try:

            operation = (
                self.key_vault_client
                .vaults
                .begin_create_or_update(
                    resource_group_name,
                    key_vault_name,
                    parameters,
                )
            )

            vault = operation.result()

            logger.info(
                "Key Vault '%s' created successfully.",
                key_vault_name,
            )

            return vault, True

        except HttpResponseError as exc:

            raise RuntimeError(
                f"Failed to create Key Vault "
                f"'{key_vault_name}': {exc}"
            ) from exc

    # ========================================================
    # GET KEY VAULT ID
    # ========================================================

    def get_key_vault_id(
        self,
        resource_group_name: str,
        key_vault_name: str,
    ) -> str:

        key_vault = (
            self.get_key_vault(
                resource_group_name,
                key_vault_name,
            )
        )

        if not key_vault:

            raise ValueError(
                f"Key Vault "
                f"'{key_vault_name}' "
                "was not found."
            )

        if not key_vault.id:

            raise RuntimeError(
                "Key Vault resource ID "
                "could not be retrieved."
            )

        return key_vault.id

    # ========================================================
    # KEY VAULT URL
    # ========================================================

    @staticmethod
    def get_key_vault_url(
        key_vault_name: str,
    ) -> str:

        return (
            f"https://"
            f"{key_vault_name}"
            f".vault.azure.net/"
        )

    # ========================================================
    # ASSIGN KEY VAULT SECRETS USER
    # ========================================================

    def assign_key_vault_secrets_user_role(
        self,
        key_vault_id: str,
        principal_id: str,
    ):

        role_definition_id = (
            f"/subscriptions/"
            f"{self.subscription_id}"
            f"/providers/"
            f"Microsoft.Authorization/"
            f"roleDefinitions/"
            f"{self.KEY_VAULT_SECRETS_USER_ROLE_ID}"
        )

        assignment_uuid = str(
            uuid5(
                NAMESPACE_URL,
                f"{key_vault_id}/"
                f"{principal_id}/"
                f"{self.KEY_VAULT_SECRETS_USER_ROLE_ID}",
            )
        )

        # ----------------------------------------------------
        # Check existing assignment
        # ----------------------------------------------------

        try:

            existing = (
                self.authorization_client
                .role_assignments
                .get(
                    key_vault_id,
                    assignment_uuid,
                )
            )

            if existing:

                logger.info(
                    "Key Vault Secrets User role "
                    "already exists."
                )

                return existing, False

        except ResourceNotFoundError:

            pass

        except HttpResponseError:

            pass

        parameters = {
            "role_definition_id": role_definition_id,
            "principal_id": principal_id,
            "principal_type": "ServicePrincipal",
        }

        try:

            assignment = (
                self.authorization_client
                .role_assignments
                .create(
                    key_vault_id,
                    assignment_uuid,
                    parameters,
                )
            )

            logger.info(
                "Key Vault Secrets User role "
                "assigned to Function App."
            )

            return assignment, True

        except HttpResponseError as exc:

            if exc.status_code == 409:

                logger.info(
                    "Key Vault Secrets User role "
                    "assignment already exists."
                )

                return None, False

            raise RuntimeError(
                "Failed to assign Key Vault Secrets User role: "
                f"{exc}"
            ) from exc

    # ========================================================
    # ASSIGN KEY VAULT SECRETS OFFICER
    # ========================================================

    def assign_key_vault_secrets_officer_role(
        self,
        key_vault_id: str,
        user_object_id: str,
    ):

        role_definition_id = (
            f"/subscriptions/"
            f"{self.subscription_id}"
            f"/providers/"
            f"Microsoft.Authorization/"
            f"roleDefinitions/"
            f"{self.KEY_VAULT_SECRETS_OFFICER_ROLE_ID}"
        )

        assignment_uuid = str(
            uuid5(
                NAMESPACE_URL,
                f"{key_vault_id}/"
                f"{user_object_id}/"
                f"{self.KEY_VAULT_SECRETS_OFFICER_ROLE_ID}",
            )
        )

        # ----------------------------------------------------
        # Check existing assignment
        # ----------------------------------------------------

        try:

            existing = (
                self.authorization_client
                .role_assignments
                .get(
                    key_vault_id,
                    assignment_uuid,
                )
            )

            if existing:

                logger.info(
                    "Key Vault Secrets Officer role "
                    "already exists."
                )

                return existing, False

        except ResourceNotFoundError:

            pass

        except HttpResponseError:

            pass

        parameters = {
            "role_definition_id": role_definition_id,
            "principal_id": user_object_id,
            "principal_type": "User",
        }

        try:

            assignment = (
                self.authorization_client
                .role_assignments
                .create(
                    key_vault_id,
                    assignment_uuid,
                    parameters,
                )
            )

            logger.info(
                "Key Vault Secrets Officer role "
                "assigned to current Azure user."
            )

            return assignment, True

        except HttpResponseError as exc:

            if exc.status_code == 409:

                logger.info(
                    "Key Vault Secrets Officer role "
                    "assignment already exists."
                )

                return None, False

            raise RuntimeError(
                "Failed to assign Key Vault Secrets Officer role: "
                f"{exc}"
            ) from exc

    # ========================================================
    # CONFIGURE FUNCTION APP KEY VAULT URL
    # ========================================================

    def configure_function_app_key_vault_url(
        self,
        resource_group_name: str,
        function_app_name: str,
        key_vault_url: str,
    ):

        logger.info(
            "Configuring KEY_VAULT_URL "
            "in Function App..."
        )

        try:

            settings = (
                self.web_client
                .web_apps
                .list_application_settings(
                    resource_group_name,
                    function_app_name,
                )
            )

            properties = (
                dict(settings.properties)
                if settings and settings.properties
                else {}
            )

            properties["KEY_VAULT_URL"] = key_vault_url

            result = (
                self.web_client
                .web_apps
                .update_application_settings(
                    resource_group_name,
                    function_app_name,
                    {
                        "properties": properties
                    },
                )
            )

            logger.info(
                "KEY_VAULT_URL configured successfully."
            )

            return result

        except HttpResponseError as exc:

            raise RuntimeError(
                "Failed to configure KEY_VAULT_URL "
                f"for Function App '{function_app_name}': {exc}"
            ) from exc