import os
import io
import re
import logging
import base64
import requests
import xml.etree.ElementTree as ET
import fnmatch

import pandas as pd

from urllib.parse import quote

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
def _extract_ips_from_simple_return(simple_return_xml: str) -> list[str]:
    """
    Extract IPv4 addresses mentioned in the Qualys SIMPLE_RETURN <TEXT>.
    Works with valid XML or raw string; returns de-duplicated ordered list.
    """
    text = ""
    if simple_return_xml:
        try:
            root = ET.fromstring(simple_return_xml)
            node = root.find(".//TEXT")
            text = node.text if node is not None and node.text else simple_return_xml
        except ET.ParseError:
            text = simple_return_xml

    # Find IPv4 candidates
    ips = re.findall(r"(?:\d{1,3}\.){3}\d{1,3}", text or "")
    # De-dup while preserving order
    seen = set()
    ordered = []
    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            ordered.append(ip)
    return ordered

def _ensure_two_columns_at_end(df: pd.DataFrame, col1: str, col2: str) -> pd.DataFrame:
    """
    Guarantee that col1 and col2 exist and are the LAST two columns.
    Do not disturb the original order of other columns.
    """
    work = df.copy()
    if col1 not in work.columns:
        work[col1] = ""
    if col2 not in work.columns:
        work[col2] = ""
    cols = [c for c in work.columns if c not in (col1, col2)] + [col1, col2]
    return work[cols]

def _apply_error_flags(df: pd.DataFrame, bad_ips: set[str]) -> pd.DataFrame:
    """
    Set Error/Corrected to 'Error' and Error Remarks to 'not in user account scope'
    only for rows whose IP Address appears in bad_ips; others remain blank.
    """
    out = df.copy()
    out.columns = out.columns.str.strip()

    if "IP Address" not in out.columns:
        raise ValueError("IP Address column not found in Excel data.")

    # Ensure columns exist at end
    out = _ensure_two_columns_at_end(out, "Error/Corrected", "Error Remarks")

    # Compute updates
    ip_series = out["IP Address"].astype(str).str.strip()
    is_error = ip_series.isin(bad_ips)

    out.loc[is_error, "Error/Corrected"] = "Error"
    out.loc[is_error, "Error Remarks"] = "not in user account scope"

    # Non-matching rows remain blank by design
    return out

