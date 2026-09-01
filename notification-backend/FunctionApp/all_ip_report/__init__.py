import logging
import json
import base64
from io import BytesIO

import azure.functions as func
import openpyxl


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Extracts all IP addresses from CMDB report (Excel)
    where Skip Scan is not true.
    """

    logging.info(
        "Processing CMDB Excel report for all IPs "
        "(Skip Scan filtering)"
    )

    try:
        req_body = req.get_json()

        excel_content_base64 = req_body.get(
            "cmdbReportContent"
        )

        if not excel_content_base64:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "error":
                        "Missing required field: "
                        "cmdbReportContent"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Decode base64
        excel_bytes = base64.b64decode(
            excel_content_base64
        )

        logging.info(
            f"Decoded Excel bytes, length: "
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

        # Read headers
        headers = []

        for cell in sheet[1]:
            headers.append(cell.value)

        logging.info(
            f"Excel headers: {headers}"
        )

        # Find required columns
        try:
            ip_col = headers.index(
                "IP Address"
            )

            skip_scan_col = headers.index(
                "Skip Scan"
            )

        except ValueError:

            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "error":
                        "Required columns not found "
                        "in Excel",
                    "details":
                        "Missing 'IP Address' or "
                        "'Skip Scan' column"
                }),
                status_code=400,
                mimetype="application/json"
            )

        logging.info(
            "Column indices - "
            f"IP: {ip_col}, "
            f"Skip Scan: {skip_scan_col}"
        )

        filtered_ips = []

        total_rows = 0
        skipped_scan = 0
        skipped_no_ip = 0

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
                    f"Skip Scan: '{skip_scan}', "
                    f"IP: '{ip_address}'"
                )

            # Skip Scan filtering
            if skip_scan in [
                "true",
                "yes",
                "1"
            ]:

                skipped_scan += 1
                continue

            # Missing IP filtering
            if (
                not ip_address
                or ip_address == "None"
                or ip_address == ""
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
            "Skipped (Skip Scan=true): "
            f"{skipped_scan}"
        )

        logging.info(
            "Skipped (no IP): "
            f"{skipped_no_ip}"
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

        logging.info(
            f"Successfully processed "
            f"{len(unique_ips)} unique IPs "
            f"(removed {duplicates_removed} duplicates)"
        )

        response = {
            "success": True,

            "ipAddresses":
                unique_ips,

            "totalIPs":
                len(unique_ips),

            "duplicatesRemoved":
                duplicates_removed
        }

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
                "success": False,
                "error":
                    "Invalid JSON format"
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
                "success": False,
                "error":
                    f"Internal server error: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )