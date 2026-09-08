import logging
import azure.functions as func
import aiohttp
import asyncio
import os
import time
import xml.etree.ElementTree as ET
import io
import traceback
import sys
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import gc

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Sync wrapper for Async DownloadQualysReport Function
    """
    # Run the async main function
    return asyncio.run(async_main(req))

async def async_main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Async DownloadQualysReport Function - Faster processing with async operations
    """
    start_time = time.time()
    
    function_state = {
        "stage": "initialization",
        "report_id": None,
        "asset_groups": None,
        "cycle_id": None,
        "api_response_status": None,
        "xml_parsed": False,
        "rows_extracted": 0,
        "processing_time": 0
    }
    
    try:
        logging.info("Async DownloadQualysReport function processing a request")
        function_state["stage"] = "parameter_extraction"
        
        # Extract parameters
        report_id = req.params.get("report_id")
        asset_groups = req.params.get("asset_groups")
        cycle_id = req.params.get("cycleId")
        
        function_state.update({
            "report_id": report_id,
            "asset_groups": asset_groups,
            "cycle_id": cycle_id
        })
        
        if not report_id:
            return func.HttpResponse(
                "Missing required parameter: report_id",
                status_code=400,
                mimetype="text/plain"
            )
        
        # Get credentials
        qualys_username = os.environ.get("QUALYS_USERNAME")
        qualys_password = os.environ.get("QUALYS_PASSWORD")
        qualys_api_url = os.environ.get("QUALYS_API_URL")
        
        if not all([qualys_username, qualys_password, qualys_api_url]):
            return func.HttpResponse(
                "Missing required environment variables",
                status_code=500,
                mimetype="text/plain"
            )
        
        logging.info(f"Downloading report ID: {report_id}")
        function_state["stage"] = "report_download"
        
        # Async download
        xml_data = await download_report_async(
            qualys_api_url, report_id, qualys_username, qualys_password
        )
        
        function_state["api_response_status"] = 200
        function_state["stage"] = "report_processing"
        processing_start = time.time()
        
        # Import modules
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        from shared.xml_parser import parse_xml, extract_asset_info, extract_vuln_details_map
        from shared.data_processor import process_vulnerability_data
        from shared.excel_generator import create_excel_report
        
        # Parse XML asynchronously
        function_state["stage"] = "xml_parsing"
        root = await parse_xml_async(xml_data)
        function_state["xml_parsed"] = True
        
        # Define headers
        csv_headers = [
            "Import Id", "IP", "DNS", "OS", "QID", "Title", "Severity", "Type",
            "Threat", "Impact", "Solution", "Port", "Protocol", "QDS", "ARS", "ACS", 
            "TruRisk Score", "Exploitability", "CVE ID", "CVSS Base", "CVSS Temporal", 
            "CVSS3 Base", "CVSS3 Temporal", "Results", "Vuln Status", "Associated Malware", 
            "First Found", "Last Found", "Last Update", "Last Fixed", "PCI Flag"
        ]
        
        function_state["stage"] = "data_extraction"
        
        # Parallel processing of asset info and vulnerability details
        asset_info_task = asyncio.create_task(extract_asset_info_async(root))
        vuln_details_task = asyncio.create_task(extract_vuln_details_async(root))
        
        # Wait for both tasks to complete
        (asset_groups_str, extracted_cycle_id), vuln_details_map = await asyncio.gather(
            asset_info_task, vuln_details_task
        )
        
        # Use provided parameters or extracted values
        if not cycle_id and extracted_cycle_id:
            cycle_id = extracted_cycle_id
            function_state["cycle_id"] = cycle_id
            
        if not asset_groups and asset_groups_str:
            asset_groups = asset_groups_str
            function_state["asset_groups"] = asset_groups
        
        logging.info(f"Built vulnerability details map for {len(vuln_details_map)} entries")
        
        # Extract hosts and process in parallel batches
        host_list = root.find(".//HOST_LIST")
        if host_list is None:
            return func.HttpResponse(
                "No HOST_LIST found in XML report",
                status_code=500,
                mimetype="text/plain"
            )
        
        hosts = host_list.findall("HOST")
        total_hosts = len(hosts)
        logging.info(f"Processing {total_hosts} hosts in parallel...")
        
        # Process hosts in parallel batches
        rows = await process_hosts_async(hosts, vuln_details_map, batch_size=20)
        
        function_state["rows_extracted"] = len(rows)
        
        if not rows:
            return func.HttpResponse(
                "No vulnerability data was extracted",
                status_code=500,
                mimetype="text/plain"
            )
        
        logging.info(f"Successfully extracted data for {len(rows)} vulnerability entries")
        
        function_state["stage"] = "data_processing"
        
        # Process data asynchronously
        stats = await process_data_async(rows, csv_headers)
        
        function_state["stage"] = "excel_generation"
        
        # Generate Excel asynchronously
        excel_data = await generate_excel_async(rows, csv_headers, stats, asset_groups_str, cycle_id)
        
        function_state["stage"] = "response_generation"
        function_state["processing_time"] = time.time() - processing_start
        
        logging.info(f"Report processing completed in {function_state['processing_time']:.2f} seconds")
        logging.info(f"Total function execution time: {time.time() - start_time:.2f} seconds")
        
        filename = f"vulnerability_report_{cycle_id}.xlsx" if cycle_id else "vulnerability_report.xlsx"
        
        return func.HttpResponse(
            excel_data,
            status_code=200,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except asyncio.TimeoutError:
        error_message = "Request timed out while processing report"
        logging.error(error_message)
        return func.HttpResponse(error_message, status_code=408, mimetype="text/plain")
        
    except Exception as e:
        stack_trace = traceback.format_exc()
        error_message = f"Error processing scan report: {str(e)}"
        logging.error(f"{error_message}\nStack trace:\n{stack_trace}")
        logging.error(f"Function state: {function_state}")
        return func.HttpResponse(error_message, status_code=500, mimetype="text/plain")


async def download_report_async(api_url, report_id, username, password):
    """Async report download with timeout"""
    report_url = f"{api_url}/api/2.0/fo/report/"
    params = {"action": "fetch", "id": report_id}
    
    connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=120)  # 2 minutes
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        auth=aiohttp.BasicAuth(username, password)
    ) as session:
        headers = {"X-Requested-With": "IVM Automation"}
        
        async with session.get(report_url, params=params, headers=headers) as response:
            if response.status != 200:
                error_msg = f"Qualys API error: {response.status}"
                if response.text:
                    error_msg += f" - {await response.text()}"
                raise Exception(error_msg)
            
            return await response.text()


