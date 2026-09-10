import logging
import json
import azure.functions as func
import os
from datetime import datetime


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint.

    Returns the health status of the DFN Integration Function App
    and verifies whether the required DFN credentials are configured.
    """

    logging.info("Health check endpoint called")

    client_id = os.environ.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET")

    config_status = (
        "configured"
        if client_id and client_secret
        else "missing_credentials"
    )

    return func.HttpResponse(
        json.dumps(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "function_app": "DFN-Integration-Minimal-Processing",
                "version": "2.3",
                "configuration": config_status,
                "features": [
                    "Import ID filling only (IP_QID_Port format)",
                    "Preserves original data structure and order",
                    "No column removal or data cleaning",
                    "Minimal processing approach"
                ]
            },
            indent=2
        ),
        status_code=200 if config_status == "configured" else 503,
        mimetype="application/json"
    )