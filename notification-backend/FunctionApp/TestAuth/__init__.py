import logging
import json
import azure.functions as func
import os


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Test authentication configuration for DFN.
    """

    logging.info("Test authentication endpoint called")

    client_id = os.environ.get("CLIENT_ID")
    client_secret = os.environ.get("CLIENT_SECRET")

    if not client_id or not client_secret:
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": "Missing CLIENT_ID or CLIENT_SECRET configuration"
            }, indent=2),
            status_code=500,
            mimetype="application/json"
        )

    return func.HttpResponse(
        json.dumps({
            "success": True,
            "message": "Authentication configuration is present",
            "client_id_configured": bool(client_id),
            "client_secret_configured": bool(client_secret)
        }, indent=2),
        status_code=200,
        mimetype="application/json"
    )