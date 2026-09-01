import logging
import json
from datetime import datetime
from dateutil.parser import parse
import azure.functions as func
import sys
import os

# Add the parent directory to sys.path so we can import shared_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utils import (
    is_business_day,
    is_business_hour,
    handle_api_response,
    DEFAULT_REGION
)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Check if a reference date time is a business day and falls within business hours
    for the specified region
    """
    logging.info('Processing IsBusinessDayAndHour request')
    
    try:
        # Parse request body
        try:
            req_body = req.get_json()
            logging.info(f'Request body: {json.dumps(req_body)}')
        except ValueError as e:
            logging.error(f'Failed to parse JSON: {str(e)}')
            return handle_api_response(
                400,
                {"error": f"Invalid JSON in request body: {str(e)}"}
            )
        reference_date_str = req_body.get('referenceDateTime')
        region = req_body.get('region', DEFAULT_REGION)
        start_time_str = req_body.get('startTime')
        end_time_str = req_body.get('endTime')
        business_days_input = req_body.get('businessDays')
        
        if not reference_date_str:
            return handle_api_response(
                400, 
                {"error": "referenceDateTime must be provided"}
            )
        
        # Validate time parameters
        if start_time_str and not end_time_str:
            return handle_api_response(
                400,
                {"error": "endTime must be provided when startTime is specified"}
            )
        
        if end_time_str and not start_time_str:
            return handle_api_response(
                400,
                {"error": "startTime must be provided when endTime is specified"}
            )
        
        # Parse and validate businessDays
        business_days = None
        if business_days_input is not None:
            if isinstance(business_days_input, str):
                # Try to parse string as JSON array
                try:
                    business_days = json.loads(business_days_input.strip())
                except json.JSONDecodeError:
                    return handle_api_response(
                        400,
                        {"error": "businessDays must be a valid JSON array or list, e.g., [1,2,3,4,5]"}
                    )
            elif isinstance(business_days_input, list):
                business_days = business_days_input
            else:
                return handle_api_response(
                    400,
                    {"error": "businessDays must be an array of integers (1-7)"}
                )
            
            # Validate the values are integers between 1-7
            if not all(isinstance(day, int) and 1 <= day <= 7 for day in business_days):
                return handle_api_response(
                    400,
                    {"error": "businessDays must contain integers between 1 (Monday) and 7 (Sunday)"}
                )
            
        # Parse reference date
        try:
            reference_date = parse(reference_date_str)
        except ValueError as e:
            return handle_api_response(
                400,
                {"error": f"Invalid date format: {str(e)}"}
            )
        
        # Check if reference date is a business day
        business_day_check = is_business_day(reference_date, region, business_days)
        
        # Check if reference time is within business hours
        business_hour_check = is_business_hour(
            reference_date, 
            region, 
            start_time_str, 
            end_time_str
        )
        
        # Prepare response
        response = {
            "referenceDateTime": reference_date_str,
            "region": region,
            "isBusinessDay": business_day_check,
            "isBusinessHour": business_hour_check,
            "isBusinessDayAndHour": business_day_check and business_hour_check
        }
        
        # Include custom business hours in response if provided
        if start_time_str and end_time_str:
            response["customBusinessHours"] = {
                "startTime": start_time_str,
                "endTime": end_time_str
            }
        
        # Include business days if provided
        if business_days:
            response["customBusinessDays"] = business_days
        
        return handle_api_response(200, response)
        
    except Exception as e:
        logging.exception(f"Error in IsBusinessDayAndHour: {str(e)}")
        return handle_api_response(
            500, 
            {"error": f"Internal server error: {str(e)}"}
        )