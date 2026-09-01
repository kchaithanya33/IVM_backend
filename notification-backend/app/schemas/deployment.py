from pydantic import BaseModel, Field


class FunctionAppDeploymentRequest(BaseModel):
    subscription_id: str = Field(..., min_length=1)

    resource_group_name: str = Field(..., min_length=1)

    location: str = Field(..., min_length=1)

    storage_account_name: str = Field(..., min_length=3)

    function_app_name: str = Field(..., min_length=1)

    table_name: str = Field(
        default="AppConfiguration",
        min_length=1,
    )

    cache_expiration_minutes: int = Field(
        default=10,
        ge=1,
    )


class FunctionAppDeploymentResponse(BaseModel):
    status: str

    message: str

    subscription_id: str

    resource_group_name: str

    storage_account_name: str

    function_app_name: str

    hostname: str | None = None

    endpoint: str | None = None