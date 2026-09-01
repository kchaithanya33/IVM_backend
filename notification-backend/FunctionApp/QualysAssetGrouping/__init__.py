import logging
import azure.functions as func
import json
import requests
import os
import base64
import xml.etree.ElementTree as ET

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


# ============================================================
# GET QUALYS CREDENTIALS FROM AZURE KEY VAULT
# ============================================================

def get_qualys_credentials_from_key_vault():
    """
    Retrieve Qualys username, password and API base URL
    from Azure Key Vault using Function App Managed Identity.

    Required Function App setting:
        KEY_VAULT_URL

    Required Key Vault secrets:
        QualysUsername
        QualysPassword
        QualysBaseUrl

    Example QualysBaseUrl:
        https://qualysapi.qg1.apps.qualys.in
    """

    logging.info("=== RETRIEVING QUALYS CREDENTIALS FROM KEY VAULT ===")

    key_vault_url = os.getenv("KEY_VAULT_URL")

    if not key_vault_url:
        raise ValueError(
            "KEY_VAULT_URL is not configured in Function App settings."
        )

    logging.info(f"Key Vault URL configured: {key_vault_url}")

    # Function App Managed Identity
    credential = DefaultAzureCredential()

    secret_client = SecretClient(
        vault_url=key_vault_url,
        credential=credential
    )

    # --------------------------------------------------------
    # Get Qualys username
    # --------------------------------------------------------

    username_secret = secret_client.get_secret(
        "QualysUsername"
    )

    qualys_username = username_secret.value

    # --------------------------------------------------------
    # Get Qualys password
    # --------------------------------------------------------

    password_secret = secret_client.get_secret(
        "QualysPassword"
    )

    qualys_password = password_secret.value

    # --------------------------------------------------------
    # Get Qualys Base URL
    # --------------------------------------------------------

    base_url_secret = secret_client.get_secret(
        "QualysBaseUrl"
    )

    qualys_api_url = base_url_secret.value

    # Remove trailing slash
    qualys_api_url = qualys_api_url.rstrip("/")

    # --------------------------------------------------------
    # Safe logging
    # --------------------------------------------------------

    logging.info("=== QUALYS CREDENTIAL CHECK ===")

    logging.info(
        f"Qualys Username: "
        f"{'SET' if qualys_username else 'NOT SET'}"
    )

    logging.info(
        f"Qualys Password: "
        f"{'SET' if qualys_password else 'NOT SET'}"
    )

    logging.info(
        f"Qualys Base URL: {qualys_api_url}"
    )

    return (
        qualys_username,
        qualys_password,
        qualys_api_url
    )


# ============================================================
# MAIN FUNCTION
# ============================================================

