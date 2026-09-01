
import json
import logging
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.web import WebSiteManagementClient


logger = logging.getLogger(__name__)


class FunctionAppAzureService:

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(
        self,
        subscription_id: str,
        function_app_source_dir: str = "FunctionApp",
    ):
        self.subscription_id = subscription_id

        # --------------------------------------------------------
        # Azure credential
        # --------------------------------------------------------

        self.credential = DefaultAzureCredential(
            exclude_interactive_browser_credential=False
        )

        # --------------------------------------------------------
        # Azure management clients
        # --------------------------------------------------------

        self.resource_client = ResourceManagementClient(
            self.credential,
            subscription_id,
        )

        self.storage_client = StorageManagementClient(
            self.credential,
            subscription_id,
        )

        self.web_client = WebSiteManagementClient(
            self.credential,
            subscription_id,
        )

        # --------------------------------------------------------
        # Project root
        #
        # app/azure/function_app.py
        #
        # parents[2] = notification-backend/
        # --------------------------------------------------------

        self.project_root = Path(__file__).resolve().parents[2]

        source_path = Path(function_app_source_dir)

        if source_path.is_absolute():
            self.function_app_source_dir = source_path.resolve()
        else:
            self.function_app_source_dir = (
                self.project_root / source_path
            ).resolve()

        logger.info(
            "FunctionAppAzureService initialized."
        )

        logger.info(
            "Subscription: %s",
            subscription_id,
        )

        logger.info(
            "Function App source directory: %s",
            self.function_app_source_dir,
        )

    # ============================================================
    # AZURE CLI
    # ============================================================

    def _get_az_command(self) -> str:
        """
        Find Azure CLI executable.

        Windows commonly uses:

        C:\\Program Files (x86)\\Microsoft SDKs\\Azure\\CLI2\\wbin\\az.cmd

        We first check PATH and then common Windows locations.
        """

        # --------------------------------------------------------
        # PATH
        # --------------------------------------------------------

        az_from_path = shutil.which("az")

        if az_from_path:
            logger.info(
                "Azure CLI found through PATH: %s",
                az_from_path,
            )
            return az_from_path

        az_cmd_from_path = shutil.which("az.cmd")

        if az_cmd_from_path:
            logger.info(
                "Azure CLI found through PATH: %s",
                az_cmd_from_path,
            )
            return az_cmd_from_path

        # --------------------------------------------------------
        # Windows fallback locations
        # --------------------------------------------------------

        windows_candidates = [
            Path(
                r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
            ),
            Path(
                r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
            ),
            Path(
                r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az"
            ),
            Path(
                r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az"
            ),
        ]

        for candidate in windows_candidates:

            if candidate.exists():

                logger.info(
                    "Azure CLI found at: %s",
                    candidate,
                )

                return str(candidate)

        raise RuntimeError(
            "Azure CLI was not found.\n"
            "Run 'where.exe az' in PowerShell and verify Azure CLI "
            "is installed."
        )

    # ============================================================
    # RUN AZURE CLI
    # ============================================================

    def _run_az(
        self,
        arguments: list[str],
        timeout: int = 300,
        check: bool = True,
    ) -> subprocess.CompletedProcess:

        az_command = self._get_az_command()

        command = [
            az_command,
            *arguments,
        ]

        logger.info(
            "Running Azure CLI command: az %s",
            " ".join(
                str(argument)
                for argument in arguments
                if "KEY" not in str(argument).upper()
            ),
        )

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )

        except FileNotFoundError as exc:

            raise RuntimeError(
                "Azure CLI executable could not be started.\n"
                f"Azure CLI path: {az_command}"
            ) from exc

        except subprocess.TimeoutExpired as exc:

            raise RuntimeError(
                "Azure CLI command timed out.\n"
                f"Command: az {' '.join(arguments)}"
            ) from exc

        if check and result.returncode != 0:

            stdout = (
                result.stdout.strip()
                if result.stdout
                else ""
            )

            stderr = (
                result.stderr.strip()
                if result.stderr
                else ""
            )

            error_message = stderr or stdout

            raise RuntimeError(
                "Azure CLI command failed.\n"
                f"Exit code: {result.returncode}\n"
                f"Error: {error_message}"
            )

        return result

    # ============================================================
    # CHECK AZURE CLI LOGIN
    # ============================================================

    def check_azure_cli_login(self):

        logger.info(
            "Checking Azure CLI authentication."
        )

        result = self._run_az(
            [
                "account",
                "show",
                "--subscription",
                self.subscription_id,
                "--output",
                "json",
            ],
            timeout=60,
        )

        if not result.stdout.strip():

            raise RuntimeError(
                "Azure CLI returned no account information."
            )

        logger.info(
            "Azure CLI authentication confirmed."
        )

    # ============================================================
    # RESOURCE GROUP
    # ============================================================

    def get_resource_group(
        self,
        resource_group_name: str,
    ):

        logger.info(
            "Getting Resource Group: %s",
            resource_group_name,
        )

        try:

            return (
                self.resource_client
                .resource_groups
                .get(resource_group_name)
            )

        except Exception:

            logger.info(
                "Resource Group does not exist: %s",
                resource_group_name,
            )

            return None

    # ============================================================
    # ENSURE RESOURCE GROUP
    # ============================================================

    def ensure_resource_group(
        self,
        resource_group_name: str,
        location: str,
    ):

        existing = self.get_resource_group(
            resource_group_name
        )

        if existing:

            logger.info(
                "Resource Group already exists."
            )

            return existing

        logger.info(
            "Creating Resource Group: %s",
            resource_group_name,
        )

        try:

            resource_group = (
                self.resource_client
                .resource_groups
                .create_or_update(
                    resource_group_name,
                    {
                        "location": location
                    },
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "Failed to create Resource Group: "
                f"{resource_group_name}"
            ) from exc

        logger.info(
            "Resource Group created successfully."
        )

        return resource_group

    # ============================================================
    # STORAGE ACCOUNT
    # ============================================================

    def get_storage_account(
        self,
        resource_group_name: str,
        storage_account_name: str,
    ):

        logger.info(
            "Checking Storage Account: %s",
            storage_account_name,
        )

        try:

            return (
                self.storage_client
                .storage_accounts
                .get_properties(
                    resource_group_name,
                    storage_account_name,
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "Storage Account could not be found: "
                f"{storage_account_name}"
            ) from exc

    # ============================================================
    # GET STORAGE ACCOUNT KEY
    # ============================================================

    def get_storage_account_key(
        self,
        resource_group_name: str,
        storage_account_name: str,
    ) -> str:

        logger.info(
            "Getting Storage Account key using Azure CLI."
        )

        result = self._run_az(
            [
                "storage",
                "account",
                "keys",
                "list",
                "--resource-group",
                resource_group_name,
                "--account-name",
                storage_account_name,
                "--query",
                "[0].value",
                "--output",
                "tsv",
            ],
            timeout=120,
        )

        key = (
            result.stdout.strip()
            if result.stdout
            else ""
        )

        if not key:

            raise RuntimeError(
                "Azure CLI did not return a Storage Account key. "
                f"Storage Account: {storage_account_name}"
            )

        logger.info(
            "Storage Account key retrieved successfully."
        )

        return key

    # ============================================================
    # FUNCTION APP
    # ============================================================

    def get_function_app(
        self,
        resource_group_name: str,
        function_app_name: str,
    ):

        logger.info(
            "Checking Function App: %s",
            function_app_name,
        )

        try:

            return (
                self.web_client
                .web_apps
                .get(
                    resource_group_name,
                    function_app_name,
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "Function App could not be found: "
                f"{function_app_name}"
            ) from exc

    # ============================================================
    # FUNCTION APP EXISTS
    # ============================================================

    def function_app_exists(
        self,
        resource_group_name: str,
        function_app_name: str,
    ) -> bool:

        try:

            self.web_client.web_apps.get(
                resource_group_name,
                function_app_name,
            )

            return True

        except Exception:

            return False

    # ============================================================
    # GET APPLICATION SETTINGS
    # ============================================================

    def get_function_app_settings(
        self,
        resource_group_name: str,
        function_app_name: str,
    ) -> dict[str, str]:

        try:

            settings = (
                self.web_client
                .web_apps
                .list_application_settings(
                    resource_group_name,
                    function_app_name,
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "Failed to retrieve Function App settings."
            ) from exc

        properties = getattr(
            settings,
            "properties",
            None,
        )

        if not properties:
            return {}

        return dict(properties)

    # ============================================================
    # SET APPLICATION SETTINGS
    # ============================================================

    def set_function_app_settings(
        self,
        resource_group_name: str,
        function_app_name: str,
        settings: dict[str, str],
    ):

        if not settings:

            logger.info(
                "No Function App settings supplied."
            )

            return

        logger.info(
            "Updating Function App settings."
        )

        existing_settings = (
            self.get_function_app_settings(
                resource_group_name,
                function_app_name,
            )
        )

        existing_settings.update(settings)

        try:

            self.web_client.web_apps.update_application_settings(
                resource_group_name,
                function_app_name,
                {
                    "properties": existing_settings
                },
            )

        except Exception as exc:

            raise RuntimeError(
                "Failed to update Function App settings."
            ) from exc

        logger.info(
            "Function App settings updated successfully."
        )

    # ============================================================
    # CONFIGURE FUNCTION APP SETTINGS
    # ============================================================

    def configure_function_app_settings(
        self,
        resource_group_name: str,
        function_app_name: str,
        storage_account_name: str,
        storage_account_key: str,
        table_name: str,
        cache_expiration_minutes: int = 10,
    ):

        settings = {
            "STORAGE_ACCOUNT_NAME": storage_account_name,
            "STORAGE_ACCOUNT_KEY": storage_account_key,
            "TABLE_NAME": table_name,
            "CACHE_EXPIRATION_MINUTES": str(
                cache_expiration_minutes
            ),
        }

        self.set_function_app_settings(
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            settings=settings,
        )

    # ============================================================
    # CREATE FUNCTION APP
    # ============================================================

    def create_function_app(
        self,
        resource_group_name: str,
        function_app_name: str,
        storage_account_name: str,
        location: str,
        runtime: str = "python",
        runtime_version: str = "3.11",
    ):

        logger.info(
            "Creating Function App: %s",
            function_app_name,
        )

        if self.function_app_exists(
            resource_group_name,
            function_app_name,
        ):

            logger.info(
                "Function App already exists."
            )

            return self.get_function_app(
                resource_group_name,
                function_app_name,
            )

        site_config = {
            "linux_fx_version":
                f"{runtime}|{runtime_version}",
        }

        app_settings = [
            {
                "name":
                    "FUNCTIONS_EXTENSION_VERSION",
                "value":
                    "~4",
            },
            {
                "name":
                    "AzureWebJobsStorage__accountName",
                "value":
                    storage_account_name,
            },
        ]

        site_envelope = {
            "location": location,

            "kind":
                "functionapp,linux",

            "https_only":
                True,

            "site_config":
                site_config,

            "identity": {
                "type":
                    "SystemAssigned"
            },

            "properties": {
                "siteConfig": {
                    "appSettings":
                        app_settings
                }
            },
        }

        try:

            function_app = (
                self.web_client
                .web_apps
                .begin_create_or_update(
                    resource_group_name,
                    function_app_name,
                    site_envelope,
                )
                .result()
            )

        except Exception as exc:

            raise RuntimeError(
                "Failed to create Function App: "
                f"{function_app_name}"
            ) from exc

        logger.info(
            "Function App created successfully."
        )

        return function_app

    # ============================================================
    # ENABLE MANAGED IDENTITY
    # ============================================================

    def enable_managed_identity(
        self,
        resource_group_name: str,
        function_app_name: str,
    ):

        logger.info(
            "Enabling system-assigned managed identity."
        )

        function_app = (
            self.web_client
            .web_apps
            .get(
                resource_group_name,
                function_app_name,
            )
        )

        function_app.identity = {
            "type":
                "SystemAssigned"
        }

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

        except Exception as exc:

            raise RuntimeError(
                "Failed to enable managed identity."
            ) from exc

        logger.info(
            "Managed Identity enabled."
        )

        return updated

    # ============================================================
    # GET PRINCIPAL ID
    # ============================================================

    def get_function_app_principal_id(
        self,
        resource_group_name: str,
        function_app_name: str,
    ) -> str:

        function_app = (
            self.web_client
            .web_apps
            .get(
                resource_group_name,
                function_app_name,
            )
        )

        identity = getattr(
            function_app,
            "identity",
            None,
        )

        if not identity:

            raise RuntimeError(
                "Function App does not have "
                "a managed identity."
            )

        principal_id = getattr(
            identity,
            "principal_id",
            None,
        )

        if not principal_id:

            raise RuntimeError(
                "Function App principal ID "
                "could not be retrieved."
            )

        return str(principal_id)

    # ============================================================
    # VALIDATE FUNCTION APP SOURCE
    # ============================================================

    def validate_function_app_source(self):

        source_dir = self.function_app_source_dir

        logger.info(
            "Validating Function App source: %s",
            source_dir,
        )

        if not source_dir.exists():

            raise RuntimeError(
                "Function App source directory does not exist: "
                f"{source_dir}\n"
                "Expected structure:\n"
                f"{self.project_root}\\FunctionApp"
            )

        if not source_dir.is_dir():

            raise RuntimeError(
                "Function App source path is not a directory: "
                f"{source_dir}"
            )

        required_files = [
            "host.json",
            "requirements.txt",
        ]

        for relative_path in required_files:

            file_path = (
                source_dir /
                relative_path
            )

            if not file_path.exists():

                raise RuntimeError(
                    "Required Function App file not found: "
                    f"{file_path}"
                )

        # --------------------------------------------------------
        # Find functions
        # --------------------------------------------------------

        function_json_files = list(
            source_dir.rglob("function.json")
        )

        logger.info(
            "Found %d function.json file(s).",
            len(function_json_files),
        )

        for function_json in function_json_files:

            logger.info(
                "Found function definition: %s",
                function_json.relative_to(source_dir),
            )

        logger.info(
            "Function App source validation successful."
        )

    # ============================================================
    # CREATE ZIP
    # ============================================================

    def create_function_app_zip(self) -> Path:
        """
        Create a deployment ZIP containing the complete
        FunctionApp directory.

        IMPORTANT:
        The contents of FunctionApp are placed at the ROOT
        of the ZIP.

        Correct:

            functionapp.zip
            ├── host.json
            ├── requirements.txt
            ├── all_ip_report/
            │   └── function.json
            ├── AssetDataProcessing/
            │   └── function.json
            ├── GetPartitionConfigs/
            │   └── function.json
            └── ...

        Incorrect:

            functionapp.zip
            └── FunctionApp/
                ├── host.json
                └── ...
        """

        self.validate_function_app_source()

        source_dir = self.function_app_source_dir

        # --------------------------------------------------------
        # ZIP is created in project root
        # --------------------------------------------------------

        zip_path = (
            self.project_root /
            "functionapp.zip"
        )

        logger.info(
            "========================================"
        )

        logger.info(
            "CREATING FUNCTION APP ZIP"
        )

        logger.info(
            "Source: %s",
            source_dir,
        )

        logger.info(
            "ZIP: %s",
            zip_path,
        )

        # Remove old ZIP

        if zip_path.exists():

            logger.info(
                "Removing previous ZIP: %s",
                zip_path,
            )

            zip_path.unlink()

        try:

            with zipfile.ZipFile(
                zip_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as zip_file:

                for file_path in source_dir.rglob("*"):

                    if not file_path.is_file():
                        continue

                    relative_path = (
                        file_path.relative_to(
                            source_dir
                        )
                    )

                    # ------------------------------------------------
                    # Skip Python cache
                    # ------------------------------------------------

                    if "__pycache__" in relative_path.parts:
                        continue

                    if relative_path.suffix == ".pyc":
                        continue

                    # ------------------------------------------------
                    # Skip old ZIP files
                    # ------------------------------------------------

                    if relative_path.name in (
                        "functionapp.zip",
                        "released-package.zip",
                    ):
                        continue

                    # ------------------------------------------------
                    # Add file to ZIP
                    #
                    # IMPORTANT:
                    # relative_path is used so FunctionApp itself
                    # is NOT included as a top-level directory.
                    # ------------------------------------------------

                    zip_file.write(
                        file_path,
                        relative_path.as_posix(),
                    )

                    logger.debug(
                        "Added to ZIP: %s",
                        relative_path.as_posix(),
                    )

            # --------------------------------------------------------
            # Validate ZIP
            # --------------------------------------------------------

            with zipfile.ZipFile(
                zip_path,
                mode="r",
            ) as zip_file:

                names = zip_file.namelist()

                function_json_files = [
                    name
                    for name in names
                    if name.endswith(
                        "/function.json"
                    )
                ]

                # Handle root-level function.json too

                if "function.json" in names:

                    function_json_files.append(
                        "function.json"
                    )

                logger.info(
                    "========================================"
                )

                logger.info(
                    "FUNCTIONS INCLUDED IN ZIP"
                )

                for function_json in function_json_files:

                    logger.info(
                        "Included: %s",
                        function_json,
                    )

                logger.info(
                    "Total function.json files in ZIP: %d",
                    len(function_json_files),
                )

                # ----------------------------------------------------
                # Make sure host.json is at ZIP root
                # ----------------------------------------------------

                if "host.json" not in names:

                    raise RuntimeError(
                        "Invalid Function App ZIP: "
                        "host.json is not at ZIP root."
                    )

                # ----------------------------------------------------
                # Make sure requirements.txt is at ZIP root
                # ----------------------------------------------------

                if "requirements.txt" not in names:

                    raise RuntimeError(
                        "Invalid Function App ZIP: "
                        "requirements.txt is not at ZIP root."
                    )

                if not function_json_files:

                    raise RuntimeError(
                        "Invalid Function App ZIP: "
                        "no function.json files were found."
                    )

            logger.info(
                "Function App ZIP created successfully."
            )

            logger.info(
                "ZIP path: %s",
                zip_path,
            )

            logger.info(
                "ZIP size: %.2f MB",
                zip_path.stat().st_size / (1024 * 1024),
            )

            return zip_path

        except Exception:

            if zip_path.exists():

                try:
                    zip_path.unlink()
                except Exception:
                    pass

            raise

    # ============================================================
    # DEPLOY ZIP
    # ============================================================

    def deploy_zip(
        self,
        resource_group_name: str,
        function_app_name: str,
        zip_path: Path,
        remote_build: bool = True,
    ):

        logger.info(
            "========================================"
        )

        logger.info(
            "DEPLOYING FUNCTION APP ZIP"
        )

        # --------------------------------------------------------
        # Validate ZIP
        # --------------------------------------------------------

        if not zip_path.exists():

            raise RuntimeError(
                "Deployment ZIP does not exist: "
                f"{zip_path}"
            )

        if not zip_path.is_file():

            raise RuntimeError(
                "Deployment ZIP is not a file: "
                f"{zip_path}"
            )

        # --------------------------------------------------------
        # Validate Function App
        # --------------------------------------------------------

        self.get_function_app(
            resource_group_name,
            function_app_name,
        )

        # --------------------------------------------------------
        # Validate Azure CLI
        # --------------------------------------------------------

        self.check_azure_cli_login()

        # --------------------------------------------------------
        # IMPORTANT:
        #
        # Azure CLI config-zip deploys the ZIP to the Function App.
        #
        # --build-remote true tells Azure to install dependencies
        # from requirements.txt on the server.
        # --------------------------------------------------------

        arguments = [
            "functionapp",
            "deployment",
            "source",
            "config-zip",

            "--subscription",
            self.subscription_id,

            "--resource-group",
            resource_group_name,

            "--name",
            function_app_name,

            "--src",
            str(zip_path),

            "--build-remote",
            str(remote_build).lower(),

            "--output",
            "json",
        ]

        logger.info(
            "Executing Function App ZIP deployment."
        )

        logger.info(
            "Function App: %s",
            function_app_name,
        )

        logger.info(
            "Resource Group: %s",
            resource_group_name,
        )

        logger.info(
            "ZIP: %s",
            zip_path,
        )

        result = self._run_az(
            arguments,
            timeout=1800,
        )

        output = (
            result.stdout.strip()
            if result.stdout
            else ""
        )

        if output:

            logger.info(
                "Azure Function deployment response: %s",
                output,
            )

        logger.info(
            "========================================"
        )

        logger.info(
            "FUNCTION APP ZIP DEPLOYMENT COMPLETED"
        )

        logger.info(
            "========================================"
        )

        return {
            "status": "success",
            "message":
                "Function App ZIP deployed successfully.",
            "output": output,
        }

    # ============================================================
    # RESTART FUNCTION APP
    # ============================================================

    def restart_function_app(
        self,
        resource_group_name: str,
        function_app_name: str,
    ):

        logger.info(
            "Restarting Function App: %s",
            function_app_name,
        )

        try:

            self.web_client.web_apps.restart(
                resource_group_name,
                function_app_name,
            )

        except Exception as exc:

            raise RuntimeError(
                "Failed to restart Function App: "
                f"{function_app_name}"
            ) from exc

        logger.info(
            "Function App restarted successfully."
        )

    # ============================================================
    # VERIFY DEPLOYMENT
    # ============================================================

    def verify_function_app_deployment(
        self,
        resource_group_name: str,
        function_app_name: str,
    ):

        logger.info(
            "========================================"
        )

        logger.info(
            "VERIFYING FUNCTION APP DEPLOYMENT"
        )

        # --------------------------------------------------------
        # Get Function App
        # --------------------------------------------------------

        function_app = self.get_function_app(
            resource_group_name,
            function_app_name,
        )

        hostname = getattr(
            function_app,
            "default_host_name",
            None,
        )

        # --------------------------------------------------------
        # Get deployed functions
        # --------------------------------------------------------

        result = self._run_az(
            [
                "functionapp",
                "function",
                "list",

                "--subscription",
                self.subscription_id,

                "--resource-group",
                resource_group_name,

                "--name",
                function_app_name,

                "--output",
                "json",
            ],
            timeout=180,
        )

        functions = []

        if result.stdout.strip():

            try:

                parsed = json.loads(
                    result.stdout
                )

                if isinstance(
                    parsed,
                    list,
                ):

                    functions = parsed

            except Exception as exc:

                logger.warning(
                    "Could not parse function list: %s",
                    exc,
                )

        logger.info(
            "Azure reports %d deployed function(s).",
            len(functions),
        )

        # --------------------------------------------------------
        # Print function names
        # --------------------------------------------------------

        function_names = []

        for function in functions:

            if isinstance(
                function,
                dict,
            ):

                name = (
                    function.get("name")
                    or function.get("properties", {}).get(
                        "name"
                    )
                )

                if name:

                    function_names.append(
                        name
                    )

                    logger.info(
                        "Deployed function: %s",
                        name,
                    )

        logger.info(
            "========================================"
        )

        if not functions:

            logger.warning(
                "WARNING: Azure reports ZERO deployed functions."
            )

        else:

            logger.info(
                "Function deployment verification successful."
            )

        logger.info(
            "========================================"
        )

        return {
            "hostname": hostname,
            "function_count": len(functions),
            "functions": functions,
            "function_names": function_names,
            "deployment_verified":
                len(functions) > 0,
        }

    # ============================================================
    # DEPLOY COMPLETE FUNCTION APP
    # ============================================================

    def deploy_function_app(
        self,
        resource_group_name: str,
        function_app_name: str,
        storage_account_name: str,
        storage_account_key: Optional[str] = None,
        table_name: str = "AppConfiguration",
        cache_expiration_minutes: int = 10,
        remote_build: bool = True,
        restart_after_deployment: bool = True,
    ):

        logger.info(
            "================================================"
        )

        logger.info(
            "STARTING COMPLETE FUNCTION APP DEPLOYMENT"
        )

        logger.info(
            "Function App: %s",
            function_app_name,
        )

        logger.info(
            "Resource Group: %s",
            resource_group_name,
        )

        logger.info(
            "================================================"
        )

        # --------------------------------------------------------
        # 1. Get storage key if not supplied
        # --------------------------------------------------------

        if not storage_account_key:

            logger.info(
                "Storage Account key not supplied."
            )

            storage_account_key = (
                self.get_storage_account_key(
                    resource_group_name,
                    storage_account_name,
                )
            )

        # --------------------------------------------------------
        # 2. Configure application settings
        # --------------------------------------------------------

        logger.info(
            "Configuring Function App application settings."
        )

        self.configure_function_app_settings(
            resource_group_name=
                resource_group_name,

            function_app_name=
                function_app_name,

            storage_account_name=
                storage_account_name,

            storage_account_key=
                storage_account_key,

            table_name=
                table_name,

            cache_expiration_minutes=
                cache_expiration_minutes,
        )

        # --------------------------------------------------------
        # 3. Create ZIP
        # --------------------------------------------------------

        zip_path = self.create_function_app_zip()

        # --------------------------------------------------------
        # 4. DEPLOY ZIP
        #
        # THIS WAS MISSING FROM YOUR CURRENT FLOW.
        # --------------------------------------------------------

        deployment_result = self.deploy_zip(
            resource_group_name=
                resource_group_name,

            function_app_name=
                function_app_name,

            zip_path=
                zip_path,

            remote_build=
                remote_build,
        )

        # --------------------------------------------------------
        # 5. Restart
        # --------------------------------------------------------

        if restart_after_deployment:

            self.restart_function_app(
                resource_group_name,
                function_app_name,
            )

        # --------------------------------------------------------
        # 6. Verify
        # --------------------------------------------------------

        verification = (
            self.verify_function_app_deployment(
                resource_group_name,
                function_app_name,
            )
        )

        # --------------------------------------------------------
        # 7. Final result
        # --------------------------------------------------------

        hostname = verification.get(
            "hostname"
        )

        url = (
            f"https://{hostname}"
            if hostname
            else None
        )

        logger.info(
            "================================================"
        )

        logger.info(
            "FUNCTION APP DEPLOYMENT FINISHED"
        )

        logger.info(
            "Functions deployed: %d",
            verification.get(
                "function_count",
                0,
            ),
        )

        logger.info(
            "URL: %s",
            url,
        )

        logger.info(
            "================================================"
        )

        return {
            "status": "success",

            "deployment":
                deployment_result,

            "verification":
                verification,

            "hostname":
                hostname,

            "url":
                url,

            "zip_path":
                str(zip_path),

            "function_count":
                verification.get(
                    "function_count",
                    0,
                ),

            "functions":
                verification.get(
                    "function_names",
                    [],
                ),
        }

    # ============================================================
    # HOSTNAME
    # ============================================================

    def get_hostname(
        self,
        resource_group_name: str,
        function_app_name: str,
    ) -> str:

        function_app = (
            self.web_client
            .web_apps
            .get(
                resource_group_name,
                function_app_name,
            )
        )

        hostname = getattr(
            function_app,
            "default_host_name",
            None,
        )

        if not hostname:

            raise RuntimeError(
                "Function App default hostname "
                "could not be retrieved."
            )

        return str(hostname)

    # ============================================================
    # FUNCTION APP URL
    # ============================================================

    def get_function_app_url(
        self,
        resource_group_name: str,
        function_app_name: str,
    ) -> str:

        hostname = self.get_hostname(
            resource_group_name,
            function_app_name,
        )

        return f"https://{hostname}"

    # ============================================================
    # CLEANUP ZIP
    # ============================================================

    def cleanup_zip(
        self,
        zip_path: Optional[Path],
    ):

        if zip_path is None:
            return

        if not zip_path.exists():
            return

        logger.info(
            "Cleaning deployment ZIP: %s",
            zip_path,
        )

        try:

            zip_path.unlink()

        except Exception as exc:

            logger.warning(
                "Could not remove deployment ZIP: %s",
                exc,
            )

        logger.info(
            "Deployment ZIP cleanup completed."
        )


# =================================================================
# BACKWARD COMPATIBILITY WRAPPERS
# =================================================================

def create_app_service_plan(
    subscription_id: str,
    resource_group_name: str,
    plan_name: str,
    location: str,
):

    logger.info(
        "Flex Consumption hosting plan wrapper called."
    )

    return {
        "name":
            plan_name,

        "location":
            location,

        "resourceGroup":
            resource_group_name,

        "hostingModel":
            "FlexConsumption",

        "sku":
            "FC1",
    }


# =================================================================
# CREATE FUNCTION APP WRAPPER
# =================================================================

def create_function_app(
    subscription_id: str,
    resource_group_name: str,
    function_app_name: str,
    storage_account_name: str,
    storage_account_key: str | None,
    app_service_plan_name: str,
    location: str,
):

    logger.info(
        "Creating and deploying Function App through "
        "FunctionAppAzureService."
    )

    service = FunctionAppAzureService(
        subscription_id=subscription_id,
        function_app_source_dir="FunctionApp",
    )

    # ------------------------------------------------------------
    # 1. Create Function App
    # ------------------------------------------------------------

    service.create_function_app(
        resource_group_name=
            resource_group_name,

        function_app_name=
            function_app_name,

        storage_account_name=
            storage_account_name,

        location=
            location,

        runtime=
            "python",

        runtime_version=
            "3.11",
    )

    # ------------------------------------------------------------
    # 2. Deploy code
    #
    # THIS IS THE IMPORTANT CHANGE.
    # ------------------------------------------------------------

    deployment_result = service.deploy_function_app(
        resource_group_name=
            resource_group_name,

        function_app_name=
            function_app_name,

        storage_account_name=
            storage_account_name,

        storage_account_key=
            storage_account_key,

        table_name=
            "AppConfiguration",

        cache_expiration_minutes=
            10,

        remote_build=
            True,

        restart_after_deployment=
            True,
    )

    return deployment_result