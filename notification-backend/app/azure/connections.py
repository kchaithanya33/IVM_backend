
import logging
from typing import Any, Optional

from azure.core.exceptions import (
    HttpResponseError,
    ResourceNotFoundError,
)

from azure.identity import DefaultAzureCredential

from azure.mgmt.resource.resources import (
    ResourceManagementClient,
)


logger = logging.getLogger(__name__)


class AzureConnectionService:

    # ========================================================
    # API VERSION
    # ========================================================

    API_VERSION = "2016-06-01"

    # ========================================================
    # CONNECTION DEFINITIONS
    # ========================================================

    CONNECTIONS = {

        # ----------------------------------------------------
        # SERVICE AUTHENTICATION
        # ----------------------------------------------------

        "azuretables-1": {

            "connector": "azuretables",

            "authentication_type":
                "managed_identity",

            "user_authentication": False,
        },

        "azurequeues-1": {

            "connector": "azurequeues",

            "authentication_type":
                "managed_identity",

            "user_authentication": False,
        },

        # ----------------------------------------------------
        # OAUTH USER AUTHENTICATION
        # ----------------------------------------------------

        "office365-1": {

            "connector": "office365",

            "authentication_type":
                "oauth",

            "user_authentication": True,
        },

        "teams-1": {

            "connector": "teams",

            "authentication_type":
                "oauth",

            "user_authentication": True,
        },

        "sharepointonline-1": {

            "connector":
                "sharepointonline",

            "authentication_type":
                "oauth",

            "user_authentication": True,
        },
    }

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        subscription_id: str,
    ):

        self.subscription_id = (
            subscription_id
        )

        self.credential = (
            DefaultAzureCredential()
        )

        self.resource_client = (
            ResourceManagementClient(
                credential=self.credential,
                subscription_id=(
                    subscription_id
                ),
            )
        )

    # ========================================================
    # CONNECTION RESOURCE ID
    # ========================================================

    def get_connection_id(
        self,
        resource_group_name: str,
        connection_name: str,
    ) -> str:

        return (
            f"/subscriptions/"
            f"{self.subscription_id}"
            f"/resourceGroups/"
            f"{resource_group_name}"
            f"/providers/"
            f"Microsoft.Web/"
            f"connections/"
            f"{connection_name}"
        )

    # ========================================================
    # MANAGED API ID
    # ========================================================

    def get_managed_api_id(
        self,
        location: str,
        connector: str,
    ) -> str:

        return (
            f"/subscriptions/"
            f"{self.subscription_id}"
            f"/providers/"
            f"Microsoft.Web/"
            f"locations/"
            f"{location}"
            f"/managedApis/"
            f"{connector}"
        )

    # ========================================================
    # GET CONNECTION
    # ========================================================

    def get_connection(
        self,
        resource_group_name: str,
        connection_name: str,
    ) -> Optional[Any]:

        resource_id = (
            self.get_connection_id(
                resource_group_name,
                connection_name,
            )
        )

        try:

            return (
                self.resource_client
                .resources
                .get_by_id(
                    resource_id,
                    api_version=(
                        self.API_VERSION
                    ),
                )
            )

        except ResourceNotFoundError:

            return None

    # ========================================================
    # CONNECTION EXISTS
    # ========================================================

    def connection_exists(
        self,
        resource_group_name: str,
        connection_name: str,
    ) -> bool:

        return (
            self.get_connection(
                resource_group_name,
                connection_name,
            )
            is not None
        )

    # ========================================================
    # CREATE CONNECTION
    # ========================================================

    def create_connection(
        self,
        resource_group_name: str,
        location: str,
        connection_name: str,
    ):

        if connection_name not in (
            self.CONNECTIONS
        ):

            raise ValueError(
                f"Unsupported connection "
                f"'{connection_name}'."
            )

        definition = (
            self.CONNECTIONS[
                connection_name
            ]
        )

        connector = (
            definition[
                "connector"
            ]
        )

        authentication_type = (
            definition[
                "authentication_type"
            ]
        )

        api_id = (
            self.get_managed_api_id(
                location=location,
                connector=connector,
            )
        )

        logger.info(
            "Creating connection '%s' "
            "using connector '%s'.",
            connection_name,
            connector,
        )

        # ====================================================
        # MANAGED IDENTITY
        # ====================================================

        if (
            authentication_type
            == "managed_identity"
        ):

            parameters = {

                "location": location,

                "kind": "V1",

                "properties": {

                    "api": {
                        "id": api_id,
                    },

                    "displayName":
                        connection_name,

                    "connectionState":
                        "Enabled",

                    "alternativeParameterValues":
                        {},

                    "customParameterValues":
                        {},

                    "parameterValueSet": {

                        "name":
                            "managedIdentityAuth",

                        "values": {},
                    },
                },
            }

        # ====================================================
        # OAUTH
        # ====================================================

        elif (
            authentication_type
            == "oauth"
        ):

            parameters = {

                "location": location,

                "kind": "V1",

                "properties": {

                    "api": {
                        "id": api_id,
                    },

                    "displayName":
                        connection_name,

                    "connectionState":
                        "Enabled",

                    "alternativeParameterValues":
                        {},

                    "customParameterValues":
                        {},

                    "parameterValueSet":
                        {},
                },
            }

        else:

            raise RuntimeError(
                f"Unsupported authentication "
                f"type '{authentication_type}'."
            )

        resource_id = (
            self.get_connection_id(
                resource_group_name,
                connection_name,
            )
        )

        try:

            operation = (
                self.resource_client
                .resources
                .begin_create_or_update_by_id(
                    resource_id,
                    api_version=(
                        self.API_VERSION
                    ),
                    parameters=parameters,
                )
            )

            result = (
                operation.result()
            )

            logger.info(
                "Connection '%s' created "
                "successfully.",
                connection_name,
            )

            return result

        except HttpResponseError as exc:

            raise RuntimeError(
                f"Failed to create connection "
                f"'{connection_name}': {exc}"
            ) from exc

    # ========================================================
    # NORMALIZE PROPERTIES
    # ========================================================

    @staticmethod
    def _normalize_properties(
        connection: Any,
    ) -> dict:

        properties = getattr(
            connection,
            "properties",
            None,
        )

        if properties is None:

            return {}

        if hasattr(
            properties,
            "as_dict",
        ):

            try:

                return properties.as_dict()

            except Exception:

                pass

        if isinstance(
            properties,
            dict,
        ):

            return properties

        return {}

    # ========================================================
    # CHECK ERROR STATUS
    # ========================================================

    @staticmethod
    def _has_error(
        properties: dict,
    ) -> bool:

        statuses = (
            properties.get(
                "statuses"
            )
            or []
        )

        for item in statuses:

            if hasattr(
                item,
                "as_dict",
            ):

                try:

                    item = item.as_dict()

                except Exception:

                    continue

            if not isinstance(
                item,
                dict,
            ):

                continue

            status = (
                item.get(
                    "status"
                )
            )

            if status:

                normalized = (
                    str(status)
                    .strip()
                    .lower()
                )

                if normalized in {

                    "error",

                    "failed",

                    "failure",

                    "unauthorized",

                    "notauthenticated",

                    "not authenticated",
                }:

                    return True

            if item.get("error"):

                return True

        return False

    # ========================================================
    # GET CONNECTION STATUS
    # ========================================================

    def get_connection_state(
        self,
        resource_group_name: str,
        connection_name: str,
    ) -> dict:

        connection = (
            self.get_connection(
                resource_group_name,
                connection_name,
            )
        )

        if not connection:

            return {

                "exists": False,

                "authenticated": False,

                "connection_state":
                    None,

                "status":
                    None,

                "authentication_required":
                    False,

                "message":
                    "Connection does not exist.",
            }

        properties = (
            self._normalize_properties(
                connection
            )
        )

        connection_state = (
            properties.get(
                "connectionState"
            )
        )

        statuses = (
            properties.get(
                "statuses"
            )
            or []
        )

        status_value = None

        if statuses:

            first = statuses[0]

            if hasattr(
                first,
                "as_dict",
            ):

                try:

                    first = (
                        first.as_dict()
                    )

                except Exception:

                    first = {}

            if isinstance(
                first,
                dict,
            ):

                status_value = (
                    first.get(
                        "status"
                    )
                )

        has_error = (
            self._has_error(
                properties
            )
        )

        definition = (
            self.CONNECTIONS[
                connection_name
            ]
        )

        authentication_type = (
            definition[
                "authentication_type"
            ]
        )

        # ====================================================
        # MANAGED IDENTITY
        # ====================================================

        if (
            authentication_type
            == "managed_identity"
        ):

            authenticated = (
                connection_state
                == "Enabled"
                and not has_error
            )

            authentication_required = False

        # ====================================================
        # OAUTH
        # ====================================================

        else:

            authenticated_user = (
                properties.get(
                    "authenticatedUser"
                )
            )

            authenticated = (
                connection_state
                == "Enabled"
                and not has_error
                and bool(
                    authenticated_user
                )
            )

            authentication_required = (
                not authenticated
            )

        if authenticated:

            message = (
                "Connection exists and "
                "is authenticated."
            )

        elif authentication_required:

            message = (
                "Connection exists but "
                "OAuth authentication is required."
            )

        else:

            message = (
                "Connection exists but "
                "is not ready."
            )

        return {

            "exists": True,

            "authenticated":
                authenticated,

            "connection_state":
                connection_state,

            "status":
                status_value,

            "authentication_required":
                authentication_required,

            "message":
                message,
        }

    # ========================================================
    # CHECK ALL
    # ========================================================

    def check_all_connections(
        self,
        resource_group_name: str,
    ) -> list[dict]:

        results = []

        for name in (
            self.CONNECTIONS
        ):

            definition = (
                self.CONNECTIONS[
                    name
                ]
            )

            state = (
                self.get_connection_state(
                    resource_group_name,
                    name,
                )
            )

            results.append({

                "name":
                    name,

                "connector":
                    definition[
                        "connector"
                    ],

                "authentication_type":
                    definition[
                        "authentication_type"
                    ],

                **state,
            })

        return results
