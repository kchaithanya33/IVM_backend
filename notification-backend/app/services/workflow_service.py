from deploy import NotificationDeployment


class WorkflowService:

    def deploy(self, request):

        # ====================================================
        # TABLES
        # ====================================================
        #
        # Table names are managed internally.
        # User does not need to provide them.
        #

        table_names = [

            # ------------------------------------------------
            # Notification tables
            # ------------------------------------------------

            "AppConfiguration",

            "EmailRecipientConfiguration",

            "NotificationConfiguration",

            "TeamsRecipientConfiguration",

            "NotificationTemplates",

            # ------------------------------------------------
            # Workflow tables
            # ------------------------------------------------

            "Cycles",

            "NotificationLogs",

            "NotificationStatus",

            # ------------------------------------------------
            # Auth Scan tables
            # ------------------------------------------------

            "AuthScanResults",
             # Scan Log tables
    "ScanStatusLog",
    "ScanCompletionLog",
            
        ]

        # ====================================================
        # QUEUES
        # ====================================================
        #
        # Queue names are managed internally.
        # User does not need to provide them.
        #

        queue_names = [

            # ------------------------------------------------
            # Existing queues
            # ------------------------------------------------

            "scopingschedulequeue",

            "authscan00",

            "taskreminder",

            # ------------------------------------------------
            # Qualys / Vulnerability Scan queues
            # ------------------------------------------------

            "qualysscanstatusqueue",

            "vulnscan00",

            "authscanresultshandlerqueue",
        ]

        # ====================================================
        # DEPLOYMENT
        # ====================================================

        deployment = NotificationDeployment(

            # ------------------------------------------------
            # Azure Subscription
            # ------------------------------------------------

            subscription_id=(
                request.subscription_id
            ),

            # ------------------------------------------------
            # Resource Group
            # ------------------------------------------------

            resource_group_name=(
                request.resource_group_name
            ),

            resource_group_location=(
                request.resource_group_location
            ),

            # ------------------------------------------------
            # Storage Account
            # ------------------------------------------------

            storage_account_name=(
                request.storage_account_name
            ),

            storage_account_location=(
                request.storage_account_location
            ),

            # ------------------------------------------------
            # Function App
            # ------------------------------------------------

            function_app_name=(
                request.function_app_name
            ),

            # ------------------------------------------------
            # Storage Tables
            # ------------------------------------------------

            table_names=(
                table_names
            ),

            # ------------------------------------------------
            # Storage Queues
            # ------------------------------------------------

            queue_names=(
                queue_names
            ),
        )

        # ====================================================
        # EXECUTE DEPLOYMENT
        # ====================================================

        return deployment.deploy()