
import logging

from app.azure.connections import (
    AzureConnectionService,
)

from app.schemas.connections import (
    ConnectionSetupRequest,
    ConnectionSetupResponse,
    ConnectionStatus,
)


logger = logging.getLogger(__name__)


class ConnectionSetupService:

    # ========================================================
    # ORDER
    # ========================================================

    CONNECTION_ORDER = [

        "azuretables-1",

        "azurequeues-1",

        "office365-1",

        "teams-1",

        "sharepointonline-1",
    ]

    # ========================================================
    # SETUP
    # ========================================================

    def setup(
        self,
        request: ConnectionSetupRequest,
    ) -> ConnectionSetupResponse:

        logger.info(
            "================================================"
        )

        logger.info(
            "STARTING CONNECTION SETUP"
        )

        logger.info(
            "================================================"
        )

        azure = (
            AzureConnectionService(
                subscription_id=(
                    request.subscription_id
                )
            )
        )

        results = []

        # ====================================================
        # PROCESS ONE CONNECTION AT A TIME
        # ====================================================

        for connection_name in (
            self.CONNECTION_ORDER
        ):

            definition = (
                azure.CONNECTIONS[
                    connection_name
                ]
            )

            logger.info(
                "Checking connection '%s'...",
                connection_name,
            )

            # ------------------------------------------------
            # CHECK
            # ------------------------------------------------

            state = (
                azure.get_connection_state(
                    request.resource_group_name,
                    connection_name,
                )
            )

            # ------------------------------------------------
            # CREATE IF MISSING
            # ------------------------------------------------

            if not state["exists"]:

                logger.info(
                    "Connection '%s' does not exist.",
                    connection_name,
                )

                logger.info(
                    "Creating connection '%s'...",
                    connection_name,
                )

                azure.create_connection(
                    resource_group_name=(
                        request.resource_group_name
                    ),
                    location=(
                        request.location
                    ),
                    connection_name=(
                        connection_name
                    ),
                )

                # --------------------------------------------
                # IMPORTANT:
                # Check Azure again after creation.
                # --------------------------------------------

                state = (
                    azure.get_connection_state(
                        request.resource_group_name,
                        connection_name,
                    )
                )

            # ------------------------------------------------
            # BUILD STATUS
            # ------------------------------------------------

            status = (
                ConnectionStatus(

                    name=connection_name,

                    connector=(
                        definition[
                            "connector"
                        ]
                    ),

                    authentication_type=(
                        definition[
                            "authentication_type"
                        ]
                    ),

                    exists=(
                        state["exists"]
                    ),

                    authenticated=(
                        state[
                            "authenticated"
                        ]
                    ),

                    connection_state=(
                        state[
                            "connection_state"
                        ]
                    ),

                    status=(
                        state[
                            "status"
                        ]
                    ),

                    authentication_required=(
                        state[
                            "authentication_required"
                        ]
                    ),

                    message=(
                        state[
                            "message"
                        ]
                    ),
                )
            )

            results.append(
                status
            )

            # =================================================
            # MANAGED IDENTITY CONNECTIONS
            # =================================================
            #
            # azuretables-1 and azurequeues-1
            #
            # NO USER INPUT.
            #
            # =================================================

            if not definition[
                "user_authentication"
            ]:

                if not state[
                    "authenticated"
                ]:

                    raise RuntimeError(
                        f"Connection "
                        f"'{connection_name}' "
                        "could not be authenticated "
                        "using service authentication."
                    )

                logger.info(
                    "Connection '%s' ready. "
                    "Moving to next connection.",
                    connection_name,
                )

                continue

            # =================================================
            # OAUTH CONNECTIONS
            # =================================================

            if state[
                "authenticated"
            ]:

                logger.info(
                    "OAuth connection '%s' "
                    "already authenticated.",
                    connection_name,
                )

                continue

            # ------------------------------------------------
            # STOP AND ASK USER TO AUTHENTICATE
            # ------------------------------------------------

            logger.info(
                "OAuth authentication required "
                "for '%s'.",
                connection_name,
            )

            return (
                ConnectionSetupResponse(

                    status=(
                        "authentication_required"
                    ),

                    message=(
                        f"Connection "
                        f"'{connection_name}' "
                        "requires user authentication. "
                        "Please authenticate it and "
                        "call this API again."
                    ),

                    subscription_id=(
                        request.subscription_id
                    ),

                    resource_group_name=(
                        request.resource_group_name
                    ),

                    connections=results,

                    pending_connection=(
                        connection_name
                    ),

                    authentication_required=True,

                    all_connections_ready=False,
                )
            )

        # ====================================================
        # EVERYTHING READY
        # ====================================================

        logger.info(
            "================================================"
        )

        logger.info(
            "ALL CONNECTIONS ARE READY"
        )

        logger.info(
            "================================================"
        )

        return (
            ConnectionSetupResponse(

                status="success",

                message=(
                    "All five API connections "
                    "exist and are authenticated."
                ),

                subscription_id=(
                    request.subscription_id
                ),

                resource_group_name=(
                    request.resource_group_name
                ),

                connections=results,

                pending_connection=None,

                authentication_required=False,

                all_connections_ready=True,
            )
        )
