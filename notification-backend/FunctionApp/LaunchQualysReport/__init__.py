import logging
import azure.functions as func
import json
import requests
import os
import time
import xml.etree.ElementTree as ET
import traceback

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    LaunchQualysReport Function - Initiates a report generation request in Qualys
    
    This function submits a request to Qualys to generate a vulnerability report for specified asset groups or IPs.
    
    Input: Query parameters or JSON body:
      - asset_groups: Comma-separated list of Qualys asset group IDs (query param)
      - ips: List of IP addresses (JSON body array) or comma-separated string (query param)
      - template_id: Optional ID of the Qualys report template to use (defaults to 90548452)
      - cycleId: Optional cycle identifier for the scan
    
    Output: JSON response with report_id and status information
    """
    function_state = {
        "stage": "initialization",
        "asset_groups": None,
        "ips": None,
        "template_id": None,
        "cycle_id": None,
        "report_id": None,
        "api_response_status": None
    }
    
    try:
        logging.info("LaunchQualysReport function processing a request")
        function_state["stage"] = "parameter_extraction"
        
        # Extract parameters from query parameters
        asset_groups = req.params.get("asset_groups")
        template_id = req.params.get("template_id", "90548452")
        cycle_id = req.params.get("cycleId")
        ips_param = req.params.get("ips")
        
        # Try to get IPs from JSON body if not in query params
        ips_list = None
        if not ips_param:
            try:
                body = req.get_json()
                if body and "ips" in body:
                    ips_list = body["ips"]
                    if isinstance(ips_list, list):
                        ips_param = ",".join(ips_list)
                    else:
                        ips_param = ips_list
            except ValueError:
                pass  # No JSON body or invalid JSON
        
        # Update function state
        function_state["asset_groups"] = asset_groups
        function_state["ips"] = ips_param
        function_state["template_id"] = template_id
        function_state["cycle_id"] = cycle_id
        
        # Validate that at least one parameter is provided
        if not asset_groups and not ips_param:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: either asset_groups or ips must be provided"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get Qualys credentials from environment variables
        qualys_username = os.environ["QUALYS_USERNAME"]
        qualys_password = os.environ["QUALYS_PASSWORD"]
        qualys_api_url = os.environ["QUALYS_API_URL"]
        
        # Determine what type of scan is being requested
        scan_target = f"IPs: {ips_param}" if ips_param else f"asset groups: {asset_groups}"
        logging.info(f"Initiating vulnerability report request for {scan_target}")
        function_state["stage"] = "report_generation_request"
        
        # Launch report generation - Request the report
        report_url = f"{qualys_api_url}/api/2.0/fo/report/"
        
        # Define report title based on presence of cycle_id
        report_title = f"Vulnerability_Report_{cycle_id}_{int(time.time())}" if cycle_id else f"Vulnerability_Report_{int(time.time())}"
        
        # Define report parameters for vulnerability data
        report_params = {
            "action": "launch",
            "template_id": template_id,
            "report_type": "Scan",
            "output_format": "xml",
            "report_title": report_title
        }
        
        # Add either asset_group_ids or ips parameter
        if ips_param:
            report_params["ips"] = ips_param
        else:
            report_params["asset_group_ids"] = asset_groups
        
        # Make the API request to launch report generation
        response = requests.post(
            report_url,
            data=report_params,
            auth=(qualys_username, qualys_password),
            headers={"X-Requested-With": "IVM Automation"}
        )
        
        function_state["api_response_status"] = response.status_code
        
        # Handle API errors
        if response.status_code != 200:
            error_message = f"Qualys API error when launching report: Status code {response.status_code}, Response: {response.text}"
            logging.error(error_message)
            return func.HttpResponse(
                json.dumps({"error": error_message}),
                status_code=500,
                mimetype="application/json"
            )
        
        function_state["stage"] = "parsing_report_id"
        # Parse the XML response to get the report ID
        try:
            root = ET.fromstring(response.text)
            report_id = None
            value_elem = root.find(".//VALUE")
            if value_elem is not None and value_elem.text:
                report_id = value_elem.text
                
            if not report_id:
                error_message = "Failed to get report ID from response"
                logging.error(error_message)
                return func.HttpResponse(
                    json.dumps({"error": error_message}),
                    status_code=500,
                    mimetype="application/json"
                )
            
            function_state["report_id"] = report_id
            logging.info(f"Report generation started with ID: {report_id}")

            # Build response object
            response_data = {
                "report_id": report_id,
                "status": "launched",
                "cycle_id": cycle_id,
                "template_id": template_id
            }
            
            # Add either asset_groups or ips to response
            if ips_param:
                response_data["ips"] = ips_param
            else:
                response_data["asset_groups"] = asset_groups

            # Return the report ID and status
            return func.HttpResponse(
                json.dumps(response_data),
                status_code=200,
                mimetype="application/json"
            )
            
        except ET.ParseError as pe:
            error_message = f"Failed to parse XML response when getting report ID: {str(pe)}"
            logging.error(error_message)
            return func.HttpResponse(
                json.dumps({"error": error_message}),
                status_code=500,
                mimetype="application/json"
            )
            
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"Error in LaunchQualysReport function: {str(e)}"
        logging.error(f"{error_message}\nStack trace:\n{stack_trace}")
        return func.HttpResponse(
            json.dumps({"error": error_message}),
            status_code=500, 
            mimetype="application/json"
        )