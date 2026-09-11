import azure.functions as func
import json
import logging

from shared_code.ExcelDataProcessor_helper import (
    merge_qualys_reports,
)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function for merging Qualys reports.

    This route is responsible only for:
        1. Receiving the HTTP request
        2. Reading the request body
        3. Calling the shared helper
        4. Logging the result
        5. Returning the HTTP response

    Main processing logic is maintained in:
        shared_code/ExcelDataProcessor_helper.py
    """

    try:
        body = req.get_json()

        logging.info(
            f"Received request body keys: {list(body.keys())}"
        )

        result = merge_qualys_reports(body)

        logging.info(
            f"Returning result with merged report length: "
            f"{len(result['merge_qualys_report'])}, "
            f"missing DFN report length: "
            f"{len(result['missing_dfn_report'])}, "
            f"merge_qualys_sheet length: "
            f"{len(result['merge_qualys_sheet'])}, "
            f"missing_count: "
            f"{result['missing_count']}"
        )

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(
            "Error in merge_qualys_report: %s",
            str(e),
            exc_info=True
        )

        return func.HttpResponse(
            str(e),
            status_code=500
        )