async def parse_xml_async(xml_data):
    """Async XML parsing using thread pool"""
    loop = asyncio.get_event_loop()
    
    def parse_sync():
        try:
            return ET.fromstring(xml_data)
        except ET.ParseError as pe:
            logging.error(f"XML Parse Error: {str(pe)}")
            raise
    
    # Run CPU-intensive parsing in thread pool
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = loop.run_in_executor(executor, parse_sync)
        return await future


async def extract_asset_info_async(root):
    """Async asset info extraction"""
    loop = asyncio.get_event_loop()
    
    def extract_sync():
        from shared.xml_parser import extract_asset_info
        return extract_asset_info(root)
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = loop.run_in_executor(executor, extract_sync)
        return await future


async def extract_vuln_details_async(root):
    """Async vulnerability details extraction"""
    loop = asyncio.get_event_loop()
    
    def extract_sync():
        from shared.xml_parser import extract_vuln_details_map
        return extract_vuln_details_map(root)
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = loop.run_in_executor(executor, extract_sync)
        return await future


async def process_hosts_async(hosts, vuln_details_map, batch_size=20):
    """Process hosts in parallel batches"""
    from shared.xml_parser import extract_host_vulnerabilities
    
    def process_batch_sync(batch_hosts):
        batch_rows = []
        for host_element in batch_hosts:
            try:
                host_rows = extract_host_vulnerabilities(host_element, vuln_details_map)
                batch_rows.extend(host_rows)
            except Exception as e:
                logging.warning(f"Error processing host: {str(e)}")
                continue
        return batch_rows
    
    # Create batches
    batches = [hosts[i:i + batch_size] for i in range(0, len(hosts), batch_size)]
    
    # Process batches in parallel
    loop = asyncio.get_event_loop()
    
    with ThreadPoolExecutor(max_workers=4) as executor:  # Adjust based on available cores
        tasks = []
        for batch in batches:
            future = loop.run_in_executor(executor, process_batch_sync, batch)
            tasks.append(future)
        
        # Wait for all batches to complete
        batch_results = await asyncio.gather(*tasks)
    
    # Combine results
    all_rows = []
    for batch_rows in batch_results:
        all_rows.extend(batch_rows)
    
    return all_rows


async def process_data_async(rows, csv_headers):
    """Async data processing"""
    loop = asyncio.get_event_loop()
    
    def process_sync():
        from shared.data_processor import process_vulnerability_data
        return process_vulnerability_data(rows, csv_headers)
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = loop.run_in_executor(executor, process_sync)
        return await future


async def generate_excel_async(rows, csv_headers, stats, asset_groups, cycle_id):
    """Async Excel generation using xlsxwriter"""
    loop = asyncio.get_event_loop()
    
    def generate_sync():
        from shared.excel_generator import create_excel_report_with_buffer_return
        
        # xlsxwriter version returns bytes directly
        excel_data = create_excel_report_with_buffer_return(rows, csv_headers, stats, asset_groups, cycle_id)
        
        # Force garbage collection
        gc.collect()
        
        return excel_data
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = loop.run_in_executor(executor, generate_sync)
        return await future