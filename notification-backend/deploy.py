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
        # DEPLOYMENT COMPLETE
        # ====================================================
        #
        # IMPORTANT:
        #
        # Key Vault is not created or configured here.
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
                    self.function_app_plan_name
            },

            "tables":
                tables,

            "queues":
                queues,
        }