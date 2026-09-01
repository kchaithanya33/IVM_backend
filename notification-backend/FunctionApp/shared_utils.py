# shared_utils.py

import json
import logging
import azure.functions as func
from datetime import datetime, time, timedelta, timezone
from dateutil.parser import parse

DEFAULT_REGION = "UTC"  # Default region

# Region to UTC offset mapping (in hours)
# This is simpler and more maintainable than timezone strings
REGION_UTC_OFFSETS = {
    # UTC
    "UTC": 0,
    
    # Americas
    "US_EAST": -5,           # EST/EDT (with DST consideration)
    "US_CENTRAL": -6,        # CST/CDT
    "US_MOUNTAIN": -7,       # MST/MDT
    "US_WEST": -8,           # PST/PDT
    "US": -5,                # Default to Eastern
    "CA": -5,                # Canada (Eastern)
    "MX": -6,                # Mexico
    "BR": -3,                # Brazil
    "AR": -3,                # Argentina
    "CL": -3,                # Chile
    "CO": -5,                # Colombia
    "PE": -5,                # Peru
    
    # Europe
    "UK": 0,                 # GMT/BST
    "GB": 0,
    "IE": 0,                 # Ireland
    "PT": 0,                 # Portugal
    "FR": 1,                 # France
    "DE": 1,                 # Germany
    "IT": 1,                 # Italy
    "ES": 1,                 # Spain
    "NL": 1,                 # Netherlands
    "BE": 1,                 # Belgium
    "CH": 1,                 # Switzerland
    "AT": 1,                 # Austria
    "SE": 1,                 # Sweden
    "NO": 1,                 # Norway
    "DK": 1,                 # Denmark
    "PL": 1,                 # Poland
    "CZ": 1,                 # Czech Republic
    "GR": 2,                 # Greece
    "FI": 2,                 # Finland
    "RU": 3,                 # Russia (Moscow)
    "TR": 3,                 # Turkey
    
    # Asia
    "IN": 5.5,               # India (IST)
    "LK": 5.5,               # Sri Lanka
    "PK": 5,                 # Pakistan
    "BD": 6,                 # Bangladesh
    "CN": 8,                 # China
    "JP": 9,                 # Japan
    "KR": 9,                 # South Korea
    "SG": 8,                 # Singapore
    "MY": 8,                 # Malaysia
    "TH": 7,                 # Thailand
    "VN": 7,                 # Vietnam
    "ID": 7,                 # Indonesia (Western)
    "PH": 8,                 # Philippines
    "HK": 8,                 # Hong Kong
    "TW": 8,                 # Taiwan
    "AE": 4,                 # UAE
    "UAE": 4,
    "SA": 3,                 # Saudi Arabia
    "QA": 3,                 # Qatar
    "KW": 3,                 # Kuwait
    "BH": 3,                 # Bahrain
    "OM": 4,                 # Oman
    "IL": 2,                 # Israel
    
    # Oceania
    "AU": 10,                # Australia (Eastern)
    "AU_EAST": 10,
    "AU_CENTRAL": 9.5,
    "AU_WEST": 8,
    "NZ": 12,                # New Zealand
    
    # Africa
    "ZA": 2,                 # South Africa
    "EG": 2,                 # Egypt
    "KE": 3,                 # Kenya
    "NG": 1,                 # Nigeria
    "MA": 1,                 # Morocco
}

# Region-specific business hours (24-hour format)
REGION_BUSINESS_HOURS = {
    "DEFAULT": {"start": "09:00", "end": "17:00"},
    
    # Custom hours by region
    "IN": {"start": "09:30", "end": "18:30"},
    "DE": {"start": "08:00", "end": "17:00"},
    "CH": {"start": "08:00", "end": "17:00"},
    "AT": {"start": "08:00", "end": "17:00"},
    "SE": {"start": "08:00", "end": "17:00"},
    "NO": {"start": "08:00", "end": "16:00"},
    "DK": {"start": "08:00", "end": "16:00"},
    "FI": {"start": "08:00", "end": "16:00"},
    "FR": {"start": "09:00", "end": "18:00"},
    "IT": {"start": "09:00", "end": "18:00"},
    "ES": {"start": "09:00", "end": "18:00"},
    "CN": {"start": "09:00", "end": "18:00"},
    "JP": {"start": "09:00", "end": "18:00"},
    "KR": {"start": "09:00", "end": "18:00"},
    "AE": {"start": "08:00", "end": "17:00"},
    "UAE": {"start": "08:00", "end": "17:00"},
    "SA": {"start": "08:00", "end": "17:00"},
}

# Region-specific business days (1=Monday, 7=Sunday)
REGION_BUSINESS_DAYS = {
    "DEFAULT": [1, 2, 3, 4, 5],  # Monday to Friday
    
    # Middle East: Sunday to Thursday
    "AE": [7, 1, 2, 3, 4],
    "UAE": [7, 1, 2, 3, 4],
    "SA": [7, 1, 2, 3, 4],
    "QA": [7, 1, 2, 3, 4],
    "KW": [7, 1, 2, 3, 4],
    "BH": [7, 1, 2, 3, 4],
    "OM": [7, 1, 2, 3, 4],
    "EG": [7, 1, 2, 3, 4],
    "IL": [7, 1, 2, 3, 4],
}

def handle_api_response(status_code: int, body: dict) -> func.HttpResponse:
    """
    Helper function to return consistent API responses.
    """
    return func.HttpResponse(
        json.dumps(body),
        status_code=status_code,
        mimetype="application/json"
    )

def get_utc_offset_for_region(region: str) -> float:
    """
    Returns the UTC offset in hours for the given region.
    Supports both region codes and direct offset values.
    
    Args:
        region: Region code (e.g., "IN", "US") or direct offset (e.g., "+5.5", "-8", "5.5")
    
    Returns:
        float: UTC offset in hours
    """
    region_str = str(region).strip()
    
    # If it's a direct numeric offset (e.g., "5.5", "-8", "+5.5")
    if region_str.replace('+', '').replace('-', '').replace('.', '').isdigit():
        try:
            return float(region_str)
        except ValueError:
            pass
    
    # Otherwise, look it up in the region mapping
    return REGION_UTC_OFFSETS.get(region_str.upper(), 0)

def convert_to_regional_time(utc_datetime: datetime, region: str) -> datetime:
    """
    Converts UTC datetime to regional time using offset.
    
    Args:
        utc_datetime: UTC datetime to convert
        region: Region code or UTC offset
    
    Returns:
        datetime: Datetime in regional timezone
    """
    offset_hours = get_utc_offset_for_region(region)
    
    # If datetime is naive (no timezone), assume UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    
    # Convert to UTC if it has a different timezone
    if utc_datetime.tzinfo != timezone.utc:
        utc_datetime = utc_datetime.astimezone(timezone.utc)
    
    # Apply offset
    offset = timedelta(hours=offset_hours)
    regional_time = utc_datetime + offset
    
    return regional_time

def get_business_days_for_region(region: str) -> list:
    """
    Returns the business days for the given region.
    """
    region_upper = str(region).upper()
    return REGION_BUSINESS_DAYS.get(region_upper, REGION_BUSINESS_DAYS["DEFAULT"])

def is_business_day(date: datetime, region: str, business_days: list = None) -> bool:
    """
    Checks if the given date is a business day in the provided region.
    Converts UTC datetime to region time before checking.
    
    Args:
        date: UTC datetime to check
        region: Region code (e.g., "IN", "US") or UTC offset (e.g., "+5.5")
        business_days: Optional list of business days [1-7] where 1=Monday, 7=Sunday
                      If not provided, uses region-specific defaults
    """
    try:
        logging.info(f'is_business_day called with: date={date}, region={region}, business_days={business_days}')
        
        # Convert to regional time
        local_date = convert_to_regional_time(date, region)
        logging.info(f'Local date after conversion: {local_date}')
        
        # Get business days - use provided, or fall back to region defaults
        if business_days is None:
            business_days = get_business_days_for_region(region)
        
        # Convert business_days to Python weekday format (Monday=0, Sunday=6)
        # Input format: 1=Monday, 7=Sunday
        # Python format: Monday=0, Sunday=6
        python_business_days = [day - 1 if day < 7 else 6 for day in business_days]
        logging.info(f'Python business days: {python_business_days}')
        
        # Get the weekday (Monday=0, Sunday=6)
        weekday = local_date.weekday()
        logging.info(f'Current weekday: {weekday}')
        
        # Check if it's a business day
        result = weekday in python_business_days
        logging.info(f'is_business_day result: {result}')
        
        return result
    except Exception as e:
        logging.error(f'Error in is_business_day: {str(e)}')
        raise

def is_business_hour(date: datetime, region: str, 
                     start_time_str: str = None, 
                     end_time_str: str = None) -> bool:
    """
    Checks if the given time is within business hours in the provided region.
    Converts UTC datetime to region time before checking.
    
    Args:
        date: UTC datetime to check
        region: Region code (e.g., "IN", "US") or UTC offset (e.g., "+5.5")
        start_time_str: Optional custom start time in "HH:MM:SS" or "HH:MM" format
        end_time_str: Optional custom end time in "HH:MM:SS" or "HH:MM" format
    """
    try:
        logging.info(f'is_business_hour called with: date={date}, region={region}, start={start_time_str}, end={end_time_str}')
        
        # Convert to regional time
        local_date = convert_to_regional_time(date, region)
        logging.info(f'Local date after conversion: {local_date}')
        
        # Determine business hours
        if start_time_str and end_time_str:
            # Use custom business hours
            try:
                start_parts = start_time_str.split(':')
                end_parts = end_time_str.split(':')
                
                business_hours_start = time(
                    int(start_parts[0]), 
                    int(start_parts[1]), 
                    int(start_parts[2]) if len(start_parts) > 2 else 0
                )
                business_hours_end = time(
                    int(end_parts[0]), 
                    int(end_parts[1]), 
                    int(end_parts[2]) if len(end_parts) > 2 else 0
                )
            except (ValueError, IndexError) as e:
                logging.error(f'Failed to parse time strings: {str(e)}')
                # If parsing fails, use region defaults
                region_hours = get_business_hours_for_region(region)
                business_hours_start = datetime.strptime(region_hours["start"], "%H:%M").time()
                business_hours_end = datetime.strptime(region_hours["end"], "%H:%M").time()
        else:
            # Use region-specific business hours
            region_hours = get_business_hours_for_region(region)
            business_hours_start = datetime.strptime(region_hours["start"], "%H:%M").time()
            business_hours_end = datetime.strptime(region_hours["end"], "%H:%M").time()
        
        logging.info(f'Business hours: {business_hours_start} - {business_hours_end}')
        
        local_time = local_date.time()
        logging.info(f'Local time: {local_time}')
        
        # Check if local time is within business hours
        result = business_hours_start <= local_time < business_hours_end
        logging.info(f'is_business_hour result: {result}')
        
        return result
    except Exception as e:
        logging.error(f'Error in is_business_hour: {str(e)}')
        raise

def get_business_hours_for_region(region: str) -> dict:
    """
    Returns the business hours for the provided region.
    """
    region_upper = str(region).upper()
    return REGION_BUSINESS_HOURS.get(region_upper, REGION_BUSINESS_HOURS["DEFAULT"])

def get_holidays(region: str) -> list:
    """
    Returns a list of holidays for the provided region.
    This is a placeholder and should be modified to include actual 
    holiday data for the region.
    """
    return []

def get_supported_regions() -> dict:
    """
    Returns a dictionary of all supported regions with their offset and business hours.
    """
    return {
        region: {
            "utcOffset": REGION_UTC_OFFSETS.get(region, 0),
            "businessHours": REGION_BUSINESS_HOURS.get(region, REGION_BUSINESS_HOURS["DEFAULT"]),
            "businessDays": REGION_BUSINESS_DAYS.get(region, REGION_BUSINESS_DAYS["DEFAULT"])
        }
        for region in REGION_UTC_OFFSETS.keys()
    }