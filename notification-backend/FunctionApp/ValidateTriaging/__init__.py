import logging
import json
import base64
import traceback
from io import BytesIO

import azure.functions as func

from shared_code.triaging_helpers import (
    validate_excel_file,
)


def main(req: func.HttpRequest) -> func.HttpResponse:

    logging.info(
        "Python HTTP trigger function processed a request "
        "to validate triaging sheet."
    )

    try:

        # ====================================================
        # Try to read JSON request
        # ====================================================

        try:

            request_body = req.get_json()
            json_request = True

        except ValueError:

            json_request = False

        # ====================================================
        # JSON request
        # ====================================================

        if json_request:

            # ------------------------------------------------
            # Validate request body
            # ------------------------------------------------

            if not request_body:

                return func.HttpResponse(
                    "Request body is empty. "
                    "Please send Excel file content "
                    "in the request body.",
                    status_code=400,
                )

            # ------------------------------------------------
            # Extract values
            # ------------------------------------------------

            excel_file_content = (
                request_body.get(
                    "excelFileContent"
                )
            )

            cycle_id = (
                request_body.get(
                    "cycleId"
                )
            )

            # ------------------------------------------------
            # Validate Excel content
            # ------------------------------------------------

            if not excel_file_content:

                return func.HttpResponse(
                    "Missing required field: "
                    "excelFileContent",
                    status_code=400,
                )

            # ------------------------------------------------
            # Validate cycle ID
            # ------------------------------------------------

            if not cycle_id:

                return func.HttpResponse(
                    "Missing required field: cycleId",
                    status_code=400,
                )

            # ------------------------------------------------
            # Decode Base64 Excel
            # ------------------------------------------------

            try:

                excel_bytes = base64.b64decode(
                    excel_file_content
                )

                excel_io = BytesIO(
                    excel_bytes
                )

            except Exception as e:

                logging.error(
                    "Failed to decode base64 content: "
                    f"{str(e)}"
                )

                return func.HttpResponse(
                    "Failed to decode Excel content: "
                    f"{str(e)}",
                    status_code=400,
                )

        # ====================================================
        # Raw Excel request
        # ====================================================

        else:

            # ------------------------------------------------
            # Read request body
            # ------------------------------------------------

            excel_bytes = req.get_body()

            if not excel_bytes:

                return func.HttpResponse(
                    "Request body is empty. "
                    "Please send Excel file content "
                    "or JSON payload.",
                    status_code=400,
                )

            # ------------------------------------------------
            # Get cycleId from query parameter
            # ------------------------------------------------

            cycle_id = req.params.get(
                "cycleId"
            )

            if not cycle_id:

                return func.HttpResponse(
                    "Missing required query parameter: "
                    "cycleId when using raw file content.",
                    status_code=400,
                )

            # ------------------------------------------------
            # Convert to BytesIO
            # ------------------------------------------------

            excel_io = BytesIO(
                excel_bytes
            )

        # ====================================================
        # Call shared validation helper
        # ====================================================

        (
            validation_issues,
            mismatch_tables,
            mismatch_excel,
        ) = validate_excel_file(
            excel_io,
            cycle_id,
        )

        # ====================================================
        # Build response
        # ====================================================

        response_data = {
            "cycleId": cycle_id,

            "validationSuccess": (
                len(validation_issues) == 0
            ),

            "validationIssues": validation_issues,

            "legacyMismatchTables": {
                "legacyToNonLegacyMismatch": (
                    mismatch_tables[0]
                ),

                "nonLegacyToLegacyMismatch": (
                    mismatch_tables[1]
                ),
            },
        }

        # ====================================================
        # Add mismatch Excel if available
        # ====================================================

        if mismatch_excel:

            response_data[
                "mismatchExcelFile"
            ] = mismatch_excel

            response_data[
                "mismatchExcelFileName"
            ] = (
                f"Legacy_Mismatches_"
                f"{cycle_id}.xlsx"
            )

        # ====================================================
        # Return response
        # ====================================================

        return func.HttpResponse(
            json.dumps(
                response_data
            ),
            mimetype="application/json",
            status_code=200,
        )

    except Exception as e:

        # ====================================================
        # Unexpected error
        # ====================================================

        logging.error(
            f"Error in ValidateTriaging: {str(e)}"
        )

        logging.error(
            traceback.format_exc()
        )

        return func.HttpResponse(
            "An error occurred during "
            f"triaging validation: {str(e)}",
            status_code=500,
        )