import logging
import azure.functions as func
import pandas as pd
import base64
import json
import io
import re
import xml.etree.ElementTree as ET


def _extract_ips_from_simple_return(simple_return_xml: str) -> list[str]:
    """
    Extract IPv4 addresses mentioned in the Qualys SIMPLE_RETURN <TEXT>.

    Works with valid XML or raw string; returns de-duplicated ordered list.
    """
    text = ""

    if simple_return_xml:
        try:
            root = ET.fromstring(simple_return_xml)

            node = root.find(".//TEXT")

            text = (
                node.text
                if node is not None and node.text
                else simple_return_xml
            )

        except ET.ParseError:
            text = simple_return_xml

    ips = re.findall(
        r"(?:\d{1,3}\.){3}\d{1,3}",
        text or ""
    )

    seen = set()
    ordered = []

    for ip in ips:
        if ip not in seen:
            seen.add(ip)
            ordered.append(ip)

    return ordered


def _ensure_two_columns_at_end(
    df: pd.DataFrame,
    col1: str,
    col2: str
) -> pd.DataFrame:

    work = df.copy()

    if col1 not in work.columns:
        work[col1] = ""

    if col2 not in work.columns:
        work[col2] = ""

    cols = [
        c for c in work.columns
        if c not in (col1, col2)
    ] + [col1, col2]

    return work[cols]


def _apply_error_flags(
    df: pd.DataFrame,
    bad_ips: set[str]
) -> pd.DataFrame:

    out = df.copy()

    out.columns = out.columns.str.strip()

    if "IP Address" not in out.columns:
        raise ValueError(
            "IP Address column not found in Excel data."
        )

    out = _ensure_two_columns_at_end(
        out,
        "Error/Corrected",
        "Error Remarks"
    )

    ip_series = (
        out["IP Address"]
        .astype(str)
        .str.strip()
    )

    is_error = ip_series.isin(bad_ips)

    out.loc[
        is_error,
        "Error/Corrected"
    ] = "Error"

    out.loc[
        is_error,
        "Error Remarks"
    ] = "not in user account scope"

    return out


# ============================================================
# ERROR PROCESSOR
# ============================================================

def main(
    req: func.HttpRequest
) -> func.HttpResponse:

    try:
        body = req.get_json()

    except ValueError:

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": "Invalid JSON body."
            }),
            status_code=400,
            mimetype="application/json"
        )

    excel_b64 = body.get(
        "excelFileContent"
    )

    error_payload = body.get(
        "errorPayload"
    )

    if not excel_b64:

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error":
                    "Missing excelFileContent."
            }),
            status_code=400,
            mimetype="application/json"
        )

    if not error_payload:

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error":
                    "Missing errorPayload."
            }),
            status_code=400,
            mimetype="application/json"
        )

    simple_return_xml = None

    if isinstance(
        error_payload,
        dict
    ):

        try:

            arr = (
                error_payload.get(
                    "results"
                )
                or []
            )

            if (
                arr
                and isinstance(
                    arr[0],
                    dict
                )
            ):

                result = (
                    arr[0].get(
                        "result"
                    )
                    or {}
                )

                simple_return_xml = (
                    result.get(
                        "response"
                    )
                )

        except Exception:

            simple_return_xml = None

    if (
        not simple_return_xml
        and isinstance(
            error_payload,
            str
        )
    ):

        simple_return_xml = (
            error_payload
        )

    if not simple_return_xml:

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error":
                    "Qualys SIMPLE_RETURN XML "
                    "not found in errorPayload."
            }),
            status_code=400,
            mimetype="application/json"
        )

    # ========================================================
    # Extract bad IPs from Qualys SIMPLE_RETURN
    # ========================================================

    bad_ip_list = (
        _extract_ips_from_simple_return(
            simple_return_xml
        )
    )

    bad_ips = set(
        bad_ip_list
    )

    # ========================================================
    # Read Excel
    # ========================================================

    try:

        excel_bytes = base64.b64decode(
            excel_b64
        )

        df = pd.read_excel(
            io.BytesIO(excel_bytes),
            engine="openpyxl"
        )

    except Exception as e:

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error":
                    f"Failed to read Excel: {e}"
            }),
            status_code=400,
            mimetype="application/json"
        )

    # ========================================================
    # Apply Error Flags
    # ========================================================

    try:

        updated_df = _apply_error_flags(
            df,
            bad_ips
        )

    except Exception as e:

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": str(e)
            }),
            status_code=400,
            mimetype="application/json"
        )

    # ========================================================
    # Create Updated Excel
    # ========================================================

    out = io.BytesIO()

    with pd.ExcelWriter(
        out,
        engine="openpyxl"
    ) as writer:

        updated_df.to_excel(
            writer,
            index=False,
            sheet_name="CMDB"
        )

    data = out.getvalue()

    # ========================================================
    # Return Excel
    # ========================================================

    return func.HttpResponse(
        body=data,
        status_code=200,
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                'attachment; filename="cmdb_updated.xlsx"',

            "X-Rows-Marked-Error":
                str(
                    int(
                        (
                            updated_df.get(
                                "Error/Corrected"
                            )
                            == "Error"
                        ).sum()
                    )
                ),

            "X-Error-IPs":
                ",".join(bad_ip_list)
        }
    )
