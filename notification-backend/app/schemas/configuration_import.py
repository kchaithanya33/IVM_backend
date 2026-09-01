from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# COMMON CONFIGURATION
# ============================================================

class ConfigurationValue(BaseModel):

    # User provides ONLY the value
    Value: Any

    # Only used for BusinessDay / WorkingDayandHour
    region: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    businessDays: Optional[Any] = None


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

class EmailConfigurationValue(BaseModel):

    # User provides ONLY the value
    Value: str


# ============================================================
# NOTIFICATION CONFIGURATION
# ============================================================

class NotificationConfigurationValue(BaseModel):

    # User provides these values
    NotificationChannels: str
    RecipientEmail: str
    TeamsGroup: str


# ============================================================
# TEAMS CONFIGURATION
# ============================================================

class TeamsConfigurationValue(BaseModel):

    # User provides ONLY the value
    Value: str


# ============================================================
# COMPLETE DEPLOYMENT REQUEST
# ============================================================

class ConfigurationDeploymentRequest(BaseModel):

    resource_group_name: str

    storage_account_name: str

    app_configuration: List[
        ConfigurationValue
    ] = Field(
        default_factory=list
    )

    email_configuration: List[
        EmailConfigurationValue
    ] = Field(
        default_factory=list
    )

    notification_configuration: List[
        NotificationConfigurationValue
    ] = Field(
        default_factory=list
    )

    teams_configuration: List[
        TeamsConfigurationValue
    ] = Field(
        default_factory=list
    )