import azure.functions as func
import json
import logging
import uuid

from shared_code.ExcelDataProcessor_helper import (
    process_vulnerability_excel,
    apply_business_logic,
    collect_remediated_ips,
    collect_open_ivm_ips_qids,
    generate_action_items,
)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to process Excel vulnerability data.

    This route is responsible only for:
    1. Receiving the HTTP request
    2. Reading request parameters
    3. Calling shared helper functions
    4. Combining the results
    5. Returning the HTTP response

    Business/data-processing logic is maintained in:
        shared_code/ExcelDataProcessor_helper.py
    """

    logging.info("Excel data processing function triggered.")

    try:
        # ---------------------------------------------------------
        # 1. Parse request body
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 2. Extract request parameters
        # ---------------------------------------------------------
        file_content = req_body.get("fileContent")

        file_name = req_body.get(
            "fileName",
            "vulnerability_data.xlsx"
        )

        task_id = req_body.get(
            "taskId",
            str(uuid.uuid4())
        )

        processing_type = req_body.get(
            "processingType",
            "WeeklySchedule"
        )

        requested_by = req_body.get(
            "requestedBy",
            "System"
        )

        # ---------------------------------------------------------
        # 3. Validate file content
        # ---------------------------------------------------------
        if not file_content:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "message": "No file content provided"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # ---------------------------------------------------------
        # 4. Process Excel file
        #
        # Actual Excel decoding, cleaning, DataFrame processing,
        # vulnerability record creation and statistics generation
        # are handled by the shared helper.
        # ---------------------------------------------------------
        processed_data = process_vulnerability_excel(
            file_content,
            task_id
        )

        # ---------------------------------------------------------
        # 5. Apply vulnerability business rules
        #
        # Rules such as:
        # - Open + Remediated
        # - Open + False Positive
        # - Open + Exception
        # - Expired Exception
        # - Expiring Exception
        #
        # are handled by the shared helper.
        # ---------------------------------------------------------
        business_logic_results = apply_business_logic(
            processed_data["data"]
        )

        # ---------------------------------------------------------
        # 6. Collect remediated IP addresses
        # ---------------------------------------------------------
        remediated_ip_results = collect_remediated_ips(
            processed_data["data"]
        )

        # ---------------------------------------------------------
        # 7. Collect Open IVM IPs and QIDs
        # ---------------------------------------------------------
        open_ivm_results = collect_open_ivm_ips_qids(
            processed_data["data"]
        )

        # ---------------------------------------------------------
        # 8. Generate action items
        # ---------------------------------------------------------
        action_items = generate_action_items(
            business_logic_results
        )

        # ---------------------------------------------------------
        # 9. Combine all processing results
        # ---------------------------------------------------------
        final_result = {
            **processed_data,
            "businessLogic": business_logic_results,
            "actionItems": action_items,
            "remediatedIPs": remediated_ip_results,
            "openIVMData": open_ivm_results
        }

        # ---------------------------------------------------------
        # 10. Log completion
        # ---------------------------------------------------------
        logging.info(
            f"Excel processing completed. Task ID: {task_id}"
        )

        logging.info(
            f"Total rows processed: "
            f"{processed_data['totalRows']}"
        )

        logging.info(
            f"Actions required: "
            f"{len(final_result['actionItems'])}"
        )

        logging.info(
            f"Remediated IPs found: "
            f"{remediated_ip_results['totalRemediatedIPs']}"
        )

        logging.info(
            f"Open IVM IPs found: "
            f"{open_ivm_results['totalOpenIPs']}"
        )

        # ---------------------------------------------------------
        # 11. Return successful response
        # ---------------------------------------------------------
        return func.HttpResponse(
            json.dumps(final_result),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:

        # ---------------------------------------------------------
        # 12. Error handling
        # ---------------------------------------------------------
        logging.error(
            f"Error processing Excel data: {str(e)}"
        )

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": f"Error processing Excel data: {str(e)}",
                "data": [],
                "totalRows": 0
            }),
            status_code=500,
            mimetype="application/json"
        )