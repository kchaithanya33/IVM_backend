import datetime
import json
import logging
import os
import time
import traceback

import azure.functions as func
import pandas as pd

from shared_code.helpers import (
    DFN_COLUMN_MAPPING,
    FINAL_TARGET_COLUMNS,
    create_excel_with_xlsxwriter,
    fix_port_column,
    normalize_import_id,
    process_file_content,
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    function_start_time = time.time()

    logging.info(
        "Python HTTP trigger function processed a request "
        "to identify new vulnerabilities."
    )

    temp_files = []

    try:
        # ============================================================
        # READ REQUEST BODY
        # ============================================================

        req_body = req.get_json()

        if not req_body:
            return func.HttpResponse(
                "Invalid JSON request body",
                status_code=400
            )

        cycle_id = req_body.get("cycleId")

        merged_content = req_body.get(
            "mergedReportContent"
        )

        dfn_content = req_body.get(
            "dfnReportContent"
        )

        merged_file_type = req_body.get(
            "mergedFileType",
            "xlsx"
        )

        dfn_file_type = req_body.get(
            "dfnFileType",
            "xlsx"
        )

        # ============================================================
        # VALIDATE REQUIRED PARAMETERS
        # ============================================================

        missing_params = []

        if not cycle_id:
            missing_params.append("cycleId")

        if not merged_content:
            missing_params.append(
                "mergedReportContent"
            )

        if not dfn_content:
            missing_params.append(
                "dfnReportContent"
            )

        if missing_params:
            return func.HttpResponse(
                f"Missing required parameters: "
                f"{', '.join(missing_params)}",
                status_code=400
            )

        logging.info(
            "Processing new vulnerabilities identification "
            f"for cycle ID: {cycle_id}"
        )

        # ============================================================
        # PROCESS MERGED REPORT
        # MINIMAL PROCESSING TO PRESERVE DATA
        # ============================================================

        try:
            logging.info(
                "Processing merged report from request content"
            )

            merged_df = process_file_content(
                merged_content,
                merged_file_type,
                "merged"
            )

            if len(merged_df) == 0:
                raise ValueError(
                    "Merged data contains no rows"
                )

            # --------------------------------------------------------
            # ONLY remove completely empty columns
            # PRESERVE ALL DATA
            # --------------------------------------------------------

            merged_df = merged_df.dropna(
                axis=1,
                how="all"
            )

            # --------------------------------------------------------
            # Fix Port column format
            # --------------------------------------------------------

            if "Port" in merged_df.columns:
                merged_df = fix_port_column(
                    merged_df
                )

                logging.info(
                    "Fixed Port column format "
                    "in merged data"
                )

            logging.info(
                "Successfully processed merged data "
                f"with {len(merged_df)} rows and "
                f"{len(merged_df.columns)} columns"
            )

            # --------------------------------------------------------
            # Data integrity check for merged report
            # --------------------------------------------------------

            critical_vuln_columns = [
                "Title",
                "Vulnerability Type",
                "Threat",
                "Impact",
                "Solution",
                "Severity"
            ]

            for col in critical_vuln_columns:

                if col in merged_df.columns:

                    populated = (
                        merged_df[col]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .ne("")
                        .sum()
                    )

                    missing = (
                        len(merged_df) - populated
                    )

                    if missing > 0:

                        logging.warning(
                            "INPUT DATA CHECK: "
                            f"{missing}/{len(merged_df)} "
                            f"rows missing '{col}' data "
                            "in merged report"
                        )

                    else:

                        logging.info(
                            f"✓ Column '{col}' fully populated: "
                            f"{populated}/{len(merged_df)} "
                            "rows in merged report"
                        )

        except Exception as e:

            logging.error(
                "Failed to process merged data: "
                f"{str(e)}\n"
                f"{traceback.format_exc()}"
            )

            return func.HttpResponse(
                f"Failed to process merged data: {str(e)}",
                status_code=500
            )

        # ============================================================
        # PROCESS DFN REPORT
        # ONLY TO GET IMPORT IDs FOR FILTERING
        # ============================================================

        try:
            logging.info(
                "Processing DFN data from request content"
            )

            dfn_df = process_file_content(
                dfn_content,
                dfn_file_type,
                "dfn"
            )

            dfn_df = dfn_df.dropna(
                axis=1,
                how="all"
            )

            # --------------------------------------------------------
            # Apply DFN column mapping
            # --------------------------------------------------------

            if not dfn_df.empty:

                dfn_df.rename(
                    columns=DFN_COLUMN_MAPPING,
                    inplace=True
                )

            # --------------------------------------------------------
            # Generate Import ID from IP + QID + Port
            # --------------------------------------------------------

            if (
                "Import Id" not in dfn_df.columns
                and not dfn_df.empty
                and all(
                    col in dfn_df.columns
                    for col in [
                        "IP",
                        "QID",
                        "Port"
                    ]
                )
            ):

                logging.info(
                    "Generating Import ID for DFN data "
                    "from IP, QID, and Port"
                )

                dfn_df["IP"] = (
                    dfn_df["IP"].astype(str)
                )

                dfn_df["QID"] = (
                    dfn_df["QID"].astype(str)
                )

                dfn_df["Import Id"] = (
                    dfn_df.apply(
                        lambda row:
                            normalize_import_id(
                                row["IP"],
                                row["QID"],
                                row.get(
                                    "Port",
                                    "NA"
                                )
                            ),
                        axis=1
                    )
                )

            # --------------------------------------------------------
            # Generate Import ID from IP + QID
            # No Port
            # --------------------------------------------------------

            elif (
                "Import Id" not in dfn_df.columns
                and not dfn_df.empty
                and all(
                    col in dfn_df.columns
                    for col in [
                        "IP",
                        "QID"
                    ]
                )
            ):

                logging.info(
                    "Generating Import ID for DFN data "
                    "from IP and QID (no Port)"
                )

                dfn_df["IP"] = (
                    dfn_df["IP"].astype(str)
                )

                dfn_df["QID"] = (
                    dfn_df["QID"].astype(str)
                )

                dfn_df["Import Id"] = (
                    dfn_df.apply(
                        lambda row:
                            f"{row['IP']}_{row['QID']}_",
                        axis=1
                    )
                )

            logging.info(
                "Successfully processed DFN data "
                f"with {len(dfn_df)} rows and "
                f"{len(dfn_df.columns)} columns"
            )

        except Exception as e:

            logging.error(
                "Failed to process DFN data: "
                f"{str(e)}\n"
                f"{traceback.format_exc()}"
            )

            return func.HttpResponse(
                f"Failed to process DFN data: {str(e)}",
                status_code=500
            )

        # ============================================================
        # VALIDATE REQUIRED COLUMNS
        # ============================================================

        if "Import Id" not in merged_df.columns:
            raise ValueError(
                "Column 'Import Id' not found "
                "in merged data"
            )

        if "Import Id" not in dfn_df.columns:
            raise ValueError(
                "Column 'Import Id' not found "
                "in DFN data"
            )

        # ============================================================
        # CORE FILTERING LOGIC
        # EXTRACT NEW VULNERABILITIES
        # ============================================================

        logging.info(
            "=== FILTERING NEW VULNERABILITIES ==="
        )

        merged_df["Import Id"] = (
            merged_df["Import Id"].astype(str)
        )

        dfn_ids = set(
            dfn_df["Import Id"]
            .astype(str)
            .dropna()
        )

        original_rows = len(
            merged_df
        )

        # ------------------------------------------------------------
        # Keep vulnerabilities NOT present in DFN
        # ------------------------------------------------------------

        result_df = merged_df[
            ~merged_df["Import Id"].isin(
                dfn_ids
            )
        ].copy()

        new_vulnerabilities_count = len(
            result_df
        )

        existing_vulnerabilities = (
            original_rows
            - new_vulnerabilities_count
        )

        logging.info(
            "=== NEW VULNERABILITIES "
            "FILTERING RESULTS ==="
        )

        logging.info(
            "Total vulnerabilities in merged report: "
            f"{original_rows}"
        )

        logging.info(
            "Existing vulnerabilities (in DFN): "
            f"{len(dfn_ids)}"
        )

        logging.info(
            "Matching vulnerabilities (removed): "
            f"{existing_vulnerabilities}"
        )

        logging.info(
            "New vulnerabilities (extracted): "
            f"{new_vulnerabilities_count}"
        )

        # ============================================================
        # POST-FILTER DATA INTEGRITY CHECK
        # ============================================================

        logging.info(
            "=== POST-FILTER DATA INTEGRITY CHECK ==="
        )

        for col in critical_vuln_columns:

            if col in result_df.columns:

                populated = (
                    result_df[col]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .ne("")
                    .sum()
                )

                missing = (
                    len(result_df) - populated
                )

                if missing > 0:

                    logging.warning(
                        "POST-FILTER: "
                        f"{missing}/{len(result_df)} "
                        f"new vulnerabilities missing "
                        f"'{col}' data"
                    )

                else:

                    logging.info(
                        f"✓ Column '{col}' fully populated: "
                        f"{populated}/{len(result_df)} "
                        "new vulnerabilities"
                    )

        # ============================================================
        # ENSURE ALL TARGET COLUMNS EXIST
        # ============================================================

        logging.info(
            "Ensuring all target columns exist "
            "and arranging in final order"
        )

        missing_target_cols = [
            col
            for col in FINAL_TARGET_COLUMNS
            if col not in result_df.columns
        ]

        if missing_target_cols:

            logging.info(
                "Adding missing target columns: "
                f"{missing_target_cols}"
            )

        for col in FINAL_TARGET_COLUMNS:

            if col not in result_df.columns:
                result_df[col] = ""

        # ============================================================
        # KEEP ONLY FINAL TARGET COLUMNS
        # EXACT ORDER
        # ============================================================

        result_df = result_df[
            FINAL_TARGET_COLUMNS
        ]

        # ============================================================
        # FINAL PORT COLUMN FIX
        # ============================================================

        if "Port" in result_df.columns:

            result_df = fix_port_column(
                result_df
            )

            logging.info(
                "Applied final Port column fix "
                "before Excel creation"
            )

        # ============================================================
        # FINAL DATA QUALITY VALIDATION
        # ============================================================

        logging.info(
            "=== FINAL DATA QUALITY VALIDATION ==="
        )

        total_rows = len(
            result_df
        )

        for col in [
            "Title",
            "Vulnerability Type",
            "Threat",
            "Impact",
            "Solution"
        ]:

            if col in result_df.columns:

                populated = (
                    result_df[col]
                    .fillna("")
                    .astype(str)
                    .str.strip()
                    .ne("")
                    .sum()
                )

                missing = (
                    total_rows - populated
                )

                if missing > 0:

                    logging.error(
                        "FINAL OUTPUT ISSUE: "
                        f"{missing}/{total_rows} "
                        f"rows missing '{col}' data"
                    )

                else:

                    logging.info(
                        f"✓ Column '{col}' fully populated: "
                        f"{populated}/{total_rows} rows"
                    )

        # ============================================================
        # CREATE EXCEL WORKBOOK
        # ============================================================

        logging.info(
            "Creating Excel workbook with xlsxwriter"
        )

        excel_bytes = (
            create_excel_with_xlsxwriter(
                result_df,
                cycle_id,
                "New Vulnerabilities Report"
            )
        )

        # ============================================================
        # CALCULATE STATISTICS
        # ============================================================

        total_new_vulnerabilities = (
            len(result_df)
        )

        critical_count = (
            len(
                result_df[
                    result_df["Severity"]
                    == "Critical"
                ]
            )
            if "Severity" in result_df.columns
            else 0
        )

        high_count = (
            len(
                result_df[
                    result_df["Severity"]
                    == "High"
                ]
            )
            if "Severity" in result_df.columns
            else 0
        )

        medium_count = (
            len(
                result_df[
                    result_df["Severity"]
                    == "Medium"
                ]
            )
            if "Severity" in result_df.columns
            else 0
        )

        low_count = (
            len(
                result_df[
                    result_df["Severity"]
                    == "Low"
                ]
            )
            if "Severity" in result_df.columns
            else 0
        )

        # ============================================================
        # PROCESSING TIME / FILE NAME
        # ============================================================

        function_duration = (
            time.time()
            - function_start_time
        )

        timestamp = (
            datetime.datetime.now()
            .strftime("%Y%m%d_%H%M%S")
        )

        filename = (
            f"new_vulnerabilities_"
            f"{cycle_id}_"
            f"{timestamp}.xlsx"
        )

        # ============================================================
        # RETURN EXCEL RESPONSE
        # ============================================================

        return func.HttpResponse(
            excel_bytes,
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition":
                    f"attachment; filename={filename}",

                "Content-Type":
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet",

                "Cache-Control":
                    "no-cache",

                "X-Total-New-Vulnerabilities":
                    str(
                        total_new_vulnerabilities
                    ),

                "X-Critical-Count":
                    str(critical_count),

                "X-High-Count":
                    str(high_count),

                "X-Medium-Count":
                    str(medium_count),

                "X-Low-Count":
                    str(low_count),

                "X-Processing-Time":
                    f"{function_duration:.2f}s",

                "X-Cycle-ID":
                    cycle_id,

                "X-Original-Rows":
                    str(original_rows),

                "X-Existing-Vulnerabilities":
                    str(
                        existing_vulnerabilities
                    ),

                "X-New-Vulnerabilities":
                    str(
                        total_new_vulnerabilities
                    )
            },
            status_code=200
        )

    # ================================================================
    # GLOBAL ERROR HANDLING
    # ================================================================

    except Exception as e:

        function_duration = (
            time.time()
            - function_start_time
        )

        error_type = type(e).__name__
        error_message = str(e)
        error_details = traceback.format_exc()

        logging.error(
            "Error in new_vulnerabilities: "
            f"{error_type}: {error_message}\n"
            f"{error_details}"
        )

        user_message = error_message

        if (
            isinstance(e, ValueError)
            and "Missing required columns"
            in error_message
        ):

            user_message = (
                f"Schema validation failed: "
                f"{error_message}. "
                "Please ensure the input files "
                "contain all required columns."
            )

        elif isinstance(
            e,
            pd.errors.EmptyDataError
        ):

            user_message = (
                "One or more input files contains "
                "no data. Please verify the "
                "file contents."
            )

        elif "Excel" in error_message:

            user_message = (
                f"Excel processing error: "
                f"{error_message}. "
                "The file might be corrupted or "
                "in an unsupported format."
            )

        error_response = {
            "status": "error",
            "message": user_message,
            "errorType": error_type,
            "details": error_details,
            "processingTime":
                f"{function_duration:.2f} seconds"
        }

        return func.HttpResponse(
            json.dumps(error_response),
            mimetype="application/json",
            headers={
                "X-Error-Type":
                    error_type,

                "X-Processing-Time":
                    f"{function_duration:.2f}s"
            },
            status_code=500
        )

    # ================================================================
    # FINALLY
    # ================================================================

    finally:

        for temp_file in temp_files:

            try:

                if os.path.exists(temp_file):
                    os.unlink(temp_file)

            except Exception as e:

                logging.warning(
                    f"Failed to delete temp file "
                    f"{temp_file}: {str(e)}"
                )

        logging.info(
            "New vulnerabilities function "
            "execution completed"
        )