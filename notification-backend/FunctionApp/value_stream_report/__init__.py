import azure.functions as func
import json
import logging
import uuid

from shared_code.ExcelDataProcessor_helper import (
    generate_complete_value_stream_reports,
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to generate complete value stream vulnerability reports.

    Generates:
        1. Summary table
        2. Online Monitoring table
        3. Age Bucket table

    This route is responsible only for:
        1. Receiving the HTTP request
        2. Reading request parameters
        3. Validating required inputs
        4. Calling the shared helper
        5. Logging the result
        6. Returning the HTTP response

    Main processing logic is maintained in:
        shared_code/ExcelDataProcessor_helper.py
    """

    logging.info(
        "Value stream report function triggered."
    )

    try:
        # Parse the request body
        req_body = req.get_json()

        if not req_body:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "No request body provided"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Extract parameters
        dfn_report_content = req_body.get(
            "dfnReportContent"
        )

        qualys_report_content = req_body.get(
            "qualysReportContent"
        )

        value_stream_name = req_body.get(
            "valueStreamName",
            ""
        )

        task_id = req_body.get(
            "taskId",
            str(uuid.uuid4())
        )

        cycle_id = req_body.get(
            "cycleId",
            ""
        )

        # Validate required inputs
        if not dfn_report_content:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "No DFN report content provided"
                }),
                status_code=400,
                mimetype="application/json"
            )

        if not value_stream_name:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "No value stream name provided"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Call shared business logic
        result = generate_complete_value_stream_reports(
            dfn_report_content,
            qualys_report_content,
            value_stream_name,
            task_id,
            cycle_id
        )

        logging.info(
            f"Complete value stream report completed. "
            f"Task ID: {task_id}"
        )

        logging.info(
            f"Value Stream: {value_stream_name}"
        )

        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(
            f"Error generating value stream report: {str(e)}"
        )

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": (
                    f"Error generating value stream report: {str(e)}"
                ),
                "taskId": (
                    task_id
                    if "task_id" in locals()
                    else "unknown"
                ),
                "valueStream": (
                    value_stream_name
                    if "value_stream_name" in locals()
                    else "unknown"
                )
            }),
            status_code=500,
            mimetype="application/json"
        )