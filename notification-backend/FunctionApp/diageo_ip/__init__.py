import logging
import json
import base64
from io import BytesIO

import azure.functions as func
import openpyxl


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Filters CMDB report (Excel) for all Diageo IPs
    except Mey Diageo.

    Expected input:
    {
        "cmdbReportContent": "base64_encoded_excel_content"
    }

    Returns:
    {
        "assets": [
            {
                "ip": "10.100.2.10",
                "hostname": "",
                "original_entry": "10.100.2.10",
                "source_element": "IP_SET/IP"
            }
        ],
        "totalAssets": 134,
        "expandRanges": true,
        "originalEntries": 156,
        "duplicatesRemoved": 67
    }
    """

    logging.info(
        "Processing CMDB Excel report for "
        "Diageo IPs (excluding Mey Diageo)"
    )

    try:
        req_body = req.get_json()

        excel_content_base64 = req_body.get(
            "cmdbReportContent"
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

        logging.info(
            "Received Excel content, base64 length: "
            f"{len(excel_content_base64)}"
        )

        # Decode base64
        excel_bytes = base64.b64decode(
            excel_content_base64
        )

        logging.info(
            "Decoded Excel bytes, length: "
            f"{len(excel_bytes)}"
        )

        # Load Excel
        workbook = openpyxl.load_workbook(
            BytesIO(excel_bytes),
            data_only=True
        )

        sheet = workbook.active

        logging.info(
            "Excel loaded successfully, "
            f"active sheet: {sheet.title}"
        )

        # Get headers
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

        # Filtering variables
        filtered_ips = []

        total_rows = 0
        skipped_mey_diageo = 0
        skipped_scan = 0
        skipped_no_ip = 0
        original_entries = 0

        # Process rows
        for row_num, row in enumerate(
            sheet.iter_rows(
                min_row=2,
                values_only=True
            ),
            start=2
        ):

            total_rows += 1

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

            # Debug first few rows
            if total_rows <= 3:

                logging.info(
                    f"Row {row_num} - "
                    f"Value Stream: '{value_stream}', "
                    f"Skip Scan: '{skip_scan}', "
                    f"IP: '{ip_address}'"
                )

            # Count original entries
            if (
                ip_address
                and ip_address != "None"
            ):
                original_entries += 1

            # Exclude Mey Diageo
            if value_stream == "Mey Diageo":

                skipped_mey_diageo += 1
                continue

            # Exclude Skip Scan
            if skip_scan in [
                "true",
                "yes",
                "1"
            ]:

                skipped_scan += 1
                continue

            # Exclude missing IP
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
            "Skipped (Mey Diageo): "
            f"{skipped_mey_diageo}"
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
            f"Original entries: {original_entries}"
        )

        logging.info(
            "Filtered IPs before dedup: "
            f"{len(filtered_ips)}"
        )

        # Remove duplicates while preserving order
        unique_ips = list(
            dict.fromkeys(
                filtered_ips
            )
        )

        duplicates_removed = (
            len(filtered_ips)
            - len(unique_ips)
        )

        # Build assets
        assets = []

        for ip in unique_ips:

            assets.append({
                "ip": ip,
                "hostname": "",
                "original_entry": ip,
                "source_element": "IP_SET/IP"
            })

        # Response
        response = {
            "assets": assets,

            "totalAssets":
                len(unique_ips),

            "expandRanges":
                True,

            "originalEntries":
                original_entries,

            "duplicatesRemoved":
                duplicates_removed
        }

        logging.info(
            "Successfully processed "
            f"{len(unique_ips)} unique IPs "
            f"(removed {duplicates_removed} duplicates)"
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
            "Required column not found: "
            f"{str(e)}"
        )

        return func.HttpResponse(
            json.dumps({
                "error":
                    "Required columns not found "
                    "in Excel",

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