import azure.functions as func
import json
import logging

from shared_code.ExcelDataProcessor_helper import (
    extract_missing_dfn_ips,
)


async def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()

        logging.info(
            f"Received request body keys: {list(body.keys())}"
        )

        result = extract_missing_dfn_ips(body)

        logging.info(
            f"Returning {len(result['missing_ips'])} "
            f"missing IP addresses"
        )

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        logging.error(
            "Error in ip_extracter_dfn: %s",
            str(e),
            exc_info=True
        )

        return func.HttpResponse(
            str(e),
            status_code=500
        )