import logging
import json
import base64
from io import BytesIO
from datetime import datetime

import azure.functions as func
import openpyxl


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Filters CMDB report (Excel) for Mey Diageo IPs.

    Expected input:
    {
        "cmdbReportContent": "base64_encoded_excel_content",
        "cycleId": "cycle-id"
    }

    Returns:
    {
        "groupsForCreation": [
            {
                "name": "VulnScan-CYCLE-MeyDiageo-TIMESTAMP-Batch-0",
                "ips": ["10.100.1.10"]
            }
        ]
    }
    """

    logging.info(
        "Processing CMDB Excel report for Mey Diageo IPs"
    )

    try:
        # Parse request body
        req_body = req.get_json()

        excel_content_base64 = req_body.get(
            "cmdbReportContent"
        )

        cycle_id = req_body.get(
            "cycleId"
        )

        if not excel_content_base64:
            return func.HttpResponse(
                json.dumps({
                    "error":
                        "Missing required field: "
                        "cmdbReportContent"
                }),
                status_code=400,
                mimetype="application/json"
            )

        if not cycle_id:
            return func.HttpResponse(
                json.dumps({
                    "error":
                        "Missing required field: cycleId"
                }),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(
            f"Received Excel content, base64 length: "
            f"{len(excel_content_base64)}"
        )

        # Decode base64 content
        excel_bytes = base64.b64decode(
            excel_content_base64
        )

        logging.info(
            f"Decoded Excel bytes, length: "
            f"{len(excel_bytes)}"
        )

        # Parse Excel file
        workbook = openpyxl.load_workbook(
            BytesIO(excel_bytes),
            data_only=True
        )

        sheet = workbook.active

        logging.info(
            "Excel loaded successfully, "
            f"active sheet: {sheet.title}"
        )

        # Get headers from first row
        headers = []

        for cell in sheet[1]:
            headers.append(cell.value)

        logging.info(
            f"Excel headers: {headers}"
        )

        # Find required columns
        ip_col = headers.index(
            "IP Address"
        )

        value_stream_col = headers.index(
            "Value Stream"
        )

        skip_scan_col = headers.index(
            "Skip Scan"
        )

        logging.info(
            "Column indices - "
            f"IP: {ip_col}, "
            f"Value Stream: {value_stream_col}, "
            f"Skip Scan: {skip_scan_col}"
        )

        # Filter IPs
        filtered_ips = []

        total_rows = 0
        skipped_value_stream = 0
        skipped_scan = 0
        skipped_no_ip = 0

        # Iterate through rows
        for row_num, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):

            total_rows += 1

            # Get cell values
            ip_address = (
                str(row[ip_col]).strip()
                if row[ip_col]
                else ""
            )

            value_stream = (
                str(row[value_stream_col]).strip()
                if row[value_stream_col]
                else ""
            )

            skip_scan = (
                str(row[skip_scan_col])
                .strip()
                .lower()
                if row[skip_scan_col]
                else ""
            )

            # Log first few rows
            if total_rows <= 3:

                logging.info(
                    f"Row {row_num} - "
                    f"Value Stream: '{value_stream}', "
                    f"Skip Scan: '{skip_scan}', "
                    f"IP: '{ip_address}'"
                )

            # Value Stream must be Mey Diageo
            if value_stream != "Mey Diageo":

                skipped_value_stream += 1

                continue

            # Skip Scan must not be true/yes/1
            if skip_scan in [
                "true",
                "yes",
                "1"
            ]:

                skipped_scan += 1

                continue

            # IP must exist
            if (
                not ip_address
                or ip_address == "None"
            ):

                skipped_no_ip += 1

                continue

            filtered_ips.append(
                ip_address
            )

        logging.info(
            f"Total rows: {total_rows}"
        )

        logging.info(
            "Skipped (not Mey Diageo): "
            f"{skipped_value_stream}"
        )

        logging.info(
            "Skipped (Skip Scan=true): "
            f"{skipped_scan}"
        )

        logging.info(
            "Skipped (no IP): "
            f"{skipped_no_ip}"
        )

        logging.info(
            f"Filtered IPs: {len(filtered_ips)}"
        )

        # Remove duplicates while preserving order
        unique_ips = list(
            dict.fromkeys(
                filtered_ips
            )
        )

        # Generate group name
        now = datetime.now()

        timestamp = now.strftime(
            "%d%m%y%H%M"
        )

        group_name = (
            f"VulnScan-{cycle_id}-"
            f"MeyDiageo-{timestamp}-"
            f"Batch-0"
        )

        # Create response
        response = {
            "groupsForCreation": [
                {
                    "name": group_name,
                    "ips": unique_ips
                }
            ]
        }

        logging.info(
            f"Successfully processed "
            f"{len(unique_ips)} IPs "
            f"for cycle {cycle_id}"
        )

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )

    except json.JSONDecodeError:

        logging.error(
            "Invalid JSON in request body"
        )

        return func.HttpResponse(
            json.dumps({
                "error":
                    "Invalid JSON format"
            }),
            status_code=400,
            mimetype="application/json"
        )

    except ValueError as e:

        logging.error(
            f"Required column not found: {str(e)}"
        )

        return func.HttpResponse(
            json.dumps({
                "error":
                    "Required columns not found in Excel",
                "details":
                    str(e)
            }),
            status_code=400,
            mimetype="application/json"
        )

    except Exception as e:

        logging.error(
            f"Unexpected error: {str(e)}"
        )

        return func.HttpResponse(
            json.dumps({
                "error":
                    f"Internal server error: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )