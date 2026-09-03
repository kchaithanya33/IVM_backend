import logging
import azure.functions as func
import json
import requests
import os
from urllib.parse import urlencode
from datetime import datetime
import xml.etree.ElementTree as ET

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    try:
        # Get request body
        req_body = req.get_json()
        
        # Extract required parameters
        qualys_username = os.environ["QUALYS_USERNAME"] 
        qualys_password = os.environ["QUALYS_PASSWORD"]
        qualys_api_url = os.environ["QUALYS_API_URL"]
        
        asset_group = req_body.get('assetGroup')
        scan_title = req_body.get('scanTitle', f'VM Auth Scan Launch {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        option_profile = req_body.get('optionProfile')  # Option profile name
        option_id = req_body.get('optionId')           # Direct option ID if known
        iscanner_name = req_body.get('iscannerName')
        
        # Validate required parameters
        if not asset_group:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter 'assetGroup'"}),
                status_code=400,
                mimetype="application/json"
            )
            
        # If option_profile is provided but no option_id, fetch the option_id
        if option_profile and not option_id:
            logging.info(f"Looking up option ID for profile: {option_profile}")
            option_id = get_option_id_from_title(
                qualys_api_url,
                qualys_username,
                qualys_password,
                option_profile
            )
            if not option_id:
                return func.HttpResponse(
                    json.dumps({"error": f"Could not find option ID for option profile '{option_profile}'"}),
                    status_code=400,
                    mimetype="application/json"
                )
            logging.info(f"Found option ID: {option_id} for profile: {option_profile}")
                
        if not option_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter 'optionId' or 'optionProfile'"}),
                status_code=400,
                mimetype="application/json"
            )
            
        # Launch authenticated scan
        scan_result = launch_authenticated_scan(
            qualys_api_url,
            qualys_username,
            qualys_password,
            asset_group,
            scan_title,
            option_id,
            iscanner_name
        )
        
        return func.HttpResponse(
            json.dumps(scan_result),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

def get_option_id_from_title(api_url, username, password, option_title):
    """
    Get the option ID from the option profile name/title
    """
    endpoint = f"{api_url}/api/2.0/fo/subscription/option_profile/vm/"
    
    # Prepare request headers
    headers = {
        "X-Requested-With": "curl demo 2"
    }
    
    # Prepare request parameters
    params = {
        "action": "list"
    }
    
    # Make the API request
    response = requests.get(
        endpoint,
        headers=headers,
        params=params,
        auth=(username, password),
        verify=True
    )
    
    # Check if request was successful
    if response.status_code == 200:
        # Parse XML response
        root = ET.fromstring(response.text)
        
        # Find profile with matching name
        for profile in root.findall('.//OPTION_PROFILE'):
            name_elem = profile.find('.//GROUP_NAME')
            if name_elem is not None:
                # Use CDATA content and strip whitespace
                name_text = name_elem.text.strip() if name_elem.text else ""
                if name_text == option_title:
                    id_elem = profile.find('.//ID')
                    if id_elem is not None:
                        return id_elem.text
    
    return None

def launch_authenticated_scan(api_url, username, password, asset_group, scan_title, option_id, iscanner_name=None):
    """
    Launch an authenticated scan in Qualys
    """
    # API endpoint for launching scan
    endpoint = f"{api_url}/api/2.0/fo/scan/"
    
    # Prepare request headers
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "curl demo 2"
    }
    
    # Prepare request parameters
    params = {
        "action": "launch",
        "scan_title": scan_title,
        "option_id": option_id,
        "target_from": "assets",
        "asset_groups": asset_group,
    }
    
    # Add scanner name if provided
    if iscanner_name:
        params["iscanner_name"] = iscanner_name
    
    # Make the API request
    response = requests.post(
        endpoint,
        headers=headers,
        data=urlencode(params),
        auth=(username, password),
        verify=True  # Use SSL verification
    )
    
    # Check if request was successful
    if response.status_code == 200:
        # Parse XML response
        root = ET.fromstring(response.text)
        
        # Extract scan ID
        scan_id = None
        scan_reference = None
        
        # Look for ID and REFERENCE in the XML response
        for item in root.findall('.//ITEM'):
            key = item.find('./KEY')
            if key is not None and key.text == "ID":
                scan_id = item.find('./VALUE').text
            elif key is not None and key.text == "REFERENCE":
                scan_reference = item.find('./VALUE').text
        
        return {
            "success": True,
            "message": "Scan launched successfully",
            "scanId": scan_id,
            "reference": scan_reference,
            "scanTitle": scan_title,
            "assetGroup": asset_group,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "success": False,
            "status_code": response.status_code,
            "error": response.text
        }