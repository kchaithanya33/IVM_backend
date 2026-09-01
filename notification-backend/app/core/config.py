import os
from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# LOAD .ENV
# ============================================================

# Project root:
# notification-backend/
BASE_DIR = Path(__file__).resolve().parents[2]

ENV_FILE = BASE_DIR / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


# ============================================================
# HELPER
# ============================================================

def get_env(
    name: str,
    default: str | None = None,
    required: bool = False,
) -> str | None:
    """
    Read an environment variable.

    Args:
        name: Environment variable name.
        default: Default value if not present.
        required: If True, raise an error when missing.

    Returns:
        Environment variable value.
    """

    value = os.getenv(name, default)

    if required and not value:
        raise ValueError(
            f"Required environment variable '{name}' "
            f"is not configured."
        )

    return value


# ============================================================
# SETTINGS
# ============================================================

class Settings:
    """
    Central application configuration.

    All environment-specific values should be accessed
    through this class instead of calling os.getenv()
    throughout the application.
    """

    # ========================================================
    # APPLICATION
    # ========================================================

    app_name: str = get_env(
        "APP_NAME",
        "Notification Backend",
    )

    app_environment: str = get_env(
        "APP_ENVIRONMENT",
        "development",
    )

    debug: bool = (
        get_env("DEBUG", "false").lower()
        in ("true", "1", "yes")
    )

    host: str = get_env(
        "HOST",
        "0.0.0.0",
    )

    port: int = int(
        get_env(
            "PORT",
            "8000",
        )
    )

    # ========================================================
    # AZURE
    # ========================================================

    azure_tenant_id: str | None = get_env(
        "AZURE_TENANT_ID"
    )

    azure_client_id: str | None = get_env(
        "AZURE_CLIENT_ID"
    )

    azure_client_secret: str | None = get_env(
        "AZURE_CLIENT_SECRET"
    )

    azure_subscription_id: str | None = get_env(
        "AZURE_SUBSCRIPTION_ID"
    )

    # ========================================================
    # RESOURCE GROUP
    # ========================================================

    azure_resource_group: str | None = get_env(
        "AZURE_RESOURCE_GROUP"
    )

    azure_location: str = get_env(
        "AZURE_LOCATION",
        "canadacentral",
    )

    # ========================================================
    # STORAGE ACCOUNT
    # ========================================================

    storage_account_name: str | None = get_env(
        "STORAGE_ACCOUNT_NAME"
    )

    storage_account_key: str | None = get_env(
        "STORAGE_ACCOUNT_KEY"
    )

    storage_connection_string: str | None = get_env(
        "AZURE_STORAGE_CONNECTION_STRING"
    )

    # ========================================================
    # TABLE STORAGE
    # ========================================================

    app_configuration_table: str = get_env(
        "APP_CONFIGURATION_TABLE",
        "AppConfiguration",
    )

    email_recipient_configuration_table: str = get_env(
        "EMAIL_RECIPIENT_CONFIGURATION_TABLE",
        "EmailRecipientConfiguration",
    )

    notification_configuration_table: str = get_env(
        "NOTIFICATION_CONFIGURATION_TABLE",
        "NotificationConfiguration",
    )

    notification_templates_table: str = get_env(
        "NOTIFICATION_TEMPLATES_TABLE",
        "NotificationTemplates",
    )

    teams_recipient_configuration_table: str = get_env(
        "TEAMS_RECIPIENT_CONFIGURATION_TABLE",
        "TeamsRecipientConfiguration",
    )

    notification_logs_table: str = get_env(
        "NOTIFICATION_LOGS_TABLE",
        "NotificationLogs",
    )

    notification_status_table: str = get_env(
        "NOTIFICATION_STATUS_TABLE",
        "NotificationStatus",
    )

    # ========================================================
    # QUEUE STORAGE
    # ========================================================

    followup_queue_name: str = get_env(
        "FOLLOWUP_QUEUE_NAME",
        "taskreminder",
    )

    azure_queue_connection_string: str | None = get_env(
        "AZURE_QUEUE_CONNECTION_STRING"
    )

    # ========================================================
    # ARM TEMPLATE
    # ========================================================

    notification_arm_template: str = get_env(
        "NOTIFICATION_ARM_TEMPLATE",
        str(
            BASE_DIR
            / "arm"
            / "notification.json"
        ),
    )

    # ========================================================
    # NOTIFICATION LOGIC APPS
    # ========================================================

    logic_app_name: str = get_env(
        "LOGIC_APP_NAME",
        "notification-logic-chai",
    )

    completion_logic_app_name: str = get_env(
        "COMPLETION_LOGIC_APP_NAME",
        "notification-completion-logic-chai",
    )

    notification_followup_logic_app_name: str = get_env(
        "NOTIFICATION_FOLLOWUP_LOGIC_APP_NAME",
        "notification-followup-logic-chai",
    )

    # ========================================================
    # AZURE API CONNECTIONS
    # ========================================================

    azure_tables_connection_name: str = get_env(
        "AZURE_TABLES_CONNECTION_NAME",
        "azuretables-1",
    )

    azure_queues_connection_name: str = get_env(
        "AZURE_QUEUES_CONNECTION_NAME",
        "azurequeues-1",
    )

    office365_connection_name: str = get_env(
        "OFFICE365_CONNECTION_NAME",
        "office365-1",
    )

    teams_connection_name: str = get_env(
        "TEAMS_CONNECTION_NAME",
        "teams-1",
    )

    # ========================================================
    # CALLBACK
    # ========================================================

    callback_secret_key: str = get_env(
        "CALLBACK_SECRET_KEY",
        "",
    )

    # ========================================================
    # SECURITY
    # ========================================================

    secret_key: str = get_env(
        "SECRET_KEY",
        "",
    )

    # ========================================================
    # LOGGING
    # ========================================================

    log_level: str = get_env(
        "LOG_LEVEL",
        "INFO",
    )

    # ========================================================
    # CORS
    # ========================================================

    cors_origins: str = get_env(
        "CORS_ORIGINS",
        "*",
    )

    # ========================================================
    # CACHE
    # ========================================================

    cache_expiration_minutes: int = int(
        get_env(
            "CACHE_EXPIRATION_MINUTES",
            "10",
        )
    )


# ============================================================
# GLOBAL SETTINGS INSTANCE
# ============================================================

settings = Settings()