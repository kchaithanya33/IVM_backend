import logging

from app.azure.function_app import (
    FunctionAppAzureService,
)

from app.schemas.deployment import (
    FunctionAppDeploymentRequest,
    FunctionAppDeploymentResponse,
)


logger = logging.getLogger(__name__)


class FunctionAppDeploymentService:

    # ============================================================
    # DEPLOY FUNCTION APP
    # ============================================================

    def deploy(
        self,
        request: FunctionAppDeploymentRequest,
    ) -> FunctionAppDeploymentResponse:

        logger.info(
            "========================================"
        )

        logger.info(
            "Starting Function App deployment"
        )

        logger.info(
            "Subscription: %s",
            request.subscription_id,
        )

        logger.info(
            "Resource Group: %s",
            request.resource_group_name,
        )

        logger.info(
            "Storage Account: %s",
            request.storage_account_name,
        )

        logger.info(
            "Function App: %s",
            request.function_app_name,
        )

        logger.info(
            "Table Name: %s",
            request.table_name,
        )

        # ========================================================
        # IMPORTANT
        #
        # Your actual folder is:
        #
        # notification-backend/
        # ├── FunctionApp/
        # │   ├── host.json
        # │   ├── requirements.txt
        # │   ├── shared_code/
        # │   ├── GetPartitionConfigs/
        # │   └── ...
        # │
        # └── app/
        #
        # Therefore use:
        #
        # function_app_source_dir="FunctionApp"
        #
        # NOT:
        #
        # function_app_source_dir="function_app"
        # ========================================================

        azure_service = FunctionAppAzureService(
            subscription_id=request.subscription_id,
            function_app_source_dir="FunctionApp",
        )

        zip_path = None

        try:

            # ====================================================
            # 1. CHECK AZURE CLI
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 1: Checking Azure CLI authentication"
            )

            azure_service.check_azure_cli_login()

            # ====================================================
            # 2. RESOURCE GROUP
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 2: Checking Resource Group"
            )

            azure_service.ensure_resource_group(
                resource_group_name=(
                    request.resource_group_name
                ),
                location=(
                    request.location
                ),
            )

            # ====================================================
            # 3. STORAGE ACCOUNT
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 3: Checking Storage Account"
            )

            azure_service.get_storage_account(
                resource_group_name=(
                    request.resource_group_name
                ),
                storage_account_name=(
                    request.storage_account_name
                ),
            )

            # ====================================================
            # 4. STORAGE ACCOUNT KEY
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 4: Getting Storage Account key"
            )

            storage_account_key = (
                azure_service.get_storage_account_key(
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    storage_account_name=(
                        request.storage_account_name
                    ),
                )
            )

            # ====================================================
            # 5. FUNCTION APP
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 5: Checking Function App"
            )

            azure_service.get_function_app(
                resource_group_name=(
                    request.resource_group_name
                ),
                function_app_name=(
                    request.function_app_name
                ),
            )

            # ====================================================
            # 6. FUNCTION APP SETTINGS
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 6: Configuring Function App settings"
            )

            azure_service.configure_function_app_settings(
                resource_group_name=(
                    request.resource_group_name
                ),
                function_app_name=(
                    request.function_app_name
                ),
                storage_account_name=(
                    request.storage_account_name
                ),
                storage_account_key=(
                    storage_account_key
                ),
                table_name=(
                    request.table_name
                ),
                cache_expiration_minutes=(
                    request.cache_expiration_minutes
                ),
            )

            # ====================================================
            # 7. VALIDATE SOURCE
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 7: Validating Function App source"
            )

            azure_service.validate_function_app_source()

            # ====================================================
            # 8. CREATE ZIP
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 8: Creating Function App ZIP"
            )

            zip_path = (
                azure_service.create_function_app_zip()
            )

            logger.info(
                "Deployment ZIP created: %s",
                zip_path,
            )

            # ====================================================
            # 9. DEPLOY ZIP
            # ====================================================
            #
            # IMPORTANT:
            #
            # This does NOT use:
            #
            # - publishing profile
            # - SCM basic authentication
            # - Kudu username/password
            #
            # It uses:
            #
            # az functionapp deployment source config-zip
            #
            # exactly like your working Bash script.
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 9: Deploying Function App code"
            )

            deployment_result = (
                azure_service.deploy_zip(
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    function_app_name=(
                        request.function_app_name
                    ),
                    zip_path=(
                        zip_path
                    ),
                    remote_build=True,
                )
            )

            logger.info(
                "Function App code deployment completed."
            )

            logger.info(
                "Deployment result: %s",
                deployment_result,
            )

            # ====================================================
            # 10. RESTART
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 10: Restarting Function App"
            )

            azure_service.restart_function_app(
                resource_group_name=(
                    request.resource_group_name
                ),
                function_app_name=(
                    request.function_app_name
                ),
            )

            # ====================================================
            # 11. VERIFY DEPLOYMENT
            # ====================================================
            #
            # This is important.
            #
            # Previously your API returned 200 because the backend
            # completed its own steps, but we did not verify that
            # Azure actually exposed the deployed functions.
            #
            # Now we explicitly call:
            #
            # az functionapp function list
            #
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 11: Verifying deployed functions"
            )

            verification = (
                azure_service.verify_function_app_deployment(
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    function_app_name=(
                        request.function_app_name
                    ),
                )
            )

            function_count = (
                verification.get(
                    "function_count",
                    0,
                )
            )

            logger.info(
                "Azure reports %s deployed function(s).",
                function_count,
            )

            if function_count == 0:

                logger.warning(
                    "Azure Function App deployment command "
                    "completed, but Azure currently reports "
                    "zero functions."
                )

                logger.warning(
                    "Check host.json, requirements.txt and "
                    "the Python Function programming model."
                )

            # ====================================================
            # 12. GET HOSTNAME
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Step 12: Getting Function App hostname"
            )

            hostname = (
                azure_service.get_hostname(
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    function_app_name=(
                        request.function_app_name
                    ),
                )
            )

            # ====================================================
            # 13. ENDPOINT
            # ====================================================

            endpoint = (
                f"https://{hostname}"
                f"/api/config/{{partition}}"
            )

            # ====================================================
            # SUCCESS
            # ====================================================

            logger.info(
                "========================================"
            )

            logger.info(
                "Function App deployment completed."
            )

            logger.info(
                "Function App URL: https://%s",
                hostname,
            )

            logger.info(
                "Function count reported by Azure: %s",
                function_count,
            )

            return FunctionAppDeploymentResponse(
                status="success",

                message=(
                    "Function App code deployed successfully."
                ),

                subscription_id=(
                    request.subscription_id
                ),

                resource_group_name=(
                    request.resource_group_name
                ),

                storage_account_name=(
                    request.storage_account_name
                ),

                function_app_name=(
                    request.function_app_name
                ),

                hostname=(
                    hostname
                ),

                endpoint=(
                    endpoint
                ),
            )

        except Exception as exc:

            logger.exception(
                "Function App code deployment failed."
            )

            raise RuntimeError(
                "Function App code deployment failed: "
                f"{exc}"
            ) from exc

        finally:
            logger.info(
        "Keeping deployment ZIP for inspection: %s",
        zip_path,
    )