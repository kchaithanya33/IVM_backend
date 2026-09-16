import json
import logging
import base64
from datetime import datetime
import azure.functions as func
import pandas as pd
from io import BytesIO


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Azure Function to count rows with data in Import Id column from Excel/CSV file.
    """
    logging.info("Content Row Counter function processed a request.")

    try:
        # Parse request body
        req_body = req.get_json()

        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Invalid request body"}),
                status_code=400,
                mimetype="application/json"
            )

        # Get required parameters
        file_content = req_body.get("fileContent")
        cycle_id = req_body.get("cycleId", "")
        file_type = req_body.get("fileType", "xlsx")

        if not file_content:
            return func.HttpResponse(
                json.dumps({"error": "fileContent is required"}),
                status_code=400,
                mimetype="application/json"
            )

        # Count rows with Import Id data
        row_count = count_import_id_rows(file_content, file_type)

        response_data = {
            "cycleId": cycle_id,
            "rowCount": row_count,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "success"
        }

        logging.info(
            f"Successfully counted {row_count} rows with Import Id data"
        )

        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")

        return func.HttpResponse(
            json.dumps({
                "error": str(e),
                "status": "failed",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }),
            status_code=500,
            mimetype="application/json"
        )


def count_import_id_rows(file_content, file_type):
    """
    Count rows that have data in the Import Id column.
    """
    try:
        # Decode base64 content
        decoded_bytes = base64.b64decode(file_content)

        if file_type.lower() == "xlsx":
            # Read Excel file
            df = pd.read_excel(BytesIO(decoded_bytes))
        else:
            # Read CSV file
            df = pd.read_csv(BytesIO(decoded_bytes))

        # Find Import Id column
        import_id_col = None
        possible_names = {"importid"}

        for col in df.columns:
            col_normalized = (
                str(col)
                .lower()
                .strip()
                .replace(" ", "")
                .replace("_", "")
            )

            if col_normalized in possible_names:
                import_id_col = col
                break

        if import_id_col is None:
            available_columns = ", ".join(
                str(col) for col in df.columns.tolist()
            )

            raise Exception(
                f"Import Id column not found. "
                f"Available columns: {available_columns}"
            )

        # Count non-null and non-empty Import Id values
        import_id_series = df[import_id_col]

        non_empty_mask = (
            import_id_series.notna()
            & (import_id_series.astype(str).str.strip() != "")
            & (import_id_series.astype(str).str.strip().str.lower() != "nan")
        )

        return int(non_empty_mask.sum())

    except Exception as e:
        raise Exception(
            f"Failed to count Import Id rows: {str(e)}"
        )