def compare_and_update_tags(new_df, existing_excel_content, comparison_column='Tags', key_columns=['Name', 'IP Address']):
    """
    Compare and update tags from existing Excel file
    """
    try:
        logging.info("=== STARTING TAG COMPARISON PROCESS ===")
        
        # Decode and read existing Excel file
        existing_excel_bytes = base64.b64decode(existing_excel_content)
        existing_df = pd.read_excel(io.BytesIO(existing_excel_bytes))
        
        # Clean column names (remove extra spaces)
        existing_df.columns = existing_df.columns.str.strip()
        new_df.columns = new_df.columns.str.strip()
        
        logging.info(f"Existing Excel file loaded successfully - Rows: {len(existing_df)}")
        logging.info(f"New Excel file has {len(new_df)} rows")
        logging.info(f"Looking for comparison column: '{comparison_column}'")
        logging.info(f"Key columns for matching: {key_columns}")
        
        # Create a lookup dictionary from existing data for Tags
        existing_lookup = {}
        if comparison_column in existing_df.columns:
            logging.info(f"Found '{comparison_column}' column in existing Excel file")
            tag_entries_count = 0

            for idx, row in existing_df.iterrows():
                # Create composite key using available key columns
                available_key_cols = [col for col in key_columns if col in existing_df.columns]
                if available_key_cols:
                    key_values = []
                    for col in available_key_cols:
                        val = row[col]
                        if pd.isna(val):
                            key_values.append('')
                        else:
                            key_values.append(str(val).strip().lower())

                    composite_key = '|'.join(key_values)
                    tag_value = row[comparison_column] if not pd.isna(row[comparison_column]) else ''

                    if tag_value:  # Only store non-empty tags
                        try:
                            tag_str = str(tag_value).strip()
                            # Convert to float first, then to int if it's a whole number
                            tag_float = float(tag_str)
                            if tag_float.is_integer():
                                tag_value = int(tag_float)
                                logging.info(f"Converted tag value to integer: {tag_value} for key: {composite_key}")
                            else:
                                tag_value = tag_float
                                logging.info(f"Tag value is a non-integer float: {tag_value} for key: {composite_key}")
                        except (ValueError, TypeError):
                            logging.info(f"Keeping original tag value: {tag_value} for key: {composite_key}")

                        existing_lookup[composite_key] = tag_value
                        tag_entries_count += 1

                        if tag_entries_count <= 5:  # Log first 5 entries for debugging
                            logging.info(f"Sample lookup entry #{tag_entries_count}: Key='{composite_key}' -> Tag='{tag_value}'")
        else:
            logging.warning(f"Column '{comparison_column}' NOT found in existing Excel file")
            logging.info(f"Available columns in existing file: {list(existing_df.columns)}")

        logging.info(f"Created lookup dictionary with {len(existing_lookup)} tag entries")

        # Ensure Tags column exists in new DataFrame
        if comparison_column not in new_df.columns:
            new_df[comparison_column] = ''
            logging.info(f"Added new '{comparison_column}' column to DataFrame")
        else:
            logging.info(f"'{comparison_column}' column already exists in DataFrame")

        # Update Tags column in new DataFrame
        updated_count = 0
        matched_entries = []
        unmatched_entries = []
        
        logging.info("=== STARTING TAG UPDATE PROCESS ===")
        
        for index, row in new_df.iterrows():
            # Create composite key for lookup
            available_key_cols = [col for col in key_columns if col in new_df.columns]
            if available_key_cols:
                key_values = []
                for col in available_key_cols:
                    val = row[col]
                    if pd.isna(val):
                        key_values.append('')
                    else:
                        key_values.append(str(val).strip().lower())
                
                composite_key = '|'.join(key_values)
                
                # Look up existing tags and update
                if composite_key in existing_lookup:
                    existing_tags = existing_lookup[composite_key]
                    new_df.at[index, comparison_column] = existing_tags
                    updated_count += 1
                    matched_entries.append({
                        'index': index,
                        'key': composite_key,
                        'tag': existing_tags
                    })
                    
                    if updated_count <= 5:  # Log first 5 updates for debugging
                        logging.info(f"Update #{updated_count}: Row {index} -> Key: '{composite_key}' -> Tag: '{existing_tags}'")
                else:
                    unmatched_entries.append({
                        'index': index,
                        'key': composite_key
                    })

        logging.info(f"=== TAG UPDATE SUMMARY ===")
        logging.info(f"Successfully updated {updated_count} rows with existing tags")
        logging.info(f"Matched entries: {len(matched_entries)}")
        logging.info(f"Unmatched entries: {len(unmatched_entries)}")
        
        if unmatched_entries and len(unmatched_entries) <= 10:
            logging.info("Sample unmatched keys:")
            for entry in unmatched_entries[:5]:
                logging.info(f"  Unmatched key: '{entry['key']}'")
        
        return new_df, updated_count
        
    except Exception as e:
        logging.error(f"ERROR in tag comparison: {str(e)}", exc_info=True)
        return new_df, 0

def get_qualys_tags(ip_addresses, qualys_username, qualys_password, qualys_api_url="https://qualysapi.qualys.eu"):
    """
    Get tags from Qualys API for given IP addresses
    
    Args:
        ip_addresses: List of IP addresses to query
        qualys_username: Qualys API username
        qualys_password: Qualys API password
        qualys_api_url: Qualys API base URL
    
    Returns:
        Dictionary mapping IP addresses to their criticality tags
    """
    if not ip_addresses or not qualys_username or not qualys_password:
        logging.warning("Qualys API call skipped - missing parameters")
        return {}
    
    try:
        logging.info(f"=== STARTING QUALYS API CALL ===")
        logging.info(f"Querying {len(ip_addresses)} IP addresses")
        logging.info(f"Qualys API URL: {qualys_api_url}")
        logging.info(f"Sample IPs to query: {ip_addresses[:5] if len(ip_addresses) > 5 else ip_addresses}")
        
        # Join IPs with comma and URL encode
        ips_param = ','.join(ip_addresses)
        encoded_ips = quote(ips_param)
        
        # Construct API URL
        api_url = f"{qualys_api_url}/api/2.0/fo/asset/host/?action=list&ips={encoded_ips}&show_tags=1"
        
        # Prepare headers and authentication
        headers = {
            'X-Requested-With': 'Security Automation',
        }
        
        # Make API request with basic authentication
        auth = (qualys_username, qualys_password)
        
        logging.info(f"Making Qualys API request...")
        response = requests.get(api_url, headers=headers, auth=auth, timeout=60)
        
        logging.info(f"Qualys API response status: {response.status_code}")
        
        if response.status_code != 200:
            logging.error(f"Qualys API request failed with status {response.status_code}")
            logging.error(f"Response text: {response.text[:500]}...")  # Log first 500 chars
            return {}
        
        logging.info("Qualys API call successful, parsing XML response...")
        
        # Parse XML response
        return parse_qualys_xml_response(response.text)
        
    except Exception as e:
        logging.error(f"ERROR calling Qualys API: {str(e)}", exc_info=True)
        return {}

