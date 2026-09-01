import logging
import time

from azure.core.exceptions import (
    HttpResponseError,
    ResourceNotFoundError,
)

from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential


logger = logging.getLogger(__name__)


class KeyVaultSecretManager:

    def __init__(
        self,
        key_vault_url: str,
        credential=None,
    ):

        self.key_vault_url = key_vault_url

        self.credential = (
            credential
            if credential is not None
            else DefaultAzureCredential()
        )

        self.client = SecretClient(
            vault_url=key_vault_url,
            credential=self.credential,
        )

    # ========================================================
    # SET SECRET
    # ========================================================

    def set_secret(
        self,
        secret_name: str,
        secret_value: str,
    ):

        if secret_value is None:
            raise ValueError(
                f"Secret value for '{secret_name}' "
                "cannot be None."
            )

        logger.info(
            "Setting Key Vault secret '%s'",
            secret_name,
        )

        return self.client.set_secret(
            secret_name,
            secret_value,
        )

    # ========================================================
    # SET QUALYS USERNAME
    # ========================================================

    def set_qualys_username(
        self,
        username: str,
    ):

        return self.set_secret(
            "QualysUsername",
            username,
        )

    # ========================================================
    # SET QUALYS PASSWORD
    # ========================================================

    def set_qualys_password(
        self,
        password: str,
    ):

        return self.set_secret(
            "QualysPassword",
            password,
        )

    # ========================================================
    # SET QUALYS BASE URL
    # ========================================================

    def set_qualys_base_url(
        self,
        base_url: str,
    ):

        return self.set_secret(
            "QualysBaseUrl",
            base_url,
        )

    # ========================================================
    # STORE ALL QUALYS SECRETS
    # ========================================================

    def store_qualys_secrets(
        self,
        username: str,
        password: str,
        base_url: str,
        retries: int = 6,
        retry_delay: int = 10,
    ):

        """
        Store the same three secrets used by deploy.sh:

            QualysUsername
            QualysPassword
            QualysBaseUrl

        RBAC propagation can take some time after the role
        assignment, so retry the operation.
        """

        last_exception = None

        for attempt in range(1, retries + 1):

            try:

                logger.info(
                    "Attempt %s/%s to store Qualys "
                    "secrets in Key Vault",
                    attempt,
                    retries,
                )

                self.set_qualys_username(
                    username
                )

                self.set_qualys_password(
                    password
                )

                self.set_qualys_base_url(
                    base_url
                )

                logger.info(
                    "All Qualys secrets stored successfully."
                )

                return

            except HttpResponseError as exc:

                last_exception = exc

                logger.warning(
                    "Unable to store Key Vault secrets "
                    "on attempt %s/%s: %s",
                    attempt,
                    retries,
                    exc,
                )

                if attempt < retries:

                    logger.info(
                        "Waiting %s seconds for RBAC "
                        "propagation...",
                        retry_delay,
                    )

                    time.sleep(
                        retry_delay
                    )

        raise RuntimeError(
            "Failed to store Qualys secrets in "
            "Key Vault after RBAC retry attempts."
        ) from last_exception

    # ========================================================
    # GET SECRET
    # ========================================================

    def get_secret(
        self,
        secret_name: str,
    ):

        try:

            secret = self.client.get_secret(
                secret_name
            )

            return secret.value

        except ResourceNotFoundError as exc:

            raise ValueError(
                f"Secret '{secret_name}' "
                "was not found in Key Vault."
            ) from exc

    # ========================================================
    # GET QUALYS CREDENTIALS
    # ========================================================

    def get_qualys_credentials(self):

        return {
            "username": self.get_secret(
                "QualysUsername"
            ),
            "password": self.get_secret(
                "QualysPassword"
            ),
            "base_url": self.get_secret(
                "QualysBaseUrl"
            ),
        }