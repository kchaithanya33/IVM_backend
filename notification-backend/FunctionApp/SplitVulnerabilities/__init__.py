import base64
import datetime
import io
import json
import logging
import os
import tempfile
import time
import traceback
from io import StringIO

import azure.functions as func
import pandas as pd
import xlsxwriter


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Split vulnerabilities into New and Old based on ID column
    New Vulnerabilities: ID column is blank/empty
    Old Vulnerabilities: ID column has a value
    """
    function_start_time = time.time()
    logging.info(
        'Python HTTP trigger function processed a request to split vulnerabilities.'
    )

    try:
        req_body = req.get_json()

        if not req_body:
            return func.HttpResponse(
                "Invalid JSON request body",
                status_code=400
            )

        cycle_id = req_body.get('cycleId')
        excel_content = req_body.get('excelContent')
        file_type = req_body.get('fileType', 'xlsx')

        # Validate required parameters
        missing_params = []

        if not cycle_id:
            missing_params.append("cycleId")

        if not excel_content:
            missing_params.append("excelContent")

        if missing_params:
            return func.HttpResponse(
                f"Missing required parameters: {', '.join(missing_params)}",
                status_code=400
            )

        logging.info(
            f"Processing vulnerability split for cycle ID: {cycle_id}"
        )

        # Process Excel file
        try:
            logging.info("Processing Excel content from request")

            # Decode base64 content
            binary_content = base64.b64decode(excel_content)

            # Read Excel file
            if file_type == 'xlsx':
                with tempfile.NamedTemporaryFile(
                    suffix='.xlsx',
                    delete=False
                ) as temp_file:

                    temp_file.write(binary_content)
                    temp_filename = temp_file.name

                try:
                    # Try to read the Excel file
                    excel_file = pd.ExcelFile(temp_filename)
                    sheet_names = excel_file.sheet_names

                    logging.info(
                        f"Excel file contains sheets: {sheet_names}"
                    )

                    # Read the first sheet
                    df = pd.read_excel(
                        temp_filename,
                        sheet_name=0
                    )

                    logging.info(
                        f"Read Excel file with {len(df)} rows "
                        f"and {len(df.columns)} columns"
                    )

                finally:
                    # Clean up temp file
                    try:
                        os.unlink(temp_filename)
                    except Exception as e:
                        logging.warning(
                            f"Failed to delete temp file "
                            f"{temp_filename}: {str(e)}"
                        )

            else:
                # Handle CSV if needed
                csv_str = binary_content.decode('utf-8')

                df = pd.read_csv(
                    StringIO(csv_str)
                )

                logging.info(
                    f"Read CSV file with {len(df)} rows "
                    f"and {len(df.columns)} columns"
                )

            if df.empty:
                raise ValueError("Excel file contains no data")

            # Check if ID column exists
            if 'ID' not in df.columns:

                # Try case-insensitive search
                id_candidates = [
                    col
                    for col in df.columns
                    if col.lower() == 'id'
                ]

                if id_candidates:
                    df = df.rename(
                        columns={
                            id_candidates[0]: 'ID'
                        }
                    )

                    logging.info(
                        f"Renamed column "
                        f"'{id_candidates[0]}' to 'ID'"
                    )

                else:
                    raise ValueError(
                        "Column 'ID' not found in the Excel file"
                    )

            logging.info(
                f"Successfully processed Excel data "
                f"with {len(df)} rows"
            )

        except Exception as e:
            logging.error(
                f"Failed to process Excel data: {str(e)}\n"
                f"{traceback.format_exc()}"
            )

            return func.HttpResponse(
                f"Failed to process Excel data: {str(e)}",
                status_code=500
            )

        # Split vulnerabilities based on ID column
        logging.info("=== SPLITTING VULNERABILITIES ===")

        # New Vulnerabilities:
        # ID is blank/empty/null
        new_vulns_df = df[
            df['ID'].isna()
            |
            (df['ID'].astype(str).str.strip() == '')
            |
            (
                df['ID']
                .astype(str)
                .str.strip()
                .str.lower()
                == 'nan'
            )
        ].copy()

        # Old Vulnerabilities:
        # ID has a value
        old_vulns_df = df[
            df['ID'].notna()
            &
            (df['ID'].astype(str).str.strip() != '')
            &
            (
                df['ID']
                .astype(str)
                .str.strip()
                .str.lower()
                != 'nan'
            )
        ].copy()

        new_count = len(new_vulns_df)
        old_count = len(old_vulns_df)
        total_count = len(df)

        logging.info("=== SPLIT RESULTS ===")
        logging.info(
            f"Total vulnerabilities: {total_count}"
        )
        logging.info(
            f"New vulnerabilities (ID blank): {new_count}"
        )
        logging.info(
            f"Old vulnerabilities (ID has value): {old_count}"
        )
        logging.info(
            f"Verification: {new_count + old_count} = {total_count}"
        )

        # Verify split
        if new_count + old_count != total_count:
            logging.warning(
                "Split verification failed! Sum doesn't match total."
            )

        # Create Excel workbook with two sheets
        logging.info(
            "Creating Excel workbook with two sheets"
        )

        try:
            excel_buffer = io.BytesIO()

            workbook = xlsxwriter.Workbook(
                excel_buffer,
                {'in_memory': True}
            )

            # No special formatting - plain Excel

            # Helper function to write dataframe to worksheet
            def write_dataframe_to_sheet(
                worksheet,
                dataframe,
                sheet_name
            ):
                """Write dataframe to worksheet - plain format"""

                # Write headers
                for col_num, column_name in enumerate(
                    dataframe.columns
                ):
                    worksheet.write(
                        0,
                        col_num,
                        column_name
                    )

                # Write data
                for row_num, (_, row_data) in enumerate(
                    dataframe.iterrows(),
                    1
                ):
                    for col_num, cell_value in enumerate(
                        row_data
                    ):
                        display_value = (
                            ''
                            if pd.isna(cell_value)
                            else cell_value
                        )

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value
                        )

                logging.info(
                    f"Written {len(dataframe)} rows "
                    f"to '{sheet_name}' sheet"
                )

            # Create New Vulnerabilities sheet
            if new_count > 0:
                new_worksheet = workbook.add_worksheet(
                    "New Vulnerabilities"
                )

                write_dataframe_to_sheet(
                    new_worksheet,
                    new_vulns_df,
                    "New Vulnerabilities"
                )
            else:
                logging.warning(
                    "No new vulnerabilities found - "
                    "skipping sheet creation"
                )

            # Create Old Vulnerabilities sheet
            if old_count > 0:
                old_worksheet = workbook.add_worksheet(
                    "Old Vulnerabilities"
                )

                write_dataframe_to_sheet(
                    old_worksheet,
                    old_vulns_df,
                    "Old Vulnerabilities"
                )
            else:
                logging.warning(
                    "No old vulnerabilities found - "
                    "skipping sheet creation"
                )

            # Close workbook and get bytes
            workbook.close()

            excel_buffer.seek(0)
            excel_bytes = excel_buffer.read()

            logging.info(
                "Successfully created Excel workbook "
                "with split vulnerabilities"
            )

        except Exception as e:
            logging.error(
                f"Error creating Excel workbook: {str(e)}\n"
                f"{traceback.format_exc()}"
            )

            return func.HttpResponse(
                f"Failed to create Excel workbook: {str(e)}",
                status_code=500
            )

        # Calculate statistics for each category
        def get_severity_stats(dataframe):
            """Calculate severity statistics for a dataframe"""

            stats = {
                'total': len(dataframe),
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }

            if (
                'Severity' in dataframe.columns
                and len(dataframe) > 0
            ):
                stats['critical'] = len(
                    dataframe[
                        dataframe['Severity'] == 'Critical'
                    ]
                )

                stats['high'] = len(
                    dataframe[
                        dataframe['Severity'] == 'High'
                    ]
                )

                stats['medium'] = len(
                    dataframe[
                        dataframe['Severity'] == 'Medium'
                    ]
                )

                stats['low'] = len(
                    dataframe[
                        dataframe['Severity'] == 'Low'
                    ]
                )

            return stats

        new_stats = get_severity_stats(
            new_vulns_df
        )

        old_stats = get_severity_stats(
            old_vulns_df
        )

        function_duration = (
            time.time() - function_start_time
        )

        timestamp = datetime.datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = (
            f"split_vulnerabilities_"
            f"{cycle_id}_"
            f"{timestamp}.xlsx"
        )

        return func.HttpResponse(
            excel_bytes,
            mimetype=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": (
                    f"attachment; filename={filename}"
                ),

                "Content-Type": (
                    "application/vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),

                "Cache-Control": "no-cache",

                # Overall stats
                "X-Total-Vulnerabilities": str(
                    total_count
                ),

                "X-Processing-Time": (
                    f"{function_duration:.2f}s"
                ),

                "X-Cycle-ID": cycle_id,

                # New vulnerabilities stats
                "X-New-Total": str(
                    new_stats['total']
                ),

                "X-New-Critical": str(
                    new_stats['critical']
                ),

                "X-New-High": str(
                    new_stats['high']
                ),

                "X-New-Medium": str(
                    new_stats['medium']
                ),

                "X-New-Low": str(
                    new_stats['low']
                ),

                # Old vulnerabilities stats
                "X-Old-Total": str(
                    old_stats['total']
                ),

                "X-Old-Critical": str(
                    old_stats['critical']
                ),

                "X-Old-High": str(
                    old_stats['high']
                ),

                "X-Old-Medium": str(
                    old_stats['medium']
                ),

                "X-Old-Low": str(
                    old_stats['low']
                )
            },
            status_code=200
        )

    except Exception as e:
        function_duration = (
            time.time() - function_start_time
        )

        error_type = type(e).__name__
        error_message = str(e)
        error_details = traceback.format_exc()

        logging.error(
            f"Error in split_vulnerabilities: "
            f"{error_type}: {error_message}\n"
            f"{error_details}"
        )

        user_message = error_message

        if (
            isinstance(e, ValueError)
            and "Column 'ID' not found" in error_message
        ):
            user_message = (
                "The Excel file is missing the required "
                "'ID' column for splitting vulnerabilities."
            )

        elif isinstance(
            e,
            pd.errors.EmptyDataError
        ):
            user_message = (
                "The Excel file contains no data. "
                "Please verify the file contents."
            )

        elif (
            "Excel" in error_message
            or "workbook" in error_message.lower()
        ):
            user_message = (
                f"Excel processing error: {error_message}. "
                "The file might be corrupted or in an "
                "unsupported format."
            )

        error_response = {
            "status": "error",
            "message": user_message,
            "errorType": error_type,
            "details": error_details,
            "processingTime": (
                f"{function_duration:.2f} seconds"
            )
        }

        return func.HttpResponse(
            json.dumps(error_response),
            mimetype="application/json",
            headers={
                "X-Error-Type": error_type,
                "X-Processing-Time": (
                    f"{function_duration:.2f}s"
                )
            },
            status_code=500
        )

    finally:
        logging.info(
            "Split vulnerabilities function execution completed"
        )