def parse_qualys_xml_response(xml_content):
    """
    Parse Qualys XML response and extract criticality numbers for each IP
    
    Args:
        xml_content: XML string response from Qualys API
    
    Returns:
        Dictionary mapping IP addresses to their criticality numbers (e.g., "5")
    """
    ip_tags = {}
    
    try:
        logging.info("=== PARSING QUALYS XML RESPONSE ===")
        
        # Parse XML
        root = ET.fromstring(xml_content)
        
        # Find all HOST elements
        hosts_found = 0
        hosts_with_tags = 0
        hosts_with_criticality = 0
        
        for host in root.findall('.//HOST'):
            hosts_found += 1
            ip_elem = host.find('IP')
            if ip_elem is None:
                continue
                
            ip_address = ip_elem.text.strip()
            
            # Look for tags
            tags_elem = host.find('TAGS')
            if tags_elem is not None:
                hosts_with_tags += 1
                logging.info(f"Found tags for IP: {ip_address}")
                
                # Find criticality tag
                for tag in tags_elem.findall('TAG'):
                    name_elem = tag.find('NAME')
                    if name_elem is not None:
                        tag_name = name_elem.text.strip() if name_elem.text else ""
                        
                        # Check if this is a criticality tag (case-insensitive)
                        if tag_name.lower().startswith('criticality'):
                            hosts_with_criticality += 1
                            # Extract the criticality number using regex
                            criticality_match = re.search(r'criticality\s+(\d+)', tag_name, re.IGNORECASE)
                            if criticality_match:
                                criticality_number = int(criticality_match.group(1))  # Convert to int
                                ip_tags[ip_address] = criticality_number
                                logging.info(f"SUCCESS: Found criticality {criticality_number} for {ip_address} (from tag: {tag_name})")
                            else:
                                # If we can't extract number, store the full tag for debugging
                                ip_tags[ip_address] = tag_name
                                logging.warning(f"Could not extract criticality number from tag '{tag_name}' for {ip_address}")
                            break  # Take the first criticality tag found
            else:
                logging.info(f"No tags found for IP: {ip_address}")
        
        logging.info(f"=== QUALYS XML PARSING SUMMARY ===")
        logging.info(f"Total hosts found: {hosts_found}")
        logging.info(f"Hosts with tags: {hosts_with_tags}")
        logging.info(f"Hosts with criticality tags: {hosts_with_criticality}")
        logging.info(f"IP addresses with extracted tags: {len(ip_tags)}")
        
        return ip_tags
        
    except Exception as e:
        logging.error(f"ERROR parsing Qualys XML response: {str(e)}", exc_info=True)
        return {}

