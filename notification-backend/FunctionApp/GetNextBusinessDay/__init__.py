import logging
import json
from datetime import datetime, timedelta, time
from dateutil.parser import parse
import azure.functions as func
import sys
import os
import pytz


# Add the parent directory to sys.path so we can import shared_utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_utils import (
    is_business_day, 
    is_business_hour, 
    get_business_hours_for_region,
    handle_api_response, 
    DEFAULT_REGION
)

# Region to timezone mapping
REGION_TIMEZONE_MAP = {
    'IN': 'Asia/Kolkata',
    'US': 'America/New_York',
    'UK': 'Europe/London',
    'AU': 'Australia/Sydney',
}


def get_timezone_for_region(region):
    """Get pytz timezone object for a region"""
    tz_name = REGION_TIMEZONE_MAP.get(region, 'UTC')
    return pytz.timezone(tz_name)


def parse_time_string(time_str):
    """Parse time string in HH:MM:SS format to time object"""
    parts = time_str.split(':')
    return time(int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)


def calculate_time_until_business_hours(current_dt_region, start_time, end_time, business_days):
    """
    Calculate how much time until the next business hours start.
    
    Returns:
        tuple: (next_business_datetime, hours_to_wait, minutes_to_wait, is_currently_within_hours)
    """
    current_date = current_dt_region.date()
    current_time = current_dt_region.time()
    current_weekday = current_dt_region.isoweekday()  # 1=Monday, 7=Sunday
    
    is_today_business_day = current_weekday in business_days
    
    # Case 1: Currently within business hours
    if is_today_business_day and start_time <= current_time < end_time:
        return current_dt_region, 0, 0, True
    
    # Case 2: Today is a business day but before business hours
    if is_today_business_day and current_time < start_time:
        next_business_dt = datetime.combine(current_date, start_time)
        next_business_dt = current_dt_region.tzinfo.localize(next_business_dt)
        time_diff = next_business_dt - current_dt_region
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        return next_business_dt, hours, minutes, False
    
    # Case 3: After business hours today OR not a business day
    # Find next business day
    next_date = current_dt_region + timedelta(days=1)
    
    while next_date.isoweekday() not in business_days:
        next_date += timedelta(days=1)
    
    # Create datetime at business start time on next business day
    next_business_dt = datetime.combine(next_date.date(), start_time)
    next_business_dt = current_dt_region.tzinfo.localize(next_business_dt)
    
    time_diff = next_business_dt - current_dt_region
    hours = int(time_diff.total_seconds() // 3600)
    minutes = int((time_diff.total_seconds() % 3600) // 60)
    
    return next_business_dt, hours, minutes, False


def calculate_next_business_slot(reference_dt_utc, region, start_time_str, end_time_str, business_days):
    """
    Calculate the next available business time slot considering both date and time.
    Also calculates the wait time until business hours.
    
    Args:
        reference_dt_utc: datetime object in UTC (timezone aware)
        region: region code (e.g., 'IN')
        start_time_str: business start time in region time (e.g., '05:00:00')
        end_time_str: business end time in region time (e.g., '18:00:00')
        business_days: list of business days (1=Monday, 2=Tuesday, ..., 7=Sunday)
    
    Returns:
        dict: {
            'next_slot_utc': datetime,
            'next_slot_region': datetime,
            'is_within_hours': bool,
            'hours_to_wait': int,
            'minutes_to_wait': int,
            'days_to_wait': int
        }
    """
    region_tz = get_timezone_for_region(region)
    
    # Convert UTC time to region timezone
    reference_dt_region = reference_dt_utc.astimezone(region_tz)
    
    # Parse business hours
    start_time = parse_time_string(start_time_str)
    end_time = parse_time_string(end_time_str)
    
    # Get current date and time components in region timezone
    current_date = reference_dt_region.date()
    current_time = reference_dt_region.time()
    current_weekday = reference_dt_region.isoweekday()  # 1=Monday, 7=Sunday
    
    logging.info(f"Reference time in {region}: {reference_dt_region}")
    logging.info(f"Current weekday: {current_weekday}, Business days: {business_days}")
    logging.info(f"Current time: {current_time}, Business hours: {start_time} - {end_time}")
    
    # Calculate time until next business hours
    next_business_dt_region, hours_to_wait, minutes_to_wait, is_within_hours = \
        calculate_time_until_business_hours(reference_dt_region, start_time, end_time, business_days)
    
    # Convert to UTC
    next_slot_utc = next_business_dt_region.astimezone(pytz.UTC)
    
    # Calculate days difference
    days_to_wait = (next_business_dt_region.date() - reference_dt_region.date()).days
    
    logging.info(f"Next business slot - Region: {next_business_dt_region}")
    logging.info(f"Next business slot - UTC: {next_slot_utc}")
    logging.info(f"Wait time - Days: {days_to_wait}, Hours: {hours_to_wait}, Minutes: {minutes_to_wait}")
    
    return {
        'next_slot_utc': next_slot_utc,
        'next_slot_region': next_business_dt_region,
        'is_within_hours': is_within_hours,
        'hours_to_wait': hours_to_wait,
        'minutes_to_wait': minutes_to_wait,
        'days_to_wait': days_to_wait,
        'total_minutes_to_wait': hours_to_wait * 60 + minutes_to_wait
    }


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Calculate the next business day/slot from a reference date
    """
    logging.info('Processing GetNextBusinessDay request')
    
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
        offset_days = req_body.get('offsetDays', 1)
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
            logging.info(f'businessDays input type: {type(business_days_input)}, value: {business_days_input}')
            
            if isinstance(business_days_input, str):
                # Try to parse string as JSON array
                try:
                    business_days = json.loads(business_days_input.strip())
                    logging.info(f'Parsed businessDays from string: {business_days}')
                except json.JSONDecodeError as e:
                    logging.error(f'Failed to parse businessDays JSON: {str(e)}')
                    return handle_api_response(
                        400,
                        {"error": f"businessDays must be a valid JSON array or list, e.g., [1,2,3,4,5]. Error: {str(e)}"}
                    )
            elif isinstance(business_days_input, list):
                business_days = business_days_input
                logging.info(f'businessDays is already a list: {business_days}')
            else:
                logging.error(f'businessDays is invalid type: {type(business_days_input)}')
                return handle_api_response(
                    400,
                    {"error": f"businessDays must be an array of integers (1-7), got type: {type(business_days_input).__name__}"}
                )
            
            # Validate the values are integers between 1-7
            if not all(isinstance(day, int) and 1 <= day <= 7 for day in business_days):
                logging.error(f'businessDays contains invalid values: {business_days}')
                return handle_api_response(
                    400,
                    {"error": "businessDays must contain integers between 1 (Monday) and 7 (Sunday)"}
                )
        
        logging.info(f'Final businessDays value: {business_days}')
            
        # Parse date - make it timezone aware
        try:
            reference_date = parse(reference_date_str)
            # If naive datetime, assume UTC
            if reference_date.tzinfo is None:
                reference_date = pytz.UTC.localize(reference_date)
            else:
                # Ensure it's in UTC
                reference_date = reference_date.astimezone(pytz.UTC)
                
            logging.info(f"Parsed reference date (UTC): {reference_date}")
        except ValueError as e:
            return handle_api_response(
                400,
                {"error": f"Invalid date format: {str(e)}"}
            )
        
        # NEW LOGIC: If business hours AND business days are provided, 
        # calculate next available business slot with wait time calculation
        if start_time_str and end_time_str and business_days:
            logging.info("Calculating next business slot with time consideration and wait time")
            
            result = calculate_next_business_slot(
                reference_date,
                region,
                start_time_str,
                end_time_str,
                business_days
            )
            
            # Prepare comprehensive response
            response = {
                "referenceDateTime": reference_date_str,
                "nextBusinessDay": result['next_slot_utc'].isoformat(),  # Backward compatible field name
                "nextBusinessDateTime": result['next_slot_utc'].isoformat(),
                "nextBusinessDateTimeRegion": result['next_slot_region'].isoformat(),
                "region": region,
                "isWithinBusinessHours": result['is_within_hours'],
                "waitTime": {
                    "days": result['days_to_wait'],
                    "hours": result['hours_to_wait'],
                    "minutes": result['minutes_to_wait'],
                    "totalMinutes": result['total_minutes_to_wait'],
                    "totalHours": round(result['total_minutes_to_wait'] / 60, 2),
                    "visibilityTimeoutSeconds": result['total_minutes_to_wait'] * 60
                },
                "customBusinessHours": {
                    "startTime": start_time_str,
                    "endTime": end_time_str
                },
                "customBusinessDays": business_days
            }
            
            return handle_api_response(200, response)
        
        # ORIGINAL LOGIC: Calculate next business day (without time consideration)
        # This runs when only offsetDays is used without business hours
        else:
            logging.info("Calculating next business day (offset-based)")
            days_added = 0
            next_date = reference_date
            
            while days_added < offset_days:
                next_date += timedelta(days=1)
                if is_business_day(next_date, region, business_days):
                    days_added += 1
                    
            # Check if the time is within business hours
            is_within_business_hours = is_business_hour(
                next_date, 
                region, 
                start_time_str, 
                end_time_str
            )
            
            # Prepare response
            response = {
                "referenceDateTime": reference_date_str,
                "nextBusinessDay": next_date.isoformat(),
                "region": region,
                "isWithinBusinessHours": is_within_business_hours
            }
            
            # Include custom business hours in response if provided
            if start_time_str and end_time_str:
                response["customBusinessHours"] = {
                    "startTime": start_time_str,
                    "endTime": end_time_str
                }
            else:
                # Get default business hours for the region
                region_business_hours = get_business_hours_for_region(region)
                response["regionBusinessHours"] = region_business_hours
            
            # Include custom business days if provided
            if business_days:
                response["customBusinessDays"] = business_days
            
            return handle_api_response(200, response)
        
    except Exception as e:
        logging.exception(f"Error in GetNextBusinessDay: {str(e)}")
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Full traceback: {error_details}")
        return handle_api_response(
            500, 
            {"error": f"Internal server error: {str(e)}", "details": error_details}
        )