def main(req: func.HttpRequest) -> func.HttpResponse:

    logging.info(
        "Qualys Asset Grouping function processing request"
    )

    try:

        # ====================================================
        # GET REQUEST BODY
        # ====================================================

        req_body = req.get_json()

        # ====================================================
        # GET QUALYS CREDENTIALS FROM KEY VAULT
        # ====================================================

        (
            qualys_username,
            qualys_password,
            qualys_api_url
        ) = get_qualys_credentials_from_key_vault()

        # ====================================================
        # GET INPUT PARAMETERS
        # ====================================================

        cycle_id = req_body.get("cycleId")

        groups = req_body.get(
            "groups",
            []
        )

        # Support groupsForCreation
        if not groups and "groupsForCreation" in req_body:

            groups = req_body.get(
                "groupsForCreation",
                []
            )

            logging.info(
                f"Using groupsForCreation format with "
                f"{len(groups)} groups"
            )

        # ====================================================
        # VALIDATE GROUPS
        # ====================================================

        if not groups:

            return func.HttpResponse(
                json.dumps({
                    "error":
                        "Missing required parameter "
                        "'groups' or 'groupsForCreation'"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # ====================================================
        # HANDLE CYCLE ID
        # ====================================================

        if not cycle_id:

            logging.info(
                "No cycleId provided, "
                "will use group names as-is"
            )

            cycle_id = ""

        # ====================================================
        # PROCESS GROUPS
        # ====================================================

        results = []

        for group in groups:

            group_name = group.get("name")

            ips = group.get(
                "ips",
                []
            )

            # ------------------------------------------------
            # Validate group name
            # ------------------------------------------------

            if not group_name:

                results.append({
                    "success": False,
                    "error": "Missing group name"
                })

                continue

            # ------------------------------------------------
            # Validate IPs
            # ------------------------------------------------

            if not ips:

                results.append({
                    "success": False,
                    "groupName": group_name,
                    "error": "No IPs provided for group"
                })

                continue

            try:

                # ============================================
                # CREATE FORMATTED GROUP NAME
                # ============================================

                if (
                    cycle_id
                    and cycle_id not in group_name
                ):

                    formatted_group_name = (
                        f"{cycle_id}_{group_name}"
                    )

                else:

                    formatted_group_name = group_name

                logging.info(
                    f"Using formatted group name: "
                    f"{formatted_group_name}"
                )

                # ============================================
                # CREATE ASSET GROUP
                # ============================================

                group_result = create_asset_group(
                    qualys_api_url,
                    qualys_username,
                    qualys_password,
                    formatted_group_name,
                    ips
                )

                results.append({
                    "success": True,
                    "groupName": formatted_group_name,
                    "result": group_result
                })

            except Exception as e:

                logging.error(
                    f"Error creating asset group "
                    f"{group_name}: {str(e)}",
                    exc_info=True
                )

                results.append({
                    "success": False,
                    "groupName": group_name,
                    "error": str(e)
                })

        # ====================================================
        # RETURN RESULTS
        # ====================================================

        return func.HttpResponse(
            json.dumps({
                "results": results
            }),
            status_code=200,
            mimetype="application/json"
        )

    except ValueError as e:

        logging.error(
            f"Invalid request: {str(e)}"
        )

        return func.HttpResponse(
            json.dumps({
                "error": str(e)
            }),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:

        logging.error(
            f"Error in QualysAssetGrouping function: "
            f"{str(e)}",
            exc_info=True
        )

        return func.HttpResponse(
            json.dumps({
                "error": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )


# ============================================================
# CREATE / UPDATE ASSET GROUP
# ============================================================

def create_asset_group(
    api_url,
    username,
    password,
    group_name,
    ips
):

    logging.info(
        f"Creating asset group: "
        f"{group_name} with {len(ips)} IPs"
    )

    # ========================================================
    # QUALYS API ENDPOINT
    # ========================================================

    endpoint = (
        f"{api_url}/api/2.0/fo/asset/group/"
    )

    # ========================================================
    # IP STRING
    # ========================================================

    ip_string = ",".join(
        str(ip).strip()
        for ip in ips
    )

    # ========================================================
    # CHECK EXISTING GROUP
    # ========================================================

    existing_group = check_asset_group_exists(
        api_url,
        username,
        password,
        group_name
    )

    action = (
        "update"
        if existing_group
        else "add"
    )

    # ========================================================
    # BASIC AUTH
    # ========================================================

    auth_string = (
        f"{username}:{password}"
    )

    encoded_auth = base64.b64encode(
        auth_string.encode()
    ).decode()

    # ========================================================
    # HEADERS
    # ========================================================

    headers = {
        "X-Requested-With": "Security Automation",
        "Content-Type":
            "application/x-www-form-urlencoded",
        "Authorization":
            f"Basic {encoded_auth}"
    }

    # ========================================================
    # REQUEST DATA
    # ========================================================

    data = {
        "action": action,
        "title": group_name,
        "ips": ip_string
    }

    logging.info(
        f"Calling Qualys endpoint: {endpoint}"
    )

    logging.info(
        f"Action: {action}"
    )

    logging.info(
        f"Group name: {group_name}"
    )

    logging.info(
        f"IP count: {len(ips)}"
    )

    # ========================================================
    # API REQUEST
    # ========================================================

    try:

        response = requests.post(
            endpoint,
            headers=headers,
            data=data,
            verify=True,
            timeout=30
        )

    except requests.RequestException as e:

        logging.error(
            f"Qualys API request exception: {str(e)}"
        )

        raise Exception(
            f"API request failed: {str(e)}"
        )

    # ========================================================
    # RESPONSE
    # ========================================================

    logging.info(
        f"Qualys response status code: "
        f"{response.status_code}"
    )

    if response.status_code != 200:

        logging.error(
            f"Qualys API error response: "
            f"{response.text[:1000]}"
        )

        return {
            "status": "error",
            "message":
                "Qualys API request failed",
            "statusCode":
                response.status_code,
            "response":
                response.text[:1000]
        }

    # ========================================================
    # PARSE XML
    # ========================================================

    try:

        root = ET.fromstring(
            response.text
        )

    except ET.ParseError as e:

        logging.error(
            f"Failed to parse Qualys XML: "
            f"{str(e)}"
        )

        return {
            "status": "error",
            "message":
                f"Failed to parse Qualys response: {str(e)}",
            "response":
                response.text[:1000]
        }

    # ========================================================
    # CHECK SUCCESS
    # ========================================================

    if "successfully" in response.text.lower():

        asset_group_id = None

        # ----------------------------------------------------
        # If newly created, try to get ID directly
        # ----------------------------------------------------

        if not existing_group:

            try:

                id_element = root.find(
                    ".//ASSET_GROUP/ID"
                )

                if (
                    id_element is not None
                    and id_element.text
                ):

                    asset_group_id = (
                        id_element.text.strip()
                    )

                    logging.info(
                        f"Extracted asset group ID: "
                        f"{asset_group_id}"
                    )

            except Exception as e:

                logging.warning(
                    f"Could not extract asset group ID: "
                    f"{str(e)}"
                )

        # ----------------------------------------------------
        # If update or ID not found
        # ----------------------------------------------------

        if asset_group_id is None:

            asset_group_id = get_asset_group_id(
                api_url,
                username,
                password,
                group_name
            )

        return {
            "status": "success",
            "message":
                f"Asset group {group_name} "
                f"{'updated' if existing_group else 'created'} "
                f"successfully",
            "ipCount":
                len(ips),
            "assetGroupId":
                asset_group_id
        }

    # ========================================================
    # QUALYS RETURNED ERROR
    # ========================================================

    return {
        "status": "error",
        "message":
            "Failed to create/update asset group",
        "response":
            response.text[:1000]
    }


# ============================================================
# CHECK IF ASSET GROUP EXISTS
# ============================================================

def check_asset_group_exists(
    api_url,
    username,
    password,
    group_name
):

    logging.info(
        f"Checking if asset group exists: "
        f"{group_name}"
    )

    endpoint = (
        f"{api_url}/api/2.0/fo/asset/group/"
    )

    # ========================================================
    # BASIC AUTH
    # ========================================================

    auth_string = (
        f"{username}:{password}"
    )

    encoded_auth = base64.b64encode(
        auth_string.encode()
    ).decode()

    headers = {
        "X-Requested-With": "Security Automation",
        "Authorization":
            f"Basic {encoded_auth}"
    }

    params = {
        "action": "list",
        "title": group_name
    }

    try:

        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            verify=True,
            timeout=30
        )

    except requests.RequestException as e:

        logging.error(
            f"Error checking asset group: "
            f"{str(e)}"
        )

        return False

    logging.info(
        f"Asset group check status: "
        f"{response.status_code}"
    )

    if response.status_code == 200:

        return (
            group_name.lower()
            in response.text.lower()
        )

    logging.warning(
        f"Asset group existence check failed: "
        f"{response.status_code}"
    )

    logging.warning(
        f"Response: {response.text[:500]}"
    )

    return False


# ============================================================
# GET ASSET GROUP ID
# ============================================================

def get_asset_group_id(
    api_url,
    username,
    password,
    group_name
):

    logging.info(
        f"Getting asset group ID for: "
        f"{group_name}"
    )

    endpoint = (
        f"{api_url}/api/2.0/fo/asset/group/"
    )

    # ========================================================
    # BASIC AUTH
    # ========================================================

    auth_string = (
        f"{username}:{password}"
    )

    encoded_auth = base64.b64encode(
        auth_string.encode()
    ).decode()

    headers = {
        "X-Requested-With": "Security Automation",
        "Authorization":
            f"Basic {encoded_auth}"
    }

    params = {
        "action": "list",
        "title": group_name
    }

    try:

        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            verify=True,
            timeout=30
        )

    except requests.RequestException as e:

        logging.error(
            f"Exception getting asset group ID: "
            f"{str(e)}"
        )

        return None

    logging.info(
        f"Get asset group ID status: "
        f"{response.status_code}"
    )

    if response.status_code != 200:

        logging.error(
            f"Failed to get asset group ID. "
            f"Status: {response.status_code}"
        )

        logging.error(
            f"Response: {response.text[:500]}"
        )

        return None

    # ========================================================
    # PARSE XML
    # ========================================================

    try:

        root = ET.fromstring(
            response.text
        )

        for asset_group in root.findall(
            ".//ASSET_GROUP"
        ):

            title_element = asset_group.find(
                "TITLE"
            )

            if (
                title_element is not None
                and title_element.text
                and title_element.text.strip()
                == group_name
            ):

                id_element = asset_group.find(
                    "ID"
                )

                if (
                    id_element is not None
                    and id_element.text
                ):

                    asset_group_id = (
                        id_element.text.strip()
                    )

                    logging.info(
                        f"Found asset group ID: "
                        f"{asset_group_id}"
                    )

                    return asset_group_id

        logging.warning(
            f"Asset group {group_name} "
            f"not found in response"
        )

        return None

    except ET.ParseError as e:

        logging.error(
            f"Failed to parse XML response: "
            f"{str(e)}"
        )

        return None