def update_missing_tags_with_qualys(df, comparison_column='Tags', qualys_username=None, qualys_password=None, qualys_api_url="https://qualysapi.qualys.eu"):
    """
    Update missing tags by calling Qualys API
    
    Args:
        df: DataFrame with Tags column
        comparison_column: Name of the tags column
        qualys_username: Qualys API username
        qualys_password: Qualys API password
        qualys_api_url: Qualys API base URL
    
    Returns:
        Tuple of (updated_df, updated_count, missing_ips_list)
    """
    logging.info("=== STARTING QUALYS TAG UPDATE PROCESS ===")
    
    # Helper function to check if a tag value is missing/empty
    def is_empty_tag(value):
        """Check if a tag value should be considered empty/missing"""
        if pd.isna(value):
            return True
        str_val = str(value).strip().lower()
        return str_val in ['', 'nan', 'none', 'null']
    
    # Ensure the comparison column exists and convert to string
    if comparison_column not in df.columns:
        df[comparison_column] = ''
        logging.info(f"Added missing '{comparison_column}' column")
    
    df[comparison_column] = df[comparison_column].astype(str)
    
    # Initial missing IPs detection - BEFORE any Qualys processing
    initial_missing_ips = []
    for idx, row in df.iterrows():
        tag_value = row[comparison_column]
        if is_empty_tag(tag_value):
            initial_missing_ips.append(row['IP Address'])
    
    logging.info(f"Initial missing IPs count: {len(initial_missing_ips)}")
    logging.info(f"DataFrame has {len(df)} total rows")
    
    if not qualys_username or not qualys_password:
        logging.warning("Qualys credentials not provided, skipping Qualys API call")
        logging.info(f"Returning {len(initial_missing_ips)} IPs with missing tags (no Qualys update performed)")
        return df, 0, initial_missing_ips
    
    try:
        logging.info(f"Found {len(initial_missing_ips)} IPs with missing tags in DataFrame")
        
        if len(initial_missing_ips) <= 10:
            logging.info(f"Missing IPs: {initial_missing_ips}")
        else:
            logging.info(f"Sample missing IPs: {initial_missing_ips[:10]}... (showing first 10 of {len(initial_missing_ips)})")
        
        if not initial_missing_ips:
            logging.info("No missing tags found, skipping Qualys API call")
            return df, 0, []
        
        logging.info(f"Proceeding with Qualys API call for {len(initial_missing_ips)} IPs")
        
        # Call Qualys API in batches (max 100 IPs per request to avoid URL length limits)
        batch_size = 100
        all_qualys_tags = {}
        
        num_batches = (len(initial_missing_ips) + batch_size - 1) // batch_size
        logging.info(f"Processing in {num_batches} batches of max {batch_size} IPs each")
        
        for i in range(0, len(initial_missing_ips), batch_size):
            batch_num = (i // batch_size) + 1
            batch_ips = initial_missing_ips[i:i + batch_size]
            logging.info(f"Processing batch {batch_num}/{num_batches} with {len(batch_ips)} IPs")
            
            batch_tags = get_qualys_tags(batch_ips, qualys_username, qualys_password, qualys_api_url)
            all_qualys_tags.update(batch_tags)
            
            logging.info(f"Batch {batch_num} completed: {len(batch_tags)} tags retrieved")
        
        logging.info(f"=== QUALYS API BATCH PROCESSING COMPLETE ===")
        logging.info(f"Total tags retrieved from Qualys: {len(all_qualys_tags)}")
        
        # Update DataFrame with Qualys tags - ONLY for IPs that were initially missing
        updated_count = 0
        qualys_updates = []
        
        for index, row in df.iterrows():
            ip_address = row['IP Address']
            current_tag = row[comparison_column]
            
            # Only update if this IP was in the initial missing list AND we got a tag from Qualys
            if ip_address in initial_missing_ips and ip_address in all_qualys_tags:
                qualys_tag = all_qualys_tags[ip_address]  # This is already an integer from parse_qualys_xml_response
                df.at[index, comparison_column] = qualys_tag
                updated_count += 1
                qualys_updates.append({
                    'index': index,
                    'ip': ip_address,
                    'tag': qualys_tag
                })
                
                if updated_count <= 5:  # Log first 5 updates
                    logging.info(f"Qualys update #{updated_count}: Row {index} -> IP: {ip_address} -> Tag: {qualys_tag} (Type: {type(qualys_tag)})")
        
        # Final missing IPs detection - AFTER Qualys updates
        final_missing_ips = []
        for idx, row in df.iterrows():
            tag_value = row[comparison_column]
            if is_empty_tag(tag_value):
                final_missing_ips.append(row['IP Address'])
                # Set empty cells to empty string instead of 'nan'
                df.at[idx, comparison_column] = ''
        
        logging.info(f"=== QUALYS UPDATE SUMMARY ===")
        logging.info(f"Initial missing IPs: {len(initial_missing_ips)}")
        logging.info(f"Tags retrieved from Qualys: {len(all_qualys_tags)}")
        logging.info(f"Tags updated from Qualys API: {updated_count}")
        logging.info(f"Final missing IPs: {len(final_missing_ips)}")
        
        # Debug: Show detailed comparison
        logging.info("=== DETAILED MISSING IPs ANALYSIS ===")
        for ip in initial_missing_ips:
            if ip in all_qualys_tags:
                logging.info(f"  {ip}: Retrieved from Qualys -> {all_qualys_tags[ip]}")
            else:
                logging.info(f"  {ip}: Not found in Qualys (still missing)")
        
        if final_missing_ips and len(final_missing_ips) <= 20:
            logging.info(f"Final missing IPs list: {final_missing_ips}")
        elif final_missing_ips:
            logging.info(f"Sample final missing IPs: {final_missing_ips[:10]}... (showing first 10 of {len(final_missing_ips)})")
        
        return df, updated_count, final_missing_ips
        
    except Exception as e:
        logging.error(f"ERROR in Qualys tag update: {str(e)}", exc_info=True)
        # Return initial missing IPs if there was an error
        return df, 0, initial_missing_ips

def matches_pattern(value, pattern):
    """
    Check if a value matches a pattern with wildcard support
    
    Args:
        value: The value to check
        pattern: The pattern to match against (can contain * and ? wildcards)
    
    Returns:
        Boolean indicating if the value matches the pattern
    """
    if not pattern:
        return False
    
    # Convert both to strings and strip whitespace
    value_str = str(value).strip()
    pattern_str = str(pattern).strip()
    
    # If no wildcards, do exact match (case-insensitive)
    if '*' not in pattern_str and '?' not in pattern_str:
        return value_str.lower() == pattern_str.lower()
    
    # Use fnmatch for wildcard matching (case-insensitive)
    return fnmatch.fnmatch(value_str.lower(), pattern_str.lower())

def apply_filter_conditions(df, conditions, filter_type="include"):
    """
    Apply filter conditions to DataFrame with wildcard support
    - Include: AND logic - keep rows where ALL conditions are met
    - Exclude: OR logic - remove rows where ANY condition is met
    - Supports wildcards: * (matches any sequence of characters) and ? (matches any single character)
    - Works with ALL columns in the DataFrame (no field mapping restrictions)
    
    Args:
        df: DataFrame to filter
        conditions: List of filter conditions
        filter_type: "include" or "exclude"
    
    Returns:
        Filtered DataFrame
    
    Examples:
        - "Support group=DIN*" matches "DIN_EC_Security Support", "DIN_NOC_Support", etc.
        - "Name=Server*" matches "ServerA", "ServerB", "Server123", etc.
        - "Status=*Active*" matches "Pre-Active", "Active", "Semi-Active", etc.
        - "Code=A?C" matches "ABC", "AXC", "A1C", etc.
    """
    if not conditions:
        return df
    
    df_filtered = df.copy()
    
    if filter_type == "include":
        # INCLUDE: AND logic - all conditions must be true
        mask = pd.Series([True] * len(df_filtered), index=df_filtered.index)
        
        for condition in conditions:
            field = condition['field']
            value = condition['value']
            
            if field not in df_filtered.columns:
                logging.warning(f"Column '{field}' not found in data. Available columns: {list(df_filtered.columns)}")
                logging.warning(f"Skipping condition: {field}={value}")
                continue
            
            # Check if this is a wildcard pattern
            if '*' in value or '?' in value:
                logging.info(f"Applying wildcard pattern: {field} matches '{value}'")
                condition_mask = df_filtered[field].apply(lambda x: matches_pattern(x, value))
                matched_count = condition_mask.sum()
                logging.info(f"Wildcard condition {field}='{value}': {matched_count} rows match this pattern")
                
                # Log some sample matches for debugging (first 5)
                if matched_count > 0:
                    sample_matches = df_filtered[condition_mask][field].head(5).tolist()
                    logging.info(f"Sample matches: {sample_matches}")
            else:
                # Exact match (case-insensitive)
                condition_mask = df_filtered[field].astype(str).str.lower().str.strip() == value.lower().strip()
                logging.info(f"Applied exact condition {field}='{value}': {condition_mask.sum()} rows match")
            
            mask = mask & condition_mask  # AND logic
        
        df_filtered = df_filtered[mask]
        logging.info(f"INCLUDE filter: Kept {len(df_filtered)} rows that satisfy ALL conditions")
        
    else:  # exclude
        # EXCLUDE: OR logic - any condition being true excludes the row
        mask = pd.Series([False] * len(df_filtered), index=df_filtered.index)
        
        for condition in conditions:
            field = condition['field']
            value = condition['value']
            
            if field not in df_filtered.columns:
                logging.warning(f"Column '{field}' not found in data. Available columns: {list(df_filtered.columns)}")
                logging.warning(f"Skipping condition: {field}={value}")
                continue
            
            # Check if this is a wildcard pattern
            if '*' in value or '?' in value:
                logging.info(f"Applying wildcard exclusion pattern: {field} matches '{value}'")
                condition_mask = df_filtered[field].apply(lambda x: matches_pattern(x, value))
                matched_count = condition_mask.sum()
                logging.info(f"Wildcard exclusion condition {field}='{value}': {matched_count} rows match this pattern")
                
                # Log some sample matches for debugging (first 5)
                if matched_count > 0:
                    sample_matches = df_filtered[condition_mask][field].head(5).tolist()
                    logging.info(f"Sample exclusion matches: {sample_matches}")
            else:
                # Exact match (case-insensitive)
                condition_mask = df_filtered[field].astype(str).str.lower().str.strip() == value.lower().strip()
                logging.info(f"Applied exact exclusion condition {field}='{value}': {condition_mask.sum()} rows match")
            
            mask = mask | condition_mask  # OR logic
        
        num_excluded = mask.sum()
        df_filtered = df_filtered[~mask]
        logging.info(f"EXCLUDE filter: Removed {num_excluded} rows matching ANY exclusion condition, kept {len(df_filtered)} rows")
    
    return df_filtered

def remove_duplicate_ips(df):
    """
    Remove duplicate IP addresses, keeping the first occurrence
    
    Args:
        df: DataFrame with IP Address column
    
    Returns:
        DataFrame with unique IP addresses
    """
    if 'IP Address' not in df.columns:
        return df
    
    original_count = len(df)
    
    # Remove duplicates based on IP Address, keeping first occurrence
    df_unique = df.drop_duplicates(subset=['IP Address'], keep='first')
    
    removed_count = original_count - len(df_unique)
    logging.info(f"Removed {removed_count} duplicate IP addresses. Unique IPs: {len(df_unique)}")
    
    return df_unique

def parse_filter_expression(filter_string):
    """
    Parse ServiceNow-style filter expressions like "install_status=Decommissioned^operational_status=Operational"
    Now supports wildcard patterns like "Support group=DIN*"
    
    Returns:
        List of conditions: [{'field': 'install_status', 'value': 'Decommissioned'}, ...]
    
    Examples:
        - "Support group=DIN*" -> [{'field': 'Support group', 'value': 'DIN*'}]
        - "Name=Server*^Status=Active" -> [{'field': 'Name', 'value': 'Server*'}, {'field': 'Status', 'value': 'Active'}]
    """
    if not filter_string:
        return []
    
    conditions = []
    # Split by ^ (AND operator)
    filter_parts = filter_string.split('^')
    
    for part in filter_parts:
        if '=' in part:
            field, value = part.split('=', 1)
            conditions.append({
                'field': field.strip(),
                'value': value.strip()
            })
    
    return conditions

def encode_excel_data(
    excel_file_content,
    include_filter=None,
    exclude_filter=None,
    existing_excel_content=None,
    enable_tag_comparison=False,
    add_skip_status=False,
    comparison_column='Tags',
    key_columns=['Name', 'IP Address']
):
    """
    Process Excel data with include/exclude filtering and IP processing:
    1. Read the Excel file
    2. Apply include filter (keep rows that satisfy conditions) - supports wildcards
    3. Apply exclude filter (remove rows that satisfy conditions) - supports wildcards
    4. Process IP addresses (remove Dynamic, split multiple IPs)
    5. Remove duplicate IP addresses
    6. Add Skip Scan column if requested
    7. Compare and update Tags if requested
    8. Update missing tags using Qualys API if requested
    9. Return processed data in Excel format

    Wildcard Support:
    - Use * to match any sequence of characters
    - Use ? to match any single character
    """

    try:
        logging.info("=== STARTING EXCEL DATA PROCESSING ===")

        # ============================================================
        # LOAD EXCEL
        # ============================================================

        excel_buffer = io.BytesIO(excel_file_content)

        df = pd.read_excel(
            excel_buffer,
            engine='openpyxl'
        )

        logging.info(
            f"Original Excel data loaded successfully: "
            f"{len(df)} rows, {len(df.columns)} columns"
        )

        logging.info(
            f"Column names: {list(df.columns)}"
        )

        # ============================================================
        # STEP 1: APPLY INCLUDE FILTER
        # ============================================================

        if include_filter:

            include_conditions = parse_filter_expression(
                include_filter
            )

            logging.info(
                "=== APPLYING INCLUDE FILTER ==="
            )

            logging.info(
                f"Include filter: {include_filter}"
            )

            logging.info(
                f"Parsed conditions: {include_conditions}"
            )

            df = apply_filter_conditions(
                df,
                include_conditions,
                "include"
            )

            logging.info(
                f"After INCLUDE filtering: "
                f"{len(df)} rows remaining"
            )

        # ============================================================
        # STEP 2: APPLY EXCLUDE FILTER
        # ============================================================

        if exclude_filter:

            exclude_conditions = parse_filter_expression(
                exclude_filter
            )

            logging.info(
                "=== APPLYING EXCLUDE FILTER ==="
            )

            logging.info(
                f"Exclude filter: {exclude_filter}"
            )

            logging.info(
                f"Parsed conditions: {exclude_conditions}"
            )

            df = apply_filter_conditions(
                df,
                exclude_conditions,
                "exclude"
            )

            logging.info(
                f"After EXCLUDE filtering: "
                f"{len(df)} rows remaining"
            )

        # ============================================================
        # STEP 3: IP ADDRESS PROCESSING
        # ============================================================

        logging.info(
            "=== STARTING IP ADDRESS PROCESSING ==="
        )

        if 'IP Address' not in df.columns:

            logging.error(
                "'IP Address' column not found in DataFrame"
            )

            return {
                'success': False,
                'error': "'IP Address' column not found"
            }

        expanded_rows = []

        skipped_dynamic = 0
        skipped_empty = 0
        processed_ips = 0

        for row_idx, row in df.iterrows():

            ip_field = str(
                row['IP Address']
            ).strip()

            # --------------------------------------------------------
            # Skip empty, NaN, or Dynamic values
            # --------------------------------------------------------

            if (
                pd.isna(row['IP Address'])
                or ip_field.lower() in [
                    "dynamic",
                    "nan",
                    ""
                ]
            ):

                if ip_field.lower() == "dynamic":

                    skipped_dynamic += 1

                else:

                    skipped_empty += 1

                continue

            # --------------------------------------------------------
            # Clean NAT label and whitespace
            # --------------------------------------------------------

            cleaned = re.sub(
                r'NAT IP:\s*',
                '',
                ip_field,
                flags=re.IGNORECASE
            )

            cleaned = re.sub(
                r'\s+',
                ' ',
                cleaned
            ).strip()

            # --------------------------------------------------------
            # Extract valid IPv4 addresses
            # --------------------------------------------------------

            ip_list = re.findall(
                r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[1]?[0-9][0-9]?)\b',
                cleaned
            )

            # --------------------------------------------------------
            # No valid IPs
            # --------------------------------------------------------

            if not ip_list:
                continue

            # --------------------------------------------------------
            # Create separate rows for every IP
            # --------------------------------------------------------

            for ip in ip_list:

                new_row = row.copy()

                new_row['IP Address'] = ip.strip()

                expanded_rows.append(
                    new_row
                )

                processed_ips += 1

        logging.info(
            "IP Processing Summary:"
        )

        logging.info(
            f"  - Skipped 'Dynamic' entries: "
            f"{skipped_dynamic}"
        )

        logging.info(
            f"  - Skipped empty/NaN entries: "
            f"{skipped_empty}"
        )

        logging.info(
            f"  - Valid IPs processed: "
            f"{processed_ips}"
        )

        # ============================================================
        # NO VALID IPs
        # ============================================================

        if not expanded_rows:

            logging.warning(
                "No valid IP addresses found after filtering "
                "and processing"
            )

            return {
                'success': True,
                'excel_data': b'',
                'row_count': 0,
                'message':
                    'No valid IP addresses found after filtering'
            }

        result_df = pd.DataFrame(
            expanded_rows
        )

        logging.info(
            f"After IP processing: "
            f"{len(result_df)} rows"
        )

        # ============================================================
        # STEP 4: REMOVE DUPLICATE IP ADDRESSES
        # ============================================================

        logging.info(
            "=== REMOVING DUPLICATE IP ADDRESSES ==="
        )

        result_df = remove_duplicate_ips(
            result_df
        )

        # ============================================================
        # STEP 5: ADD SKIP SCAN COLUMN
        # ============================================================

        if add_skip_status:

            result_df['Skip Scan'] = ''

            logging.info(
                "Added 'Skip Scan' column "
                "with default value empty string"
            )

        # ============================================================
        # STEP 6: COMPARE AND UPDATE TAGS
        # ============================================================

        updated_count = 0

        if (
            enable_tag_comparison
            and existing_excel_content
        ):

            logging.info(
                "=== STARTING TAG COMPARISON "
                "WITH EXISTING EXCEL ==="
            )

            result_df, updated_count = (
                compare_and_update_tags(
                    result_df,
                    existing_excel_content,
                    comparison_column,
                    key_columns
                )
            )

            logging.info(
                f"Tag comparison completed - "
                f"Updated {updated_count} records "
                f"from existing Excel"
            )

        # ============================================================
        # STEP 7: GET QUALYS CREDENTIALS FROM KEY VAULT
        # ============================================================

        qualys_updated_count = 0
        final_missing_ips = []

        logging.info(
            "=== RETRIEVING QUALYS CREDENTIALS "
            "FROM AZURE KEY VAULT ==="
        )

        # ------------------------------------------------------------
        # Get Key Vault URL from Function App setting
        # ------------------------------------------------------------

        key_vault_url = "https://key-vault-IVM.vault.azure.net/"

        if not key_vault_url:

            raise ValueError(
                "KEY_VAULT_URL is not configured "
                "in Function App settings."
            )

        logging.info(
            f"Key Vault URL configured: "
            f"{key_vault_url}"
        )

        # ------------------------------------------------------------
        # Use Function App Managed Identity
        # ------------------------------------------------------------

        credential = DefaultAzureCredential()

        secret_client = SecretClient(
            vault_url=key_vault_url,
            credential=credential
        )

        # ------------------------------------------------------------
        # Retrieve Qualys username
        # ------------------------------------------------------------

        qualys_username = (
            secret_client
            .get_secret("QualysUsername")
            .value
        )

        # ------------------------------------------------------------
        # Retrieve Qualys password
        # ------------------------------------------------------------

        qualys_password = (
            secret_client
            .get_secret("QualysPassword")
            .value
        )

        # ------------------------------------------------------------
        # Retrieve Qualys base URL
        # ------------------------------------------------------------

        qualys_api_url = (
            secret_client
            .get_secret("QualysBaseUrl")
            .value
        )

        # ------------------------------------------------------------
        # Log only safe information
        # NEVER log username/password values
        # ------------------------------------------------------------

        logging.info(
            "=== QUALYS CREDENTIAL CHECK ==="
        )

        logging.info(
            f"Qualys Username: "
            f"{'SET' if qualys_username else 'NOT SET'}"
        )

        logging.info(
            f"Qualys Password: "
            f"{'SET' if qualys_password else 'NOT SET'}"
        )

        logging.info(
            f"Qualys API URL: "
            f"{qualys_api_url}"
        )

        # ============================================================
        # STEP 7B: UPDATE MISSING TAGS USING QUALYS
        # ============================================================

        logging.info(
            "=== STARTING QUALYS API TAG UPDATE ==="
        )

        result_df, qualys_updated_count, final_missing_ips = (
            update_missing_tags_with_qualys(
                result_df,
                comparison_column,
                qualys_username,
                qualys_password,
                qualys_api_url
            )
        )

        logging.info(
            f"Qualys API tag update completed - "
            f"Updated {qualys_updated_count} records"
        )

        logging.info(
            f"Final count of IPs still missing tags: "
            f"{len(final_missing_ips)}"
        )

        # ============================================================
        # STEP 8: CLEAN UP TAGS COLUMN
        # ============================================================

        logging.info(
            "=== CLEANING UP TAGS COLUMN ==="
        )

        tag_cleanup_count = 0

        for idx, row in result_df.iterrows():

            tag_value = row[
                comparison_column
            ]

            if (
                pd.isna(tag_value)
                or str(tag_value).strip().lower()
                in [
                    '',
                    'nan',
                    'none',
                    'null'
                ]
            ):

                result_df.at[
                    idx,
                    comparison_column
                ] = ''

                tag_cleanup_count += 1

        logging.info(
            f"Cleaned up {tag_cleanup_count} "
            f"empty tag cells"
        )

        # ============================================================
        # CONVERT NON-EMPTY TAGS TO INTEGER
        # ============================================================

        def convert_tag(val):

            try:

                if str(val).strip() == '':
                    return ''

                return int(
                    float(val)
                )

            except Exception:

                return val

        result_df[
            comparison_column
        ] = result_df[
            comparison_column
        ].apply(convert_tag)

        # ============================================================
        # RESET INDEX
        # ============================================================

        result_df = result_df.reset_index(
            drop=True
        )

        # ============================================================
        # CREATE EXCEL OUTPUT
        # ============================================================

        logging.info(
            "=== CREATING EXCEL OUTPUT ==="
        )

        output_buffer = io.BytesIO()

        with pd.ExcelWriter(
            output_buffer,
            engine='openpyxl'
        ) as writer:

            # --------------------------------------------------------
            # Main processed data
            # --------------------------------------------------------

            result_df.to_excel(
                writer,
                index=False,
                sheet_name='Processed_Data'
            )

            # --------------------------------------------------------
            # Missing IPs
            # --------------------------------------------------------

            if final_missing_ips:

                missing_df = pd.DataFrame({
                    'IP Address':
                        final_missing_ips
                })

                missing_df.to_excel(
                    writer,
                    index=False,
                    sheet_name='IPs_With_Tags_Missing'
                )

                logging.info(
                    f"Added Missing_IPs sheet with "
                    f"{len(final_missing_ips)} IP addresses"
                )

            else:

                logging.info(
                    "No missing IPs found, "
                    "skipping Missing_IPs sheet creation"
                )

        excel_data = output_buffer.getvalue()

        # ============================================================
        # FINAL SUMMARY
        # ============================================================

        logging.info(
            "=== PROCESSING COMPLETE ==="
        )

        logging.info(
            f"Final processed data: "
            f"{len(result_df)} unique rows"
        )

        logging.info(
            f"Excel file size: "
            f"{len(excel_data)} bytes"
        )

        logging.info(
            "FINAL SUMMARY:"
        )

        logging.info(
            f"  - Total rows: "
            f"{len(result_df)}"
        )

        logging.info(
            f"  - Tags from existing Excel: "
            f"{updated_count}"
        )

        logging.info(
            f"  - Tags from Qualys API: "
            f"{qualys_updated_count}"
        )

        logging.info(
            f"  - IPs still missing tags: "
            f"{len(final_missing_ips)}"
        )

        logging.info(
            f"  - Missing IPs list: "
            f"{final_missing_ips}"
        )

        return {
            'success': True,
            'excel_data': excel_data,
            'row_count': len(result_df),
            'original_count': len(df),
            'unique_ips': len(result_df),
            'updated_tags': updated_count,
            'qualys_updated_tags':
                qualys_updated_count,
            'missing_ips':
                final_missing_ips
        }

    except Exception as e:

        logging.error(
            f"ERROR in encode_excel_data: "
            f"{str(e)}",
            exc_info=True
        )

        return {
            'success': False,
            'error': str(e)
        }