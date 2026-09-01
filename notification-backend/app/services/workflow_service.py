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
        ]

        # ====================================================
        # QUEUES
        # ====================================================
        #
        # Queue names are also managed internally.
        #

        queue_names = [

            "scopingschedulequeue",

            "authscan00",

            "taskreminder",
        ]

        # ====================================================
        # DEPLOYMENT
        # ====================================================

        deployment = NotificationDeployment(

            subscription_id=(
                request.subscription_id
            ),

            resource_group_name=(
                request.resource_group_name
            ),

            resource_group_location=(
                request.resource_group_location
            ),

            storage_account_name=(
                request.storage_account_name
            ),

            storage_account_location=(
                request.storage_account_location
            ),

            function_app_name=(
                request.function_app_name
            ),

            table_names=(
                table_names
            ),

            queue_names=(
                queue_names
            ),
        )

        # ====================================================
        # EXECUTE DEPLOYMENT
        # ====================================================

        return deployment.deploy()