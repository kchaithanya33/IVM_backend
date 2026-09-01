import logging
import azure.functions as func
import base64
import json

from shared_code.qualys_helpers import encode_excel_data


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(
        '=== AZURE IP DATA PROCESSING FUNCTION STARTED ==='
    )

    try:
        try:
            req_body = req.get_json()

            if (
                req_body
                and 'excelFileContent' in req_body
            ):
                logging.info(
                    "Processing Logic App request format"
                )

                base64_content = (
                    req_body['excelFileContent']
                )

                file_content = (
                    base64.b64decode(
                        base64_content
                    )
                )

                include_filter = (
                    req_body.get('filter')
                )

                exclude_filter = (
                    req_body.get('excludefilter')
                )

                existing_excel_content = (
                    req_body.get(
                        'existingExcelContent'
                    )
                )

                enable_tag_comparison = (
                    req_body.get(
                        'enableTagComparison',
                        False
                    )
                )

                add_skip_status = (
                    req_body.get(
                        'addSkipStatus',
                        False
                    )
                )

                comparison_column = (
                    req_body.get(
                        'comparisonColumn',
                        'Tags'
                    )
                )

                key_columns = (
                    req_body.get(
                        'keyColumns',
                        ['Name', 'IP Address']
                    )
                )

                result = encode_excel_data(
                    file_content,
                    include_filter,
                    exclude_filter,
                    existing_excel_content,
                    enable_tag_comparison,
                    add_skip_status,
                    comparison_column,
                    key_columns
                )

                if result['success']:
                    logging.info(
                        "=== PROCESSING SUCCESSFUL ==="
                    )

                    return func.HttpResponse(
                        result['excel_data'],
                        status_code=200,
                        mimetype=(
                            "application/vnd.openxmlformats-"
                            "officedocument.spreadsheetml.sheet"
                        ),
                        headers={
                            'Content-Disposition':
                                f'attachment; filename="'
                                f'{req_body.get("filename", "processed_data.xlsx")}"',

                            'X-Row-Count':
                                str(
                                    result.get(
                                        'row_count',
                                        0
                                    )
                                ),

                            'X-Original-Count':
                                str(
                                    result.get(
                                        'original_count',
                                        0
                                    )
                                ),

                            'X-Unique-IPs':
                                str(
                                    result.get(
                                        'unique_ips',
                                        0
                                    )
                                ),

                            'X-Updated-Tags':
                                str(
                                    result.get(
                                        'updated_tags',
                                        0
                                    )
                                ),

                            'X-Qualys-Updated-Tags':
                                str(
                                    result.get(
                                        'qualys_updated_tags',
                                        0
                                    )
                                ),

                            'X-Missing-IPs-Count':
                                str(
                                    len(
                                        result.get(
                                            'missing_ips',
                                            []
                                        )
                                    )
                                ),

                            'X-Missing-IPs':
                                ','.join(
                                    result.get(
                                        'missing_ips',
                                        []
                                    )
                                )
                                if result.get(
                                    'missing_ips'
                                )
                                else 'none'
                        }
                    )

                else:
                    return func.HttpResponse(
                        json.dumps({
                            "error":
                                f"Error processing Excel file: "
                                f"{result['error']}"
                        }),
                        status_code=500,
                        mimetype="application/json"
                    )

        except (
            ValueError,
            TypeError
        ) as json_error:

            logging.info(
                f"JSON parsing failed, "
                f"trying binary handling: "
                f"{str(json_error)}"
            )

        # ----------------------------------------------------
        # Direct file upload
        # ----------------------------------------------------

        logging.info(
            "Processing direct file upload request"
        )

        operation = (
            req.params.get(
                'operation',
                'encode'
            ).lower()
        )

        if operation == 'encode':

            file_content = req.get_body()

            if not file_content:
                return func.HttpResponse(
                    json.dumps({
                        "error":
                            "Please pass an Excel file "
                            "in the request body."
                    }),
                    status_code=400,
                    mimetype="application/json"
                )

            include_filter = (
                req.params.get('filter')
            )

            exclude_filter = (
                req.params.get('excludefilter')
            )

            result = encode_excel_data(
                file_content,
                include_filter,
                exclude_filter
            )

            if result['success']:

                response_data = {
                    "encoded_data":
                        base64.b64encode(
                            result['excel_data']
                        ).decode('utf-8'),

                    "row_count":
                        result.get(
                            'row_count',
                            0
                        ),

                    "original_count":
                        result.get(
                            'original_count',
                            0
                        ),

                    "unique_ips":
                        result.get(
                            'unique_ips',
                            0
                        ),

                    "updated_tags":
                        result.get(
                            'updated_tags',
                            0
                        ),

                    "qualys_updated_tags":
                        result.get(
                            'qualys_updated_tags',
                            0
                        ),

                    "missing_ips":
                        result.get(
                            'missing_ips',
                            []
                        )
                }

                return func.HttpResponse(
                    json.dumps(response_data),
                    mimetype="application/json"
                )

            else:
                return func.HttpResponse(
                    json.dumps({
                        "error":
                            f"Error processing Excel file: "
                            f"{result['error']}"
                    }),
                    status_code=500,
                    mimetype="application/json"
                )

        else:

            return func.HttpResponse(
                json.dumps({
                    "error":
                        "Invalid operation. "
                        "Use 'encode' or 'decode'."
                }),
                status_code=400,
                mimetype="application/json"
            )

    except Exception as e:

        logging.error(
            f"UNEXPECTED ERROR in process_ip_data: "
            f"{str(e)}",
            exc_info=True
        )

        return func.HttpResponse(
            json.dumps({
                "error":
                    f"An error occurred: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )