import logging
import azure.functions as func
import json
import requests
import os
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    QualysScanStatus - HTTP Trigger Azure Function
    
    This function checks the status of a Qualys scan by its scan ID or scan reference.
    It replaces the direct HTTP call with managed identity that was previously used.
    
    Input: scan_id or scan_ref parameter in query string or JSON body
    Output: Simple JSON response with just the scan status
    """
    logging.info('QualysScanStatus function processing a request.')
    
    try:
        # Get scan parameters from query parameters or request body
        scan_id = req.params.get('scan_id')
        scan_ref = req.params.get('scan_ref')
        
        if not scan_id and not scan_ref:
            try:
                req_body = req.get_json()
                scan_id = req_body.get('scan_id')
                scan_ref = req_body.get('scan_ref')
            except ValueError:
                pass
        
        # Validate required parameters
        if not scan_id and not scan_ref:
            return func.HttpResponse(
                json.dumps({
                    "error": "Missing required parameter 'scan_id' or 'scan_ref'"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # ============================================================
        # GET QUALYS CREDENTIALS FROM AZURE KEY VAULT
        # ============================================================

        # Get Key Vault URL from Function App settings
        key_vault_url = "https://key-vault-IVM.vault.azure.net/"

        if not key_vault_url:
            raise ValueError(
                "KEY_VAULT_URL is not configured in Function App settings."
            )

        logging.info(
            f"Key Vault URL configured: {key_vault_url}"
        )

        # Use Function App Managed Identity
        credential = DefaultAzureCredential()

        secret_client = SecretClient(
            vault_url=key_vault_url,
            credential=credential
        )

        # Retrieve Qualys username
        qualys_username = (
            secret_client
            .get_secret("QualysUsername")
            .value
        )

        # Retrieve Qualys password
        qualys_password = (
            secret_client
            .get_secret("QualysPassword")
            .value
        )

        # Retrieve Qualys base URL
        qualys_api_url = (
            secret_client
            .get_secret("QualysBaseUrl")
            .value
        )

        # Log only safe information
        # NEVER log username/password values
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
        # EXISTING QUALYS LOGIC - UNCHANGED
        # ============================================================

        # Using the same header as in QualysScanFetch
        headers = {
            "X-Requested-With": "IVM Automation"
        }
        
        # Build the URL for the scan status check
        status_check_url = f"{qualys_api_url}/api/2.0/fo/scan/"
        params = {
            "action": "list"
        }
        
        # Determine which parameter to use based on what was provided
        if scan_ref:
            # If scan_ref was provided, use it directly
            logging.info(
                f"Checking status for Qualys scan REF: {scan_ref}"
            )
            params["scan_ref"] = scan_ref
        else:
            # If scan_id was provided, use it
            logging.info(
                f"Checking status for Qualys scan ID: {scan_id}"
            )
            # Note: API might expect scan references instead of IDs, so this might need adaptation
            params["scan_id"] = scan_id
        
        # Add enhanced logging for troubleshooting
        logging.info(
            f"API URL: {status_check_url}"
        )
        logging.info(
            f"API parameters: {params}"
        )

        # Make the API request
        try:
            response = requests.get(
                status_check_url,
                params=params,
                auth=(qualys_username, qualys_password),
                headers=headers,
                verify=True,
                timeout=30
            )
            
            # Log response status for debugging
            logging.info(
                f"Response status code: {response.status_code}"
            )

            if response.status_code != 200:
                logging.error(
                    f"Error response: {response.text[:500]}"
                )
                
        except requests.RequestException as req_ex:
            logging.error(
                f"Request exception: {str(req_ex)}"
            )
            return func.HttpResponse(
                json.dumps({
                    "error": f"API request failed: {str(req_ex)}"
                }),
                status_code=500,
                mimetype="application/json"
            )

        # Handle API errors
        if response.status_code != 200:
            logging.error(
                f"Qualys API error: Status code "
                f"{response.status_code}, "
                f"Response: {response.text[:1000]}"
            )

            return func.HttpResponse(
                json.dumps({
                    "error":
                        f"Qualys API error: "
                        f"Status code {response.status_code}",
                    "details":
                        response.text[:500]
                        if response.text
                        else "No response body"
                }),
                status_code=500,
                mimetype="application/json"
            )
        
        # Parse the XML response to extract just the status value
        try:
            # Log first part of response for debugging (limited to avoid sensitive data)
            logging.info(
                f"Received response from Qualys API "
                f"with length: {len(response.text)}"
            )

            logging.info(
                f"Response preview: "
                f"{response.text[:200]}..."
            )
            
            root = ET.fromstring(response.text)
            
            # Find the scan in the response
            scan_element = root.find(".//SCAN")

            if scan_element is None:
                logging.warning(
                    "No SCAN element found in response"
                )

                return func.HttpResponse(
                    json.dumps({
                        "error":
                            "No scan information found in response",
                        "status":
                            "Unknown"
                    }),
                    status_code=404,
                    mimetype="application/json"
                )
                
            # Extract the status
            status_element = scan_element.find(
                ".//STATUS/STATE"
            )
            
            if status_element is not None:
                scan_status = status_element.text

                logging.info(
                    f"Successfully extracted scan status: "
                    f"{scan_status}"
                )

                # Get additional scan information if available
                scan_ref = (
                    scan_element.find("REF").text
                    if scan_element.find("REF") is not None
                    else None
                )
                
                # Handle CDATA sections properly
                title_element = scan_element.find("TITLE")

                scan_title = (
                    title_element.text
                    if title_element is not None
                    else None
                )

                # Strip CDATA markers if present
                if (
                    scan_title
                    and scan_title.startswith("<![CDATA[")
                    and scan_title.endswith("]]>")
                ):
                    scan_title = scan_title[9:-3]
                    
                launch_datetime = (
                    scan_element.find(
                        "LAUNCH_DATETIME"
                    ).text
                    if scan_element.find(
                        "LAUNCH_DATETIME"
                    ) is not None
                    else None
                )
                
                # Return scan status and additional info in a simple JSON format
                result = {
                    "status": scan_status,
                    "scanRef": scan_ref
                }
                
                # Add optional information if available
                if scan_title:
                    result["title"] = scan_title

                if launch_datetime:
                    result["launchDatetime"] = launch_datetime
                
                return func.HttpResponse(
                    json.dumps(result),
                    status_code=200,
                    mimetype="application/json"
                )

            else:
                logging.warning(
                    "STATE element not found in Qualys response"
                )

                return func.HttpResponse(
                    json.dumps({
                        "status": "Unknown",
                        "error":
                            "Status information not found "
                            "in response"
                    }),
                    status_code=200,
                    mimetype="application/json"
                )
                
        except ET.ParseError as e:
            logging.error(
                f"Failed to parse XML response from Qualys: "
                f"{str(e)}"
            )

            return func.HttpResponse(
                json.dumps({
                    "error":
                        "Failed to parse XML response from Qualys",
                    "status":
                        "Error",
                    "details":
                        str(e)
                }),
                status_code=500,
                mimetype="application/json"
            )
    
    except Exception as e:
        logging.exception(
            f"Error in QualysScanStatus function: {str(e)}"
        )

        return func.HttpResponse(
            json.dumps({
                "error":
                    f"Internal server error: {str(e)}",
                "status":
                    "Error"
            }),
            status_code=500,
            mimetype="application/json"
        )