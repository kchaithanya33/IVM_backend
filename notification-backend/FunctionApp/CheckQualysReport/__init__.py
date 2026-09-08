import logging
import azure.functions as func
import json
import requests
import os
import xml.etree.ElementTree as ET
import traceback

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    CheckQualysReport Function - Checks the status of a report generation request in Qualys
    
    This function checks if a previously requested Qualys report is ready for download.
    
    Input: Query parameters:
      - report_id: The ID of the report to check
      - cycle_id: Optional cycle identifier for the scan
    
    Output: JSON response with report status information
    """
    function_state = {
        "stage": "initialization",
        "report_id": None,
        "cycle_id": None,
        "report_status": None,
        "api_response_status": None
    }
    
    try:
        logging.info("CheckQualysReport function processing a request")
        function_state["stage"] = "parameter_extraction"
        
        # Extract parameters from query parameters
        report_id = req.params.get("report_id")
        cycle_id = req.params.get("cycleId")
        
        # Update function state
        function_state["report_id"] = report_id
        function_state["cycle_id"] = cycle_id
        
        # Validate required parameters
        if not report_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter: report_id"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get Qualys credentials from environment variables
        qualys_username = os.environ["QUALYS_USERNAME"]
        qualys_password = os.environ["QUALYS_PASSWORD"]
        qualys_api_url = os.environ["QUALYS_API_URL"]
        
        logging.info(f"Checking status of report ID: {report_id}")
        function_state["stage"] = "report_status_check"
        
        # Check report status
        report_url = f"{qualys_api_url}/api/2.0/fo/report/"
        status_params = {
            "action": "list",
            "id": report_id
        }
        
        status_response = requests.get(
            report_url,
            params=status_params,
            auth=(qualys_username, qualys_password),
            headers={"X-Requested-With": "IVM Automation"}
        )
        
        function_state["api_response_status"] = status_response.status_code
        
        if status_response.status_code != 200:
            error_message = f"Qualys API error when checking report status: {status_response.status_code}"
            logging.error(error_message)
            return func.HttpResponse(
                json.dumps({"error": error_message}),
                status_code=500,
                mimetype="application/json"
            )
        
        try:
            # Parse status response to check if report is ready
            status_root = ET.fromstring(status_response.text)
            status = status_root.find(".//STATE")
            
            if status is None:
                error_message = "Failed to find report status in response"
                logging.error(error_message)
                return func.HttpResponse(
                    json.dumps({"error": error_message}),
                    status_code=500,
                    mimetype="application/json"
                )
                
            report_status = status.text
            function_state["report_status"] = report_status
            
            if report_status == "Finished":
                logging.info(f"Report {report_id} is ready for download")
                return func.HttpResponse(
                    json.dumps({
                        "report_id": report_id,
                        "status": "ready",
                        "cycle_id": cycle_id
                    }),
                    status_code=200,
                    mimetype="application/json"
                )
            elif report_status == "Error":
                error_message = "Report generation failed with state: Error"
                logging.error(error_message)
                return func.HttpResponse(
                    json.dumps({
                        "report_id": report_id,
                        "status": "error",
                        "message": error_message,
                        "cycle_id": cycle_id
                    }),
                    status_code=200,  # Sending 200 with error status in body
                    mimetype="application/json"
                )
            else:
                # Report is still being generated
                logging.info(f"Report {report_id} is still being generated. Current status: {report_status}")
                return func.HttpResponse(
                    json.dumps({
                        "report_id": report_id,
                        "status": "in_progress",
                        "current_state": report_status,
                        "cycle_id": cycle_id
                    }),
                    status_code=200,
                    mimetype="application/json"
                )
                
        except ET.ParseError as pe:
            error_message = f"Failed to parse XML response when checking report status: {str(pe)}"
            logging.error(error_message)
            return func.HttpResponse(
                json.dumps({"error": error_message}),
                status_code=500,
                mimetype="application/json"
            )
            
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"Error in CheckQualysReport function: {str(e)}"
        logging.error(f"{error_message}\nStack trace:\n{stack_trace}")
        return func.HttpResponse(
            json.dumps({"error": error_message}),
            status_code=500, 
            mimetype="application/json"
        )