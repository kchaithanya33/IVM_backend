import logging
import azure.functions as func
import pandas as pd
import base64
import json
import io


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info(
        "=== SKIP IPS FUNCTION STARTED ==="
    )

    try:
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

        if (
            not body
            or "excelFileContent" not in body
        ):
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "error":
                        "Missing 'excelFileContent' "
                        "in request body."
                }),
                status_code=400,
                mimetype="application/json"
            )

        excel_b64 = body[
            "excelFileContent"
        ]

        try:
            excel_bytes = base64.b64decode(
                excel_b64
            )

        except Exception as e:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "error":
                        f"Failed to decode "
                        f"excelFileContent: {str(e)}"
                }),
                status_code=400,
                mimetype="application/json"
            )

        df = pd.read_excel(
            io.BytesIO(excel_bytes),
            engine="openpyxl"
        )

        df.columns = (
            df.columns.str.strip()
        )

        if "IP Address" not in df.columns:
            return func.HttpResponse(
                json.dumps({
                    "success": False,
                    "error":
                        "Excel must contain "
                        "'IP Address' column."
                }),
                status_code=400,
                mimetype="application/json"
            )

        if "Skip Scan" not in df.columns:
            logging.warning(
                "'Skip Scan' column not found."
            )

            remaining_ips = _collect_all_ips(
                body
            )

            response = {
                "success": True,
                "message":
                    "No 'Skip Scan' column found. "
                    "No IPs removed.",
                "summary": {
                    "total_original_ips":
                        len(remaining_ips),

                    "ips_to_skip": 0,

                    "ips_removed": 0,

                    "final_ips_count":
                        len(remaining_ips)
                },
                "data":
                    _strip_excel_from_body(body),

                "remaining_ips":
                    sorted(
                        set(remaining_ips)
                    )
            }

            return func.HttpResponse(
                json.dumps(response),
                status_code=200,
                mimetype="application/json"
            )

        skip_mask = (
            df["Skip Scan"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin([
                "true",
                "1",
                "yes",
                "y"
            ])
        )

        skip_ips_list = (
            df.loc[
                skip_mask,
                "IP Address"
            ]
            .dropna()
            .astype(str)
            .str.strip()
            .tolist()
        )

        skip_ips_set = set(
            skip_ips_list
        )

        output_data = (
            _strip_excel_from_body(body)
        )

        removed_count = 0
        original_total = 0

        if (
            "batches" in output_data
            and isinstance(
                output_data["batches"],
                list
            )
        ):
            for batch in output_data["batches"]:

                if (
                    "assets" in batch
                    and isinstance(
                        batch["assets"],
                        list
                    )
                ):
                    original_assets = len(
                        batch["assets"]
                    )

                    original_total += (
                        original_assets
                    )

                    filtered_assets = []

                    for asset in batch["assets"]:

                        asset_ip = str(
                            asset.get(
                                "ip",
                                ""
                            )
                        ).strip()

                        if (
                            asset_ip
                            and asset_ip
                            not in skip_ips_set
                        ):
                            filtered_assets.append(
                                asset
                            )

                        elif (
                            asset_ip
                            in skip_ips_set
                        ):
                            removed_count += 1

                    batch["assets"] = (
                        filtered_assets
                    )

                    batch["asset_count"] = (
                        len(filtered_assets)
                    )

                if (
                    "ips" in batch
                    and isinstance(
                        batch["ips"],
                        list
                    )
                ):
                    before = len(
                        batch["ips"]
                    )

                    batch["ips"] = [
                        str(ip).strip()
                        for ip in batch["ips"]
                        if str(ip).strip()
                        not in skip_ips_set
                    ]

                    removed_count += (
                        before
                        - len(batch["ips"])
                    )

        if (
            "groups" in output_data
            and isinstance(
                output_data["groups"],
                list
            )
        ):
            for group in output_data["groups"]:

                if (
                    "ips" in group
                    and isinstance(
                        group["ips"],
                        list
                    )
                ):
                    before = len(
                        group["ips"]
                    )

                    group["ips"] = [
                        str(ip).strip()
                        for ip in group["ips"]
                        if str(ip).strip()
                        not in skip_ips_set
                    ]

                    removed_count += (
                        before
                        - len(group["ips"])
                    )

        remaining_ips = _collect_all_ips(
            output_data
        )

        response = {
            "success": True,

            "message":
                f"Removed {removed_count} IPs "
                f"based on 'Skip Scan' column.",

            "summary": {
                "total_original_ips":
                    original_total
                    if original_total
                    else
                    len(remaining_ips)
                    + removed_count,

                "ips_to_skip":
                    len(skip_ips_set),

                "ips_removed":
                    removed_count,

                "final_ips_count":
                    len(set(remaining_ips))
            },

            "data": output_data,

            "remaining_ips":
                sorted(
                    set(remaining_ips)
                )
        }

        logging.info(
            "=== SKIP IPS PROCESSING COMPLETE ==="
        )

        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:

        logging.exception(
            "ERROR in SkipIPs"
        )

        return func.HttpResponse(
            json.dumps({
                "success": False,
                "error": str(e)
            }),
            status_code=500,
            mimetype="application/json"
        )


def _strip_excel_from_body(
    body: dict
) -> dict:

    out = dict(body)

    out.pop(
        "excelFileContent",
        None
    )

    return out


def _collect_all_ips(
    payload: dict
) -> list:

    seen = set()
    result = []

    for batch in payload.get(
        "batches",
        []
    ) or []:

        for asset in batch.get(
            "assets",
            []
        ) or []:

            ip = str(
                asset.get(
                    "ip",
                    ""
                )
            ).strip()

            if (
                ip
                and ip not in seen
            ):
                seen.add(ip)
                result.append(ip)

        for ip in batch.get(
            "ips",
            []
        ) or []:

            sip = str(ip).strip()

            if (
                sip
                and sip not in seen
            ):
                seen.add(sip)
                result.append(sip)

    for group in payload.get(
        "groups",
        []
    ) or []:

        for ip in group.get(
            "ips",
            []
        ) or []:

            sip = str(ip).strip()

            if (
                sip
                and sip not in seen
            ):
                seen.add(sip)
                result.append(sip)

    return result