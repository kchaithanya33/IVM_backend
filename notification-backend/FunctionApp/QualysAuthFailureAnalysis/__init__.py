import logging
import azure.functions as func
import json
import requests
import os
import re
import base64
import io
import pandas as pd

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    QualysAuthFailureAnalysis Function - Analyzes authentication failures and host-not-alive issues in a scan report
    
    This function analyzes a Qualys scan report to identify authentication failures and host-not-alive issues,
    and provides a summary of affected assets.
    
    Input: JSON with:
      - scanId: The Qualys scan reference ID (this is passed directly as scan_ref to QualysScanFetch)
      - cycleId: The scan cycle ID
      - assetGroupName: The asset group name
      - scanResults: (optional) The scan results data if already available
    
    Output: Summary of authentication failures and host-not-alive issues including:
      - failureCount: The number of assets with authentication failures
      - failedAssets: List of assets with authentication failures and their details
      - notAliveCount: The number of assets that were not alive during scan
      - notAliveAssets: List of not-alive assets and their details
      - summary: Text summary of authentication failures and host-not-alive issues
    """
    logging.info('QualysAuthFailureAnalysis function processing a request')
    
    try:
        # Get request data
        req_body = req.get_json()
        
        scan_id = req_body.get('scanId')
        cycle_id = req_body.get('cycleId')
        asset_group_name = req_body.get('assetGroupName')
        scan_results = req_body.get('scanResults')
          # Validate required parameters
        if not scan_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameter 'scanId'"}),
                status_code=400,
                mimetype="application/json"
            )
            
        if not scan_results:
            # If scan results aren't provided, we need to fetch them using QualysScanFetch directly
            # Get the function app's own URL for calling QualysScanFetch
            function_app_url = os.environ.get("FUNCTION_APP_URL", "")
            if not function_app_url:
                # If FUNCTION_APP_URL is not set, try to construct it
                function_app_url = f"https://{os.environ.get('WEBSITE_HOSTNAME', '')}"
                
            if not function_app_url or function_app_url == "https://":
                logging.error("Unable to determine function app URL for internal function call")
                return func.HttpResponse(
                    json.dumps({"error": "Server configuration error: Unable to determine function app URL"}),
                    status_code=500,
                    mimetype="application/json"
                )
                
            # Call QualysScanFetch function directly
            fetch_url = f"{function_app_url}/api/QualysScanFetch"
            fetch_response = requests.post(
                fetch_url,
                # Use scan_ref instead of scan_id for auth scan results
                json={"scan_ref": scan_id, "output_format": "json_extended"},
                headers={"Content-Type": "application/json"}
            )
            
            if fetch_response.status_code != 200:
                logging.error(f"Failed to get scan results: Status {fetch_response.status_code}, Response: {fetch_response.text}")
                return func.HttpResponse(
                    json.dumps({"error": f"Failed to get scan results: {fetch_response.text}"}),
                    status_code=500,
                    mimetype="application/json"
                )
                
            scan_results = fetch_response.json()
            
        # Initialize counters and results containers
        failed_assets = []
        failure_count = 0
        not_alive_assets_windows = []
        not_alive_assets_unix = []
        not_alive_assets_unknown = []
        not_alive_count = 0
        
        # Process scan results to identify authentication failures and host-not-alive issues
        try:
            # Process authentication failures - Try both API formats
            
            # Traditional format (XML to JSON conversion with HOST_LIST structure)
            hosts = scan_results.get('HOST_LIST', {}).get('HOST', [])
            if hosts:
                if not isinstance(hosts, list):
                    hosts = [hosts]  # Handle case where there's only one host
                    
                for host in hosts:
                    host_ip = host.get('IP', 'Unknown')
                    host_name = host.get('DNS', host_ip)
                    
                    # Check for authentication status
                    auth_records = host.get('AUTHENTICATION_RECORDS', {}).get('AUTHENTICATION_RECORD', [])
                    if not isinstance(auth_records, list):
                        auth_records = [auth_records]  # Handle case where there's only one record
                    
                    for auth_record in auth_records:
                        auth_status = auth_record.get('STATUS', [])
                        if 'Failed' in auth_status or 'FAILED' in auth_status:
                            failure_count += 1
                            failed_assets.append({
                                "ip": host_ip,
                                "hostname": host_name,
                                "osType": host.get('OS', 'Unknown'),
                                "failureReason": auth_record.get('CAUSE_OF_FAILURE', 'Unknown'),
                                "tech": auth_record.get('TECHNOLOGY', 'Unknown')
                            })
            
            # New format in mock-auth-scan-result.json (JSON array format)
            if isinstance(scan_results, list):
                # Check for authentication failures
                for item in scan_results:
                    if isinstance(item, dict) and item.get('title') in ('Unix Authentication Failed', 'Windows Authentication Failed', 'VMware Authentication Failed'):
                        host_ip = item.get('ip', 'Unknown')
                        host_name = item.get('dns', host_ip)
                        os_type = item.get('os', 'Unknown')                        # Extract detailed information from results
                        results_str = item.get('results', '')
                        
                        # Extract service name, username, and authentication record
                        service = "Unknown"
                        username = "Unknown"
                        auth_record = "Unknown"
                        diagnostics = "Unknown"
                        error_code = "Unknown"
                        failure_summary = "Unknown"
                        auth_mode = "Unknown"
                        
                        if results_str:
                            # Parse the results string to extract useful information
                            results_lines = results_str.split('\n')
                            for line in results_lines:
                                if line.startswith('Service'):
                                    service = line.split('\t')[1] if '\t' in line else "Unknown"
                                elif line.startswith('User Name'):
                                    username = line.split('\t')[1] if '\t' in line else "Unknown"
                                elif line.startswith('Authentication Record'):
                                    auth_record = line.split('\t')[1] if '\t' in line else "Unknown"
                            
                            # Extract diagnostics and more detailed error information
                            try:
                                diag_start = results_str.find('Diagnostics')
                                if diag_start > -1:
                                    diagnostics = results_str[diag_start:]
                                    
                                    # Extract specific error details from diagnostics
                                    diag_lines = diagnostics.split('\n')
                                    for i, line in enumerate(diag_lines):
                                        # Look for authentication mode
                                        if 'Authentication mode' in line:
                                            auth_mode_match = re.search(r"Authentication mode\s+'([^']+)'", line)
                                            if auth_mode_match:
                                                auth_mode = auth_mode_match.group(1)
                                                
                                        # Look for specific error messages
                                        if 'credentials were incorrect' in line:
                                            failure_summary = "Incorrect credentials"
                                        elif 'Account is locked' in line:
                                            failure_summary = "Account is locked"
                                        elif 'Account is disabled' in line:
                                            failure_summary = "Account is disabled"
                                        elif 'Permission denied' in line:
                                            failure_summary = "Permission denied"
                                        elif 'No authentication methods available' in line:
                                            failure_summary = "No authentication methods available"
                                            
                                        # Extract error code if present
                                        if 'failed (diag=' in line:
                                            error_code_match = re.search(r"failed \(diag=(\d+)\)", line)
                                            if error_code_match:
                                                error_code = error_code_match.group(1)
                                        
                                        # For Windows authentication failures
                                        if 'The login is from an untrusted domain' in line:
                                            failure_summary = "Login from untrusted domain"
                                        elif 'does not have the right to login' in line:
                                            failure_summary = "User lacks login rights"
                                        elif 'No logon servers available' in line:
                                            failure_summary = "No logon servers available"
                                        elif 'Clock skew too great' in line:
                                            failure_summary = "Clock skew too great"
                            except Exception as e:
                                logging.warning(f"Error extracting diagnostics: {str(e)}")
                                diagnostics = results_str  # Fall back to full results string
                        
                        # Get last line for short failure reason if we haven't determined a specific reason
                        if failure_summary == "Unknown":
                            last_line = results_str.split('\n')[-1] if results_str and results_str.split('\n')[-1].strip() else 'Unknown'
                            failure_summary = last_line if last_line != "Unknown" else "Authentication failure"
                            
                        failure_reason_short = failure_summary
                        
                        failure_count += 1
                        failed_assets.append({
                            "ip": host_ip,
                            "hostname": host_name,
                            "osType": os_type,
                            "failureReason": failure_reason_short,
                            "failureDetails": {
                                "service": service,
                                "username": username, 
                                "authRecord": auth_record,
                                "authMode": auth_mode,
                                "errorCode": error_code,
                                "failureSummary": failure_summary,
                                "diagnostics": diagnostics
                            },
                            "tech": "Windows" if "Windows Authentication Failed" == item.get('title') else 
                                   "VMware" if "VMware Authentication Failed" == item.get('title') else "Unix",
                            "scanTimestamp": item.get('scan_date', '') or scan_results[1].get('launch_date', '') if len(scan_results) > 1 else ''
                        })
                
                # Check for host-not-alive information in array format
                for item in scan_results:
                    if isinstance(item, dict) and "hosts_not_scanned_host_not_alive_ip" in item:
                        not_alive_ips_str = item.get("hosts_not_scanned_host_not_alive_ip", "")
                        process_host_not_alive_ips(not_alive_ips_str, scan_results, not_alive_assets_windows, 
                                                  not_alive_assets_unix, not_alive_assets_unknown)
                        not_alive_count = len(not_alive_assets_windows) + len(not_alive_assets_unix) + len(not_alive_assets_unknown)
                        break
            
            # Check for host-not-alive information in dictionary format
            if not_alive_count == 0 and isinstance(scan_results, dict):
                not_alive_ips_str = scan_results.get("hosts_not_scanned_host_not_alive_ip", "")
                if not_alive_ips_str:
                    process_host_not_alive_ips(not_alive_ips_str, scan_results, not_alive_assets_windows, 
                                              not_alive_assets_unix, not_alive_assets_unknown)
                    not_alive_count = len(not_alive_assets_windows) + len(not_alive_assets_unix) + len(not_alive_assets_unknown)
            
        except Exception as e:
            logging.warning(f"Error parsing scan results: {str(e)}. Using fallback parsing method.")
            
            # Fallback parsing method using string search in case structure is different
            result_str = json.dumps(scan_results)
            
            # Find authentication failures
            # Regular Expression patterns for both formats
            patterns = {
                'old_ip': r'"IP"\s*:\s*"([^"]+)"',
                'old_dns': r'"DNS"\s*:\s*"([^"]+)"',
                'old_os': r'"OS"\s*:\s*"([^"]+)"',
                'old_failure': r'"CAUSE_OF_FAILURE"\s*:\s*"([^"]+)"',
                'old_tech': r'"TECHNOLOGY"\s*:\s*"([^"]+)"',
                'new_ip': r'"ip"\s*:\s*"([^"]+)"',
                'new_dns': r'"dns"\s*:\s*"([^"]+)"',
                'new_os': r'"os"\s*:\s*"([^"]+)"',
                'new_title': r'"title"\s*:\s*"(Unix|Windows|VMware) Authentication Failed"',
            }
            
            # Find authentication failures with different patterns
            auth_failures = []
            auth_failures.extend(re.findall(r'"STATUS"\s*:\s*"Failed".*?(?=,\s*{|}$)', result_str, re.DOTALL))
            auth_failures.extend(re.findall(r'"title"\s*:\s*"(Unix|Windows|VMware) Authentication Failed".*?(?=,\s*{|}$)', result_str, re.DOTALL))
            
            for failure in auth_failures:
                context = result_str[max(0, result_str.find(failure) - 1000):result_str.find(failure) + len(failure) + 1000]
                
                # Extract data from context using both pattern sets
                ip = extract_with_patterns(context, [patterns['old_ip'], patterns['new_ip']], "Unknown")
                hostname = extract_with_patterns(context, [patterns['old_dns'], patterns['new_dns']], "Unknown")
                os_type = extract_with_patterns(context, [patterns['old_os'], patterns['new_os']], "Unknown")
                title_match = re.search(patterns['new_title'], context)
                
                # Determine technology based on title or tech field
                tech = "Unknown"
                if re.search(patterns['old_tech'], context):
                    tech = re.search(patterns['old_tech'], context).group(1)
                elif title_match:
                    tech = title_match.group(1)
                
                failed_assets.append({
                    "ip": ip,
                    "hostname": hostname,
                    "osType": os_type,
                    "failureReason": extract_with_patterns(context, [patterns['old_failure']], "Unknown"),
                    "tech": tech
                })
                
                failure_count += 1
            
            # Fallback for host-not-alive
            not_alive_match = re.search(r'"hosts_not_scanned_host_not_alive_ip"\s*:\s*"([^"]+)"', result_str)
            if not_alive_match:
                not_alive_ips_str = not_alive_match.group(1)
                process_host_not_alive_ips(not_alive_ips_str, scan_results, not_alive_assets_windows, 
                                          not_alive_assets_unix, not_alive_assets_unknown)
                not_alive_count = len(not_alive_assets_windows) + len(not_alive_assets_unix) + len(not_alive_assets_unknown)
        
        # Prepare summary message
        auth_failures_summary = ""
        not_alive_summary = ""
        
        if failure_count > 0:
            auth_failures_summary = f"Found {failure_count} assets with authentication failures. "
        else:
            auth_failures_summary = "All assets authenticated successfully. "
        
        if not_alive_count > 0:
            not_alive_summary = f"Found {not_alive_count} hosts that were not alive during the scan. "
        else:
            not_alive_summary = "All hosts were responsive during the scan. "
        
        summary = f"Authentication scan for {asset_group_name} in cycle {cycle_id} completed. {auth_failures_summary}{not_alive_summary}"
            
        # Prepare response
        result = {
            "failureCount": failure_count,
            "failedAssets": failed_assets,
            "notAliveCount": not_alive_count,
            "notAliveAssetsWindows": not_alive_assets_windows,
            "notAliveAssetsUnix": not_alive_assets_unix,
            "notAliveAssetsUnknown": not_alive_assets_unknown,
            "summary": summary,
            "scanId": scan_id,
            "cycleId": cycle_id,
            "assetGroupName": asset_group_name
        }
        
        # 1. Parse CMDB Excel from base64 in request
        cmdb_base64 = req_body.get("cmdbReportBase64")
        ip_to_category = {}
        
        if cmdb_base64:
            try:
                cmdb_bytes = base64.b64decode(cmdb_base64)
                cmdb_file = io.BytesIO(cmdb_bytes)
                cmdb_df = pd.read_excel(cmdb_file)
                # Adjust column names as per your CMDB file
                # Example: columns = ['IP', 'Category']
                for _, row in cmdb_df.iterrows():
                    ip = str(row.get('IP')).strip()
                    category = str(row.get('Category', '')).strip().lower()
                    ip_to_category[ip] = category
            except Exception as e:
                logging.warning(f"Failed to parse CMDB Excel: {e}")
        
        # 2. Split failed_assets by category
        failed_assets_windows = []
        failed_assets_unix = []
        failed_assets_meydiageo = []
        failed_assets_others = []
        
        for asset in failed_assets:
            ip = asset.get("ip")
            category = ip_to_category.get(ip, "")
            if "windows" in category:
                failed_assets_windows.append(asset)
            elif "linux" in category or "unix" in category:
                failed_assets_unix.append(asset)
            elif "meydiageo" in category:
                failed_assets_meydiageo.append(asset)
            else:
                failed_assets_others.append(asset)
        
        # Re-categorize not_alive_assets_unknown using CMDB mapping
        not_alive_assets_windows_cmdb = []
        not_alive_assets_unix_cmdb = []
        not_alive_assets_meydiageo_cmdb = []
        not_alive_assets_unknown_cmdb = []

        for asset in not_alive_assets_unknown:
            # asset is now a string (IP), not a dict
            ip = asset
            category = ip_to_category.get(ip, "")
            if "windows" in category:
                not_alive_assets_windows_cmdb.append(ip)
            elif "linux" in category or "unix" in category:
                not_alive_assets_unix_cmdb.append(ip)
            elif "meydiageo" in category:
                not_alive_assets_meydiageo_cmdb.append(ip)
            else:
                not_alive_assets_unknown_cmdb.append(ip)

        # Update the main collections
        not_alive_assets_windows.extend(not_alive_assets_windows_cmdb)
        not_alive_assets_unix.extend(not_alive_assets_unix_cmdb)
        not_alive_assets_meydiageo = not_alive_assets_meydiageo_cmdb
        not_alive_assets_unknown = not_alive_assets_unknown_cmdb
        
        # In the result dictionary, add these new lists:
        result = {
            "failureCount": failure_count,
            "failedAssets": failed_assets,
            "failedAssetsWindows": failed_assets_windows,
            "failedAssetsUnix": failed_assets_unix,
            "failedAssetsMeyDiageo": failed_assets_meydiageo,
            "failedAssetsOthers": failed_assets_others,
            "notAliveCount": not_alive_count,
            "notAliveAssetsWindows": not_alive_assets_windows,
            "notAliveAssetsUnix": not_alive_assets_unix,
            "notAliveAssetsMeyDiageo": not_alive_assets_meydiageo,
            "notAliveAssetsUnknown": not_alive_assets_unknown,
            "summary": summary,
            "scanId": scan_id,
            "cycleId": cycle_id,
            "assetGroupName": asset_group_name
        }
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )
    
    except Exception as e:
        logging.exception(f"Error in QualysAuthFailureAnalysis function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def extract_with_patterns(text, patterns, default_value):
    """Helper function to extract data using multiple regex patterns"""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return default_value

def process_host_not_alive_ips(not_alive_ips_str, scan_results, not_alive_assets_windows, not_alive_assets_unix, not_alive_assets_unknown):
    """Process the host-not-alive IP string and add assets to appropriate lists"""
    if not not_alive_ips_str:
        return
    
    # Parse IP ranges 
    ip_ranges = not_alive_ips_str.split(', ')
    for ip_range in ip_ranges:
        if '-' in ip_range:
            # This is an IP range like 10.0.0.1-10.0.0.5
            start_ip, end_ip = ip_range.split('-')
            # Extract the base part and last octet of IP addresses
            start_parts = start_ip.split('.')
            end_parts = end_ip.split('.')
            
            # If they share the same first 3 octets
            if start_parts[:3] == end_parts[:3]:
                base_ip = '.'.join(start_parts[:3]) + '.'
                start_num = int(start_parts[3])
                end_num = int(end_parts[3])
                
                # Add each IP in the range
                for i in range(start_num, end_num + 1):
                    ip = f"{base_ip}{i}"
                    determine_os_and_add_not_alive_asset(scan_results, ip, not_alive_assets_windows, not_alive_assets_unix, not_alive_assets_unknown)
            else:
                # Complex range spanning multiple subnets
                determine_os_and_add_not_alive_asset(scan_results, start_ip, not_alive_assets_windows, not_alive_assets_unix, not_alive_assets_unknown)
                determine_os_and_add_not_alive_asset(scan_results, end_ip, not_alive_assets_windows, not_alive_assets_unix, not_alive_assets_unknown)
        else:
            # Single IP address
            determine_os_and_add_not_alive_asset(scan_results, ip_range, not_alive_assets_windows, not_alive_assets_unix, not_alive_assets_unknown)

def determine_os_and_add_not_alive_asset(scan_results, ip, not_alive_assets_windows, not_alive_assets_unix, not_alive_assets_unknown):
    """
    Determines the OS type for a not-alive host and adds it to the appropriate list
    """
    hostname = "Unknown"
    os_type = "Unknown"
    
    # Try to find the hostname and OS type from other scan data if available
    # First, convert scan_results to string for easier searching if needed
    scan_results_str = ""
    if isinstance(scan_results, dict):
        scan_results_str = json.dumps(scan_results)
    elif isinstance(scan_results, list):
        scan_results_str = json.dumps(scan_results)
    
    # Look for hostname patterns related to this IP
    ip_escaped = ip.replace(".", "\\.")
    
    # Try both old and new format patterns
    hostname_patterns = [
        rf'"IP"\s*:\s*"{ip_escaped}"[^}}]+"DNS"\s*:\s*"([^"]+)"',
        rf'"ip"\s*:\s*"{ip_escaped}"[^}}]+"dns"\s*:\s*"([^"]+)"'
    ]
    
    os_patterns = [
        rf'"IP"\s*:\s*"{ip_escaped}"[^}}]+"OS"\s*:\s*"([^"]+)"',
        rf'"ip"\s*:\s*"{ip_escaped}"[^}}]+"os"\s*:\s*"([^"]+)"'
    ]
    
    # Try to find hostname
    for pattern in hostname_patterns:
        hostname_match = re.search(pattern, scan_results_str)
        if hostname_match:
            hostname = hostname_match.group(1)
            break
    
    # Try to find OS type
    for pattern in os_patterns:
        os_match = re.search(pattern, scan_results_str)
        if os_match:
            os_type = os_match.group(1)
            break
    
    # If no OS found, try to determine from hostname
    if os_type == "Unknown" and hostname != "Unknown":
        hostname_lower = hostname.lower()
        # Check for common OS indicators in hostname
        if any(win_indicator in hostname_lower for win_indicator in ["win", "windows", "ws", "dc", "-w"]):
            os_type = "Windows"
        elif any(unix_indicator in hostname_lower for unix_indicator in ["nix", "linux", "ubuntu", "centos", "rhel", "unix", "lnx", "-l"]):
            os_type = "Unix/Linux"
    
    # Add to appropriate list based on OS type
    asset = ip
    
    if "windows" in os_type.lower():
        not_alive_assets_windows.append(asset)
    elif any(unix_indicator in os_type.lower() for unix_indicator in ["unix", "linux", "centos", "ubuntu", "rhel", "vmware"]):
        not_alive_assets_unix.append(asset)
    else:
        not_alive_assets_unknown.append(asset)