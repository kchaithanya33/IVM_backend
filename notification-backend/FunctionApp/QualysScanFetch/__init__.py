import logging
import azure.functions as func
import json
import requests
import os
from urllib.parse import urlencode

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    QualysScanFetch - HTTP Trigger Azure Function
    
    This function fetches scan results from Qualys by scan ID or scan reference.
    It replaces the direct HTTP call with managed identity that was previously used.
    
    Input: 
      - scan_id parameter in query string or JSON body
      - scan_ref parameter (alternative to scan_id) for authentication scan results
      - output_format (optional): 'json_extended' or 'xml' (defaults to JSON Extended)
    
    Output: JSON or XML response with scan results in Qualys format
    """
    logging.info('QualysScanFetch function processing a request.')
    
    try:
        # Get scan_id or scan_ref from query parameters or request body
        scan_id = req.params.get('scan_id')
        scan_ref = req.params.get('scan_ref')
        output_format = req.params.get('output_format', 'json_extended')
        
        if not scan_id and not scan_ref:
            req_body = req.get_json()
            scan_id = req_body.get('scan_id')
            scan_ref = req_body.get('scan_ref')
            output_format = req_body.get('output_format', 'json_extended')
        
        # Validate required parameters
        if not scan_id and not scan_ref:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: either 'scan_id' or 'scan_ref' must be provided"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get Qualys credentials from environment variables
        qualys_username = os.environ["QUALYS_USERNAME"]
        qualys_password = os.environ["QUALYS_PASSWORD"]
        qualys_api_url = os.environ["QUALYS_API_URL"]
        
        # Log the scan ID or scan reference we're checking (but not credentials)
        if scan_id:
            logging.info(f"Fetching results for Qualys scan ID: {scan_id}, format: {output_format}")
        else:
            logging.info(f"Fetching results for Qualys scan reference: {scan_ref}, format: {output_format}")
        
        # Build the URL for the scan fetch
        fetch_url = f"{qualys_api_url}/api/2.0/fo/scan/"
        params = {
            "action": "fetch",
            "output_format": output_format
        }
        
        # Add either scan_id or scan_ref to the parameters
        if scan_id:
            params["scan_id"] = scan_id
        else:
            params["scan_ref"] = scan_ref
        
        # Make the API request
        response = requests.get(
            fetch_url,
            params=params,
            auth=(qualys_username, qualys_password),
            headers={"X-Requested-With": "IVM Automation"}
        )
        
        # Handle API errors
        if response.status_code != 200:
            logging.error(f"Qualys API error: Status code {response.status_code}, Response: {response.text}")
            return func.HttpResponse(
                json.dumps({"error": f"Qualys API error: Status code {response.status_code}"}),
                status_code=500,
                mimetype="application/json"
            )
        
        # Return the response based on the requested format
        content_type = "application/json" if output_format.lower() == "json_extended" else "application/xml"
        
        return func.HttpResponse(
            response.text,
            status_code=200,
            mimetype=content_type
        )
    
    except Exception as e:
        logging.exception(f"Error in QualysScanFetch function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )