import logging
import json
import io
import pandas as pd
import azure.functions as func
import traceback
from datetime import datetime


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Asset Data Preparation function processing a request.')

    try:
        # Read Excel binary data directly from request body
        excel_binary = req.get_body()
        
        if not excel_binary:
            return func.HttpResponse(
                "Please pass Excel file in the request body",
                status_code=400
            )
        
        # Get cycle name, error_callback, and splitGroups from query parameters
        cycle_name = req.params.get('cycleName')
        error_callback = req.params.get('error_callback', 'false').lower() == 'true'
        split_groups = req.params.get('splitGroups', 'false').lower() == 'true'
        
        logging.info(f"Received cycle name: {cycle_name}")
        logging.info(f"Error callback mode: {error_callback}")
        logging.info(f"Split groups mode: {split_groups}")
        
        # Convert binary data to DataFrame using pandas
        df = pd.read_excel(io.BytesIO(excel_binary), engine='openpyxl')
        logging.info("Successfully read Excel file using openpyxl engine")
        
        # Convert DataFrame to list of dictionaries for processing
        excel_data = df.to_dict('records')
        
        logging.info(f"Processing {len(excel_data)} assets from the Excel data.")
        
        # Process the data with error_callback and split_groups flags
        result = process_asset_data(excel_data, cycle_name, error_callback, split_groups)
        
        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error processing asset data: {str(traceback.format_exc())}")
        print(traceback.format_exc())
        return func.HttpResponse(
            f"Error processing asset data: {str(e)}",
            status_code=500
        )


def process_asset_data(excel_data, cycle_name=None, error_callback=False, split_groups=False):
    """
    Process the Excel data to prepare assets for tagging and grouping
    
    Args:
        excel_data: List of dictionaries representing Excel rows
        cycle_name: Name of the cycle for group creation (optional)
        error_callback: Boolean flag to determine filtering logic
        split_groups: Boolean flag to split into Mey Diageo and Diageo groups
    """
    # Initialize output containers
    mey_diageo_ips = []
    diageo_ips = []
    all_ips = []
    
    # Process each asset in the data
    for asset in excel_data:
        ip = asset.get('IP Address')
        if not ip:
            continue
        
        # Determine if IP should be skipped based on error_callback mode
        should_skip = should_skip_ip(asset, error_callback)
        
        if should_skip:
            logging.info(f"Skipping IP {ip} based on filtering rules")
            continue
        
        ip_str = str(ip)
        
        # If split_groups is enabled, categorize by Value Stream
        if split_groups:
            value_stream = str(asset.get('Value Stream', '')).strip()
            
            # Determine which group this IP belongs to based on Value Stream
            if value_stream.lower() == 'mey diageo':
                mey_diageo_ips.append(ip_str)
                logging.info(f"Added IP {ip_str} to Mey Diageo group (Value Stream: {value_stream})")
            else:
                diageo_ips.append(ip_str)
                logging.info(f"Added IP {ip_str} to Diageo group (Value Stream: {value_stream})")
        else:
            # Add to single group
            all_ips.append(ip_str)
    
    # Create groups based on split_groups flag
    current_date = datetime.now()
    if not cycle_name:
        # Create a default cycle name in format Cycle-Month-Year if none provided
        cycle_name = f"Cycle-{current_date.strftime('%B-%Y')}"
    
    groups_for_creation = []
    
    if split_groups:
        # Create two separate groups
        if mey_diageo_ips:
            groups_for_creation.append({
                "name": f"{cycle_name}_MeyDiageo",
                "ips": mey_diageo_ips
            })
            logging.info(f"Created Mey Diageo group with {len(mey_diageo_ips)} IPs")
        
        if diageo_ips:
            groups_for_creation.append({
                "name": f"{cycle_name}_Diageo",
                "ips": diageo_ips
            })
            logging.info(f"Created Diageo group with {len(diageo_ips)} IPs")
    else:
        # Create single group (original behavior)
        groups_for_creation.append({
            "name": f"{cycle_name}-{current_date.strftime('%H%M%S')}",
            "ips": all_ips
        })
        logging.info(f"Created single group '{cycle_name}' with {len(all_ips)} IPs")
    
    return {
        "groupsForCreation": groups_for_creation
    }


def should_skip_ip(asset, error_callback):
    """
    Determine if an IP should be skipped based on Skip Scan and Error/Corrected columns
    
    Args:
        asset: Dictionary representing a single asset row
        error_callback: Boolean flag for filtering mode
        
    Returns:
        Boolean: True if IP should be skipped, False if it should be included
    """
    # Get Skip Scan value and normalize it
    skip_scan = asset.get('Skip Scan')
    skip_scan_is_true = False
    skip_scan_is_empty = skip_scan is None or str(skip_scan).strip() == '' or pd.isna(skip_scan)
    
    if not skip_scan_is_empty:
        skip_scan_str = str(skip_scan).strip().lower()
        skip_scan_is_true = skip_scan_str == 'true' or skip_scan_str == '1.0' or skip_scan_str == '1'
    
    # If error_callback is False, ONLY check Skip Scan column
    if not error_callback:
        # Skip if Skip Scan = True, Include if Skip Scan = False or empty
        if skip_scan_is_true:
            logging.info(f"error_callback=False: Skipping because Skip Scan=True")
            return True
        else:
            return False
    
    # If error_callback is True, check both Skip Scan and Error/Corrected columns
    error_corrected = asset.get('Error/Corrected')
    error_corrected_str = str(error_corrected).strip() if error_corrected is not None and not pd.isna(error_corrected) else ''
    error_corrected_is_empty = error_corrected_str == ''
    error_corrected_is_error = error_corrected_str.lower() == 'error'
    error_corrected_is_corrected = error_corrected_str.lower() == 'corrected'
    
    # Apply the filtering rules:
    # 1. Skip Scan = True AND Error/Corrected = Error -> SKIP
    if skip_scan_is_true and error_corrected_is_error:
        logging.info(f"Rule 1: Skip Scan=True AND Error/Corrected=Error")
        return True
    
    # 2. Skip Scan = True AND Error/Corrected = blank/empty -> SKIP
    if skip_scan_is_true and error_corrected_is_empty:
        logging.info(f"Rule 2: Skip Scan=True AND Error/Corrected=empty")
        return True
    
    # 3. Skip Scan = True AND Error/Corrected = Corrected -> SKIP
    if skip_scan_is_true and error_corrected_is_corrected:
        logging.info(f"Rule 3: Skip Scan=True AND Error/Corrected=Corrected")
        return True
    
    # 4. Skip Scan = blank/empty AND Error/Corrected = Error -> SKIP
    if skip_scan_is_empty and error_corrected_is_error:
        logging.info(f"Rule 4: Skip Scan=empty AND Error/Corrected=Error")
        return True
    
    # 5. Skip Scan = blank/empty AND Error/Corrected = Corrected -> INCLUDE
    if skip_scan_is_empty and error_corrected_is_corrected:
        logging.info(f"Rule 5: Skip Scan=empty AND Error/Corrected=Corrected - INCLUDE")
        return False
    
    # Default: include the IP if none of the skip conditions are met
    return False