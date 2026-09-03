import logging
import azure.functions as func
import json
import requests
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    QualysScanFetch - HTTP Trigger Azure Function

    This function fetches scan results from Qualys by scan ID or scan reference.

    Input:
      - scan_id parameter in query string or JSON body
      - scan_ref parameter (alternative to scan_id) for authentication scan results
      - output_format (optional): 'json_extended' or 'xml' (defaults to JSON Extended)

    Output:
      JSON or XML response with scan results in Qualys format
    """

    logging.info('QualysScanFetch function processing a request.')

    try:

        # ============================================================
        # GET REQUEST PARAMETERS
        # ============================================================

        # Get scan_id or scan_ref from query parameters or request body
        scan_id = req.params.get('scan_id')
        scan_ref = req.params.get('scan_ref')
        output_format = req.params.get(
            'output_format',
            'json_extended'
        )

        if not scan_id and not scan_ref:
            req_body = req.get_json()

            scan_id = req_body.get('scan_id')
            scan_ref = req_body.get('scan_ref')
            output_format = req_body.get(
                'output_format',
                'json_extended'
            )

        # ============================================================
        # VALIDATE REQUIRED PARAMETERS
        # ============================================================

        if not scan_id and not scan_ref:
            return func.HttpResponse(
                json.dumps({
                    "error":
                        "Missing required parameter: either "
                        "'scan_id' or 'scan_ref' must be provided"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # ============================================================
        # GET QUALYS CREDENTIALS FROM AZURE KEY VAULT
        # ============================================================

        logging.info(
            "Retrieving Qualys credentials from Azure Key Vault."
        )

        # Key Vault URL
        key_vault_url = (
            "https://kv-qualys-security-001.vault.azure.net/"
        )

        # Create credential using Function App Managed Identity
        credential = DefaultAzureCredential()

        # Create Key Vault client
        secret_client = SecretClient(
            vault_url=key_vault_url,
            credential=credential
        )

        # ------------------------------------------------------------
        # Retrieve Qualys username
        # ------------------------------------------------------------

        qualys_username = (
            secret_client
            .get_secret("QualysUsername")
            .value
        )

        # ------------------------------------------------------------
        # Retrieve Qualys password
        # ------------------------------------------------------------

        qualys_password = (
            secret_client
            .get_secret("QualysPassword")
            .value
        )

        # ------------------------------------------------------------
        # Retrieve Qualys API URL
        # ------------------------------------------------------------

        qualys_api_url = (
            secret_client
            .get_secret("QualysBaseUrl")
            .value
        )

        # ------------------------------------------------------------
        # Safe logging
        # DO NOT log username/password values
        # ------------------------------------------------------------

        logging.info(
            "=== QUALYS CREDENTIAL CHECK ==="
        )

        logging.info(
            f"Qualys Username: "
            f"{'SET' if qualys_username else 'NOT SET'}"
        )

        logging.info(
            f"Qualys Password: "
            f"{'SET' if qualys_password else 'NOT SET'}"
        )

        logging.info(
            f"Qualys API URL: "
            f"{qualys_api_url}"
        )

        # ============================================================
        # LOG SCAN INFORMATION
        # ============================================================

        # Log the scan ID or scan reference we're checking
        # but never log credentials

        if scan_id:
            logging.info(
                f"Fetching results for Qualys scan ID: "
                f"{scan_id}, format: {output_format}"
            )
        else:
            logging.info(
                f"Fetching results for Qualys scan reference: "
                f"{scan_ref}, format: {output_format}"
            )

        # ============================================================
        # BUILD QUALYS FETCH URL
        # ============================================================

        fetch_url = (
            f"{qualys_api_url}/api/2.0/fo/scan/"
        )

        params = {
            "action": "fetch",
            "output_format": output_format
        }

        # Add either scan_id or scan_ref to the parameters
        if scan_id:
            params["scan_id"] = scan_id
        else:
            params["scan_ref"] = scan_ref

        # ============================================================
        # MAKE QUALYS API REQUEST
        # ============================================================

        response = requests.get(
            fetch_url,
            params=params,
            auth=(
                qualys_username,
                qualys_password
            ),
            headers={
                "X-Requested-With": "IVM Automation"
            }
        )

        # ============================================================
        # HANDLE QUALYS API ERRORS
        # ============================================================

        if response.status_code != 200:

            logging.error(
                f"Qualys API error: "
                f"Status code {response.status_code}, "
                f"Response: {response.text}"
            )

            return func.HttpResponse(
                json.dumps({
                    "error":
                        f"Qualys API error: "
                        f"Status code {response.status_code}"
                }),
                status_code=500,
                mimetype="application/json"
            )

        # ============================================================
        # RETURN QUALYS RESPONSE
        # ============================================================

        content_type = (
            "application/json"
            if output_format.lower() == "json_extended"
            else "application/xml"
        )

        return func.HttpResponse(
            response.text,
            status_code=200,
            mimetype=content_type
        )

    # ================================================================
    # GENERAL ERROR HANDLING
    # ================================================================

    except Exception as e:

        logging.exception(
            f"Error in QualysScanFetch function: {str(e)}"
        )

        return func.HttpResponse(
            json.dumps({
                "error":
                    f"Internal server error: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )