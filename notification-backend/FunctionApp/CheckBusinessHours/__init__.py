import logging
import json
from datetime import datetime, timedelta
from dateutil.parser import parse
import azure.functions as func
import sys
import os

# Add the parent directory to sys.path so we can import shared_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utils import (
    is_business_day,
    is_business_hour,
    get_business_hours_for_region,
    get_holidays,
    handle_api_response,
    DEFAULT_REGION
)

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Calculate SLA deadline based on business hours
    """
    logging.info('Processing CalculateSLADeadline request')
    
    try:
        # Parse request body
        req_body = req.get_json()
        start_date_str = req_body.get('startDate')
        sla_hours = req_body.get('slaHours', 24)
        region = req_body.get('region', DEFAULT_REGION)
        only_count_business_hours = req_body.get('onlyCountBusinessHours', True)
        
        if not start_date_str:
            return handle_api_response(
                400, 
                {"error": "startDate must be provided"}
            )
            
        # Parse start date
        try:
            start_date = parse(start_date_str)
        except ValueError as e:
            return handle_api_response(
                400,
                {"error": f"Invalid date format: {str(e)}"}
            )
        
        # Get business hours for the region
        business_hours = get_business_hours_for_region(region)
        
        # Calculate deadline
        deadline_date = start_date
        hours_counted = 0
        actual_hours_elapsed = 0
        crosses_holidays = False
        
        if only_count_business_hours:
            # Only count business hours
            current_date = start_date
            
            # If starting outside business hours, move to the next business hour
            if not is_business_hour(current_date, region):
                # Move to next business day if needed
                while not is_business_day(current_date, region):
                    current_date += timedelta(days=1)
                    crosses_holidays = True
                
                # Set time to business hours start
                try:
                    business_start_time = datetime.strptime(business_hours["startTime"], "%H:%M:%S").time()
                    current_date = datetime.combine(current_date.date(), business_start_time)
                except (KeyError, ValueError):
                    # Default to 9 AM if there's an issue with business hours config
                    current_date = datetime.combine(current_date.date(), datetime.strptime("09:00:00", "%H:%M:%S").time())
            
            # Now calculate by incrementing hours during business hours
            while hours_counted < sla_hours:
                # Check if current time is a business hour
                if is_business_hour(current_date, region):
                    hours_counted += 1
                
                current_date += timedelta(hours=1)
                actual_hours_elapsed += 1
                
                # If we've moved to a new day, check if it's a business day
                if current_date.day != deadline_date.day:
                    deadline_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    # If not a business day, skip to the next business day
                    while not is_business_day(deadline_date, region):
                        deadline_date += timedelta(days=1)
                        crosses_holidays = True
                        actual_hours_elapsed += 24
                    
                    # Set time to business hours start
                    try:
                        business_start_time = datetime.strptime(business_hours["startTime"], "%H:%M:%S").time()
                        current_date = datetime.combine(deadline_date.date(), business_start_time)
                    except (KeyError, ValueError):
                        # Default to 9 AM
                        current_date = datetime.combine(deadline_date.date(), datetime.strptime("09:00:00", "%H:%M:%S").time())
            
            deadline_date = current_date
        else:
            # Simply add the SLA hours regardless of business hours
            deadline_date = start_date + timedelta(hours=sla_hours)
            actual_hours_elapsed = sla_hours
            
            # Check if we crossed any holidays
            current_date = start_date
            while current_date <= deadline_date:
                if not is_business_day(current_date, region) and current_date.date() != start_date.date():
                    crosses_holidays = True
                    break
                current_date += timedelta(days=1)
        
        # Prepare response
        response = {
            "deadlineDate": deadline_date.isoformat(),
            "businessHoursRequired": sla_hours,
            "actualHoursElapsed": actual_hours_elapsed,
            "crossesHolidays": crosses_holidays
        }
        
        return handle_api_response(200, response)
        
    except Exception as e:
        logging.exception(f"Error in CalculateSLADeadline: {str(e)}")
        return handle_api_response(
            500, 
            {"error": f"Internal server error: {str(e)}"}
        )