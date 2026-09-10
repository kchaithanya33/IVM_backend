import logging
import json

import azure.functions as func

from shared_code.dfn_helpers import (
    get_dfn_client,
    handle_excel_output_minimal,
    handle_csv_output_minimal
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to get DFN report and fill missing Import ID values only.

    Original route:
        get_dfn_report

    Supported methods:
        GET
        POST
    """

    logging.info(
        "DFN Integration function processed a request."
    )

    try:
        # ====================================================
        # GET DFN CLIENT
        # ====================================================

        dfn_client = get_dfn_client()

        if not dfn_client:

            return func.HttpResponse(
                json.dumps(
                    {
                        "error": "Configuration error",
                        "message":
                            "CLIENT_ID and CLIENT_SECRET "
                            "must be configured in "
                            "environment variables"
                    }
                ),
                status_code=500,
                mimetype="application/json"
            )

        # ====================================================
        # GET PARAMETERS FROM QUERY STRING
        # ====================================================

        report_id = req.params.get(
            "report_id",
            dfn_client.default_report_id
        )

        workspace_id = req.params.get(
            "workspace_id",
            dfn_client.default_workspace_id
        )

        output_format = req.params.get(
            "format",
            "csv"
        )

        # ====================================================
        # OPTIONAL TIMEOUT / RETRY PARAMETERS
        # ====================================================

        timeout = req.params.get(
            "timeout"
        )

        max_retries = req.params.get(
            "max_retries"
        )

        # ====================================================
        # POST REQUEST BODY OVERRIDES
        # ====================================================

        if req.method == "POST":

            try:

                req_body = req.get_json()

                if req_body:

                    report_id = req_body.get(
                        "report_id",
                        report_id
                    )

                    workspace_id = req_body.get(
                        "workspace_id",
                        workspace_id
                    )

                    output_format = req_body.get(
                        "format",
                        output_format
                    )

                    timeout = req_body.get(
                        "timeout",
                        timeout
                    )

                    max_retries = req_body.get(
                        "max_retries",
                        max_retries
                    )

            except ValueError:
                # Keep original behavior:
                # invalid/missing JSON body is ignored
                pass

        # ====================================================
        # CONVERT TIMEOUT TO INTEGER
        # ====================================================

        if timeout:

            try:

                timeout = int(timeout)

            except ValueError:

                timeout = None

        # ====================================================
        # CONVERT MAX RETRIES TO INTEGER
        # ====================================================

        if max_retries:

            try:

                max_retries = int(max_retries)

            except ValueError:

                max_retries = None

        # ====================================================
        # LOG PARAMETERS
        # ====================================================

        logging.info(
            f"Parameters - "
            f"Report ID: {report_id}, "
            f"Workspace ID: {workspace_id}, "
            f"Format: {output_format}"
        )

        # ====================================================
        # GET REPORT FROM DFN
        # ====================================================

        result = dfn_client.get_dfn_report(
            report_id,
            workspace_id,
            output_format,
            timeout,
            max_retries
        )

        # ====================================================
        # CHECK RESULT
        # ====================================================

        if (
            result is None
            or (
                isinstance(result, tuple)
                and len(result) != 2
            )
        ):

            return func.HttpResponse(
                json.dumps(
                    {
                        "error":
                            "Failed to retrieve DFN report",

                        "message":
                            "Could not retrieve data "
                            "from DFN API"
                    }
                ),
                status_code=500,
                mimetype="application/json"
            )

        # ====================================================
        # UNPACK RESULT
        # ====================================================

        report_data, data_type = result

        # ====================================================
        # EMPTY RESPONSE
        # ====================================================

        if not report_data:

            return func.HttpResponse(
                json.dumps(
                    {
                        "error":
                            "No data received from DFN API",

                        "message":
                            "The API returned an empty response"
                    }
                ),
                status_code=204,
                mimetype="application/json"
            )

        # ====================================================
        # LOG RECEIVED DATA
        # ====================================================

        logging.info(
            f"Received data - "
            f"Type: {data_type}, "
            f"Size: "
            f"{len(report_data) if report_data else 0} bytes"
        )

        # ====================================================
        # EXCEL OUTPUT
        # ====================================================

        if output_format.lower() in [
            "excel",
            "xlsx"
        ]:

            return handle_excel_output_minimal(
                report_data,
                data_type,
                report_id
            )

        # ====================================================
        # CSV OUTPUT
        # ====================================================

        else:

            return handle_csv_output_minimal(
                report_data,
                data_type,
                report_id
            )

    # ========================================================
    # GENERAL ERROR HANDLING
    # ========================================================

    except Exception as e:

        logging.error(
            f"Error in DFN Integration function: {e}"
        )

        return func.HttpResponse(
            json.dumps(
                {
                    "error":
                        "Internal server error",

                    "message":
                        str(e)
                }
            ),
            status_code=500,
            mimetype="application/json"
        )