import logging
import json
import base64
import io

from typing import List, Dict, Any

import pandas as pd
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Extract and filter open IPs based on CMDB Skip Scan configuration.

    Expected request body:
    {
        "openIPs": ["ip1", "ip2", "..."],
        "cmdbFileContent": "base64_encoded_excel_content",
        "cmdbFileName": "filename.xlsx",
        "cycleId": "cycle_id",
        "taskId": "task_id"
    }
    """

    logging.info(
        "OpenIPExtractor: Processing CMDB Skip Scan filter request"
    )

    try:
        # Parse request body
        req_body = req.get_json()

        if not req_body:
            return _create_error_response(
                "Request body is required",
                400,
                0,
                0,
                0
            )

        # Extract parameters
        open_ips = req_body.get(
            "openIPs",
            []
        )

        cmdb_file_content = req_body.get(
            "cmdbFileContent",
            ""
        )

        cmdb_file_name = req_body.get(
            "cmdbFileName",
            "cmdb_file.xlsx"
        )

        cycle_id = req_body.get(
            "cycleId",
            ""
        )

        task_id = req_body.get(
            "taskId",
            ""
        )

        processing_type = req_body.get(
            "processingType",
            "CMDBFilter"
        )

        logging.info(
            f"OpenIPExtractor: Processing "
            f"{len(open_ips)} open IPs against CMDB file: "
            f"{cmdb_file_name}"
        )

        # Validate request
        validation_result = _validate_request_parameters(
            open_ips,
            cmdb_file_content
        )

        if not validation_result["valid"]:
            return _create_error_response(
                validation_result["message"],
                400,
                len(open_ips),
                0,
                0
            )

        # Decode base64 file
        try:
            file_content = base64.b64decode(
                cmdb_file_content
            )

            logging.info(
                "OpenIPExtractor: Successfully decoded "
                f"base64 content, size: "
                f"{len(file_content)} bytes"
            )

        except Exception as e:

            logging.error(
                "OpenIPExtractor: Error decoding "
                f"base64 content: {str(e)}"
            )

            return _create_error_response(
                f"Error decoding file content: {str(e)}",
                400,
                len(open_ips),
                0,
                0
            )

        # Process CMDB Excel file
        cmdb_processing_result = (
            _process_cmdb_excel_file(
                file_content,
                cmdb_file_name
            )
        )

        if not cmdb_processing_result["success"]:
            return _create_error_response(
                cmdb_processing_result["message"],
                500,
                len(open_ips),
                0,
                0
            )

        df = cmdb_processing_result["dataframe"]
        sheet_info = cmdb_processing_result["sheet_info"]

        # Filter IPs
        filtering_result = _filter_ips_by_skip_scan(
            open_ips,
            df
        )

        # Prepare response
        response_data = {
            "success": True,

            "message": (
                f"Successfully processed {len(open_ips)} IPs. "
                f"Excluded "
                f"{len(filtering_result['excluded_ips'])} "
                f"IPs marked for skip scan."
            ),

            "filteredIPs":
                filtering_result["filtered_ips"],

            "excludedIPs":
                filtering_result["excluded_ips"],

            "totalOriginal":
                len(open_ips),

            "totalFiltered":
                len(filtering_result["filtered_ips"]),

            "totalExcluded":
                len(filtering_result["excluded_ips"]),

            "cycleId":
                cycle_id,

            "taskId":
                task_id,

            "cmdbFileName":
                cmdb_file_name,

            "processingType":
                processing_type,

            "processingDetails": {
                "cmdbRecordsProcessed":
                    len(df),

                "cmdbIPsWithSkipScan":
                    len(
                        filtering_result[
                            "skip_scan_ips"
                        ]
                    ),

                "sheetUsed":
                    sheet_info["sheet_used"],

                "availableSheets":
                    sheet_info["available_sheets"],

                "skipScanIPs":
                    list(
                        filtering_result[
                            "skip_scan_ips"
                        ]
                    ),

                "processingTimestamp":
                    pd.Timestamp.now().isoformat()
            },

            "statistics": {
                "filteringEfficiency":
                    round(
                        (
                            len(
                                filtering_result[
                                    "excluded_ips"
                                ]
                            )
                            / len(open_ips)
                        ) * 100,
                        2
                    ) if open_ips else 0,

                "retentionRate":
                    round(
                        (
                            len(
                                filtering_result[
                                    "filtered_ips"
                                ]
                            )
                            / len(open_ips)
                        ) * 100,
                        2
                    ) if open_ips else 0
            }
        }

        logging.info(
            "OpenIPExtractor: Processing completed successfully. "
            f"Original: {len(open_ips)}, "
            f"Filtered: "
            f"{len(filtering_result['filtered_ips'])}, "
            f"Excluded: "
            f"{len(filtering_result['excluded_ips'])}"
        )

        return func.HttpResponse(
            json.dumps(
                response_data,
                indent=2
            ),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:

        logging.error(
            "OpenIPExtractor: Unexpected error: "
            f"{str(e)}"
        )

        return _create_error_response(
            f"Unexpected error occurred: {str(e)}",
            500,
            len(open_ips)
            if "open_ips" in locals()
            else 0,
            0,
            0
        )


def _validate_request_parameters(
    open_ips: List[str],
    cmdb_file_content: str
) -> Dict[str, Any]:
    """Validate the request parameters."""

    if not open_ips:
        return {
            "valid": False,
            "message":
                "openIPs list is required and cannot be empty"
        }

    if not cmdb_file_content:
        return {
            "valid": False,
            "message":
                "cmdbFileContent is required"
        }

    return {
        "valid": True,
        "message": "Valid parameters"
    }


def _process_cmdb_excel_file(
    file_content: bytes,
    file_name: str
) -> Dict[str, Any]:
    """Process the CMDB Excel file."""

    try:

        excel_file = pd.ExcelFile(
            io.BytesIO(file_content)
        )

        available_sheets = (
            excel_file.sheet_names
        )

        logging.info(
            "OpenIPExtractor: Available sheets: "
            f"{available_sheets}"
        )

        # Find preferred sheet
        sheet_name = None

        priority_sheets = [
            "Processed_Data",
            "ProcessedData",
            "Data",
            "Sheet1"
        ]

        for priority_sheet in priority_sheets:

            if priority_sheet in available_sheets:
                sheet_name = priority_sheet
                break

        if not sheet_name:
            sheet_name = available_sheets[0]

        logging.info(
            "OpenIPExtractor: Using sheet: "
            f"{sheet_name}"
        )

        # Read Excel data
        df = pd.read_excel(
            io.BytesIO(file_content),
            sheet_name=sheet_name
        )

        logging.info(
            "OpenIPExtractor: Excel file loaded "
            f"successfully. Shape: {df.shape}"
        )

        logging.info(
            "OpenIPExtractor: Columns: "
            f"{list(df.columns)}"
        )

        # Required columns
        required_columns = [
            "IP Address",
            "Skip Scan"
        ]

        missing_columns = [
            col
            for col in required_columns
            if col not in df.columns
        ]

        # Alternative column names
        if missing_columns:

            column_mapping = {
                "IP Address": [
                    "IP_Address",
                    "IPAddress",
                    "IP",
                    "ip_address"
                ],

                "Skip Scan": [
                    "Skip_Scan",
                    "SkipScan",
                    "skip_scan",
                    "SKIP_SCAN"
                ]
            }

            for required_col in missing_columns:

                found = False

                for alt_col in column_mapping.get(
                    required_col,
                    []
                ):

                    if alt_col in df.columns:

                        df.rename(
                            columns={
                                alt_col:
                                    required_col
                            },
                            inplace=True
                        )

                        found = True

                        logging.info(
                            "OpenIPExtractor: Mapped "
                            f"column '{alt_col}' "
                            f"to '{required_col}'"
                        )

                        break

                if not found:
                    return {
                        "success": False,
                        "message": (
                            f"Missing required column "
                            f"'{required_col}' in CMDB file. "
                            f"Available columns: "
                            f"{list(df.columns)}"
                        )
                    }

        return {
            "success": True,
            "dataframe": df,
            "sheet_info": {
                "sheet_used":
                    sheet_name,

                "available_sheets":
                    available_sheets
            }
        }

    except Exception as e:

        logging.error(
            "OpenIPExtractor: Error reading "
            f"Excel file: {str(e)}"
        )

        return {
            "success": False,
            "message":
                f"Error reading Excel file: {str(e)}"
        }


def _filter_ips_by_skip_scan(
    open_ips: List[str],
    df: pd.DataFrame
) -> Dict[str, Any]:
    """Filter IPs based on Skip Scan configuration."""

    # Clean data
    df["IP Address"] = (
        df["IP Address"]
        .astype(str)
        .str.strip()
    )

    df["Skip Scan"] = (
        df["Skip Scan"]
        .fillna(False)
    )

    # Convert Skip Scan to boolean
    def convert_to_bool(value):

        if (
            pd.isna(value)
            or value == ""
            or value is None
        ):
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):

            return (
                bool(value)
                if not pd.isna(value)
                and value != 0
                else False
            )

        if isinstance(value, str):

            return value.lower().strip() in [
                "true",
                "1",
                "yes",
                "y",
                "1.0"
            ]

        return False

    df["Skip Scan"] = (
        df["Skip Scan"]
        .apply(convert_to_bool)
    )

    logging.info(
        "OpenIPExtractor: Skip Scan value "
        "distribution: "
        f"{df['Skip Scan'].value_counts().to_dict()}"
    )

    # IPs marked for skip scan
    skip_scan_ips = set(
        df[
            df["Skip Scan"] == True
        ]["IP Address"].tolist()
    )

    logging.info(
        "OpenIPExtractor: Found "
        f"{len(skip_scan_ips)} IPs marked "
        f"for skip scan: "
        f"{list(skip_scan_ips)}"
    )

    # Filter open IPs
    filtered_ips = []
    excluded_ips = []

    for ip in open_ips:

        ip_str = str(ip).strip()

        if ip_str in skip_scan_ips:

            excluded_ips.append(ip_str)

            logging.info(
                "OpenIPExtractor: Excluding IP "
                f"{ip_str} - marked for skip scan"
            )

        else:

            filtered_ips.append(ip_str)

    return {
        "filtered_ips":
            filtered_ips,

        "excluded_ips":
            excluded_ips,

        "skip_scan_ips":
            skip_scan_ips
    }


def _create_error_response(
    message: str,
    status_code: int,
    total_original: int,
    total_filtered: int,
    total_excluded: int
) -> func.HttpResponse:
    """Create standardized error response."""

    error_response = {
        "success": False,

        "message":
            message,

        "filteredIPs": [],

        "excludedIPs": [],

        "totalOriginal":
            total_original,

        "totalFiltered":
            total_filtered,

        "totalExcluded":
            total_excluded,

        "error": True,

        "timestamp":
            pd.Timestamp.now().isoformat()
    }

    return func.HttpResponse(
        json.dumps(error_response),
        status_code=status_code,
        mimetype="application/json"
    )