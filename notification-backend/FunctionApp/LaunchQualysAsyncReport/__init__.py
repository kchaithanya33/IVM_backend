import logging
import azure.functions as func
import json
import requests
import os
import time
import xml.etree.ElementTree as ET
import traceback
from threading import Thread


def launch_qualys_and_callback(
    qualys_api_url, qualys_username, qualys_password, 
    report_params, callback_url, callback_payload, 
    execution_id
):
    """
    Background thread function to:
    1. Launch Qualys report (may take 2-5 minutes)
    2. Parse report ID from response
    3. Call the next Logic App (Polling Logic App) with report ID and all original parameters
    """
    try:
        logging.info(f"[Background-{execution_id}] Starting Qualys report launch")
        
        # Make the API request to launch report generation
        report_url = f"{qualys_api_url}/api/2.0/fo/report/"
        
        start_time = time.time()
        response = requests.post(
            report_url,
            data=report_params,
            auth=(qualys_username, qualys_password),
            headers={"X-Requested-With": "IVM Automation"},
            timeout=300  # 5 minute timeout for large IP lists
        )
        elapsed_time = time.time() - start_time
        
        logging.info(f"[Background-{execution_id}] Qualys API responded in {elapsed_time:.2f} seconds with status {response.status_code}")
        
        if response.status_code != 200:
            error_msg = f"Qualys API error: Status {response.status_code}, Response: {response.text}"
            logging.error(f"[Background-{execution_id}] {error_msg}")
            
            # Call Logic App 2 with error status
            error_payload = callback_payload.copy()
            error_payload["status"] = "error"
            error_payload["error"] = error_msg
            error_payload["executionId"] = execution_id
            
            try:
                requests.post(
                    callback_url,
                    json=error_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                logging.info(f"[Background-{execution_id}] Notified Logic App of error")
            except Exception as e:
                logging.error(f"[Background-{execution_id}] Failed to notify Logic App of error: {str(e)}")
            
            return
        
        # Parse the XML response to get the report ID
        try:
            root = ET.fromstring(response.text)
            report_id = None
            value_elem = root.find(".//VALUE")
            if value_elem is not None and value_elem.text:
                report_id = value_elem.text
                
            if not report_id:
                error_msg = "Failed to extract report ID from Qualys response"
                logging.error(f"[Background-{execution_id}] {error_msg}. Response: {response.text[:500]}")
                return
            
            logging.info(f"[Background-{execution_id}] Report launched successfully with ID: {report_id}")
            
        except ET.ParseError as pe:
            logging.error(f"[Background-{execution_id}] Failed to parse XML response: {str(pe)}")
            return
        
        # Call Logic App 2 (Polling Logic App) with report ID and all original parameters
        final_payload = callback_payload.copy()
        final_payload["vulnReportId"] = report_id
        final_payload["status"] = "launched"
        final_payload["executionId"] = execution_id
        final_payload["qualysLaunchTime"] = elapsed_time
        
        try:
            logging.info(f"[Background-{execution_id}] Calling Polling Logic App with report ID: {report_id}")
            logging.debug(f"[Background-{execution_id}] Polling Logic App payload: {json.dumps(final_payload, indent=2)}")
            
            callback_response = requests.post(
                callback_url,
                json=final_payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if callback_response.status_code in [200, 201, 202]:
                logging.info(f"[Background-{execution_id}] Successfully triggered Polling Logic App. Status: {callback_response.status_code}")
            else:
                logging.warning(f"[Background-{execution_id}] Polling Logic App returned status {callback_response.status_code}: {callback_response.text}")
                
        except requests.exceptions.Timeout:
            logging.error(f"[Background-{execution_id}] Polling Logic App call timed out after 30 seconds")
        except requests.exceptions.RequestException as e:
            logging.error(f"[Background-{execution_id}] Failed to call Polling Logic App: {str(e)}")
            
    except Exception as e:
        stack_trace = traceback.format_exc()
        logging.error(f"[Background-{execution_id}] Unexpected error in background thread: {str(e)}\nStack trace:\n{stack_trace}")


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    LaunchQualysAsyncReport Function - Initiates a report generation request in Qualys
    and triggers Polling Logic App when report ID is available
    
    This function immediately returns 200 OK to the calling Logic App,
    then launches the Qualys report in a background thread and calls the 
    Polling Logic App when the report ID is available.
    
    Input: JSON body:
      - logic_app_url: URL of the Polling Logic App to call after report is launched (required)
      - ips: List of IP addresses (array) or comma-separated string (required)
      - template_id: Qualys report template ID (optional, defaults to 90548452)
      - cycleId: Reporting cycle ID (required, will be passed to Polling Logic App)
      - scanCompletionDate: Scan completion date (optional, will be passed to Polling Logic App)
      - poll_interval: Polling interval in seconds (optional, defaults to 30)
      - Any other parameters: Will be passed through to Polling Logic App
    
    Output: JSON response with status 200 and execution tracking ID
    """
    function_state = {
        "stage": "initialization",
        "execution_id": None
    }
    
    try:
        logging.info("LaunchQualysAsyncReport function processing a request")
        function_state["stage"] = "parameter_extraction"
        
        # Get parameters from JSON body
        try:
            body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                mimetype="application/json"
            )
        
        if not body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Generate unique execution ID for tracking
        execution_id = f"exec_{int(time.time())}_{os.urandom(4).hex()}"
        function_state["execution_id"] = execution_id
        
        # Extract required Polling Logic App URL
        logic_app_url = body.get("logic_app_url")
        if not logic_app_url:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: logic_app_url"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Extract required cycleId
        cycle_id = body.get("cycleId")
        if not cycle_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: cycleId"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Extract IPs (required)
        ips = body.get("ips")
        if not ips:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: ips"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Convert IPs list to comma-separated string if needed
        if isinstance(ips, list):
            ips_param = ",".join(ips)
            ips_count = len(ips)
        else:
            ips_param = str(ips)
            ips_count = len(ips_param.split(','))
        
        # Extract optional parameters with defaults
        template_id = body.get("template_id", "92270780")  # Using your template ID from Logic App
        poll_interval = body.get("poll_interval", 30)
        scan_completion_date = body.get("scanCompletionDate", "")
        
        # Get Qualys credentials from environment variables
        try:
            qualys_username = os.environ["QUALYS_USERNAME"]
            qualys_password = os.environ["QUALYS_PASSWORD"]
            qualys_api_url = os.environ["QUALYS_API_URL"]
        except KeyError as ke:
            return func.HttpResponse(
                json.dumps({"error": f"Missing environment variable: {str(ke)}"}),
                status_code=500,
                mimetype="application/json"
            )
        
        logging.info(f"[{execution_id}] Received request for {ips_count} IPs, cycleId: {cycle_id}")
        function_state["stage"] = "preparing_background_task"
        
        # Define report title with timestamp
        timestamp = int(time.time())
        report_title = f"Vulnerability_Report_{cycle_id}_{timestamp}"
        
        # Define report parameters for vulnerability data
        report_params = {
            "action": "launch",
            "template_id": template_id,
            "report_type": "Scan",
            "output_format": "xml",
            "report_title": report_title,
            "ips": ips_param
        }
        
        logging.info(f"[{execution_id}] Report will be launched with template_id: {template_id}")
        
        # Create callback payload for Polling Logic App
        # This will include ALL parameters that need to be passed through
        callback_payload = {
            "cycleId": cycle_id,
            "pollInterval": poll_interval
        }
        
        # Add scanCompletionDate if provided
        if scan_completion_date:
            callback_payload["scanCompletionDate"] = scan_completion_date
        
        # Pass through ALL other parameters from request body 
        # (except logic_app_url, ips, and template_id which are already handled)
        excluded_keys = ["logic_app_url", "ips", "template_id"]
        for key, value in body.items():
            if key not in excluded_keys and key not in callback_payload:
                callback_payload[key] = value
        
        # Start background thread to launch report and callback to Polling Logic App
        thread = Thread(
            target=launch_qualys_and_callback,
            args=(
                qualys_api_url, 
                qualys_username, 
                qualys_password,
                report_params,
                logic_app_url,
                callback_payload,
                execution_id
            ),
            daemon=True
        )
        thread.start()
        logging.info(f"[{execution_id}] Started background thread for Qualys report launch")
        
        # Return 200 OK immediately to Logic App 1
        response_data = {
            "status": "accepted",
            "message": "Report launch initiated. Polling Logic App will be triggered when report ID is available.",
            "executionId": execution_id,
            "cycleId": cycle_id,
            "ipCount": ips_count,
            "estimatedDuration": "2-5 minutes for report launch"
        }
        
        logging.info(f"[{execution_id}] Returning 200 OK to caller immediately")
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )
            
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"Error in LaunchQualysAsyncReport function at stage '{function_state.get('stage', 'unknown')}': {str(e)}"
        logging.error(f"{error_message}\nStack trace:\n{stack_trace}")
        logging.error(f"Function state: {json.dumps(function_state)}")
        return func.HttpResponse(
            json.dumps({
                "error": error_message,
                "stage": function_state.get("stage", "unknown"),
                "executionId": function_state.get("execution_id")
            }),
            status_code=500, 
            mimetype="application/json"
        )