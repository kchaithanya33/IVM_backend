import logging
import json
import traceback
import io
from datetime import datetime

import pandas as pd
import azure.functions as func


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Route to process asset data from Excel file.

    Query parameters:
    - cycleName: Name of the cycle for group creation
    - error_callback: Boolean flag ('true'/'false')
    - splitGroups: Boolean flag ('true'/'false')
    """

    logging.info(
        "Asset Data Preparation function processing a request."
    )

    try:
        # Read Excel binary data directly from request body
        excel_binary = req.get_body()

        if not excel_binary:
            return func.HttpResponse(
                json.dumps({
                    "error":
                        "Please pass Excel file in the request body"
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Get query parameters
        cycle_name = req.params.get("cycleName")

        error_callback = (
            req.params.get(
                "error_callback",
                "false"
            ).lower() == "true"
        )

        split_groups = (
            req.params.get(
                "splitGroups",
                "false"
            ).lower() == "true"
        )

        logging.info(
            f"Received cycle name: {cycle_name}"
        )

        logging.info(
            f"Error callback mode: {error_callback}"
        )

        logging.info(
            f"Split groups mode: {split_groups}"
        )

        # Convert binary data to DataFrame
        df = pd.read_excel(
            io.BytesIO(excel_binary),
            engine="openpyxl"
        )

        logging.info(
            "Successfully read Excel file "
            "using openpyxl engine"
        )

        # Convert DataFrame to list of dictionaries
        excel_data = df.to_dict("records")

        logging.info(
            f"Processing {len(excel_data)} assets "
            "from the Excel data."
        )

        # Process the data
        result = process_asset_data(
            excel_data,
            cycle_name,
            error_callback,
            split_groups
        )

        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:

        logging.error(
            "Error processing asset data: "
            f"{str(traceback.format_exc())}"
        )

        print(traceback.format_exc())

        return func.HttpResponse(
            json.dumps({
                "error":
                    f"Error processing asset data: {str(e)}"
            }),
            status_code=500,
            mimetype="application/json"
        )


def process_asset_data(
    excel_data,
    cycle_name=None,
    error_callback=False,
    split_groups=False
):
    """
    Process the Excel data to prepare assets
    for tagging and grouping.
    """

    mey_diageo_ips = []
    diageo_ips = []
    all_ips = []

    # Process each asset
    for asset in excel_data:

        ip = asset.get("IP Address")

        if not ip:
            continue

        # Determine whether IP should be skipped
        should_skip = should_skip_ip(
            asset,
            error_callback
        )

        if should_skip:

            logging.info(
                f"Skipping IP {ip} "
                "based on filtering rules"
            )

            continue

        ip_str = str(ip)

        # Split groups by Value Stream
        if split_groups:

            value_stream = str(
                asset.get(
                    "Value Stream",
                    ""
                )
            ).strip()

            if value_stream.lower() == "mey diageo":

                mey_diageo_ips.append(
                    ip_str
                )

                logging.info(
                    f"Added IP {ip_str} "
                    "to Mey Diageo group "
                    f"(Value Stream: {value_stream})"
                )

            else:

                diageo_ips.append(
                    ip_str
                )

                logging.info(
                    f"Added IP {ip_str} "
                    "to Diageo group "
                    f"(Value Stream: {value_stream})"
                )

        else:

            # Single group
            all_ips.append(ip_str)

    # Create groups
    current_date = datetime.now()

    if not cycle_name:

        cycle_name = (
            f"Cycle-{current_date.strftime('%B-%Y')}"
        )

    # Timestamp suffix
    timestamp_suffix = (
        current_date.strftime(
            "%d%m%y_%H%M%S"
        )
    )

    groups_for_creation = []

    if split_groups:

        # Mey Diageo group
        if mey_diageo_ips:

            groups_for_creation.append({
                "name":
                    f"{cycle_name}_MeyDiageo_"
                    f"{timestamp_suffix}",

                "ips":
                    mey_diageo_ips
            })

            logging.info(
                f"Created Mey Diageo group with "
                f"{len(mey_diageo_ips)} IPs - "
                f"Name: {cycle_name}_MeyDiageo_"
                f"{timestamp_suffix}"
            )

        # Diageo group
        if diageo_ips:

            groups_for_creation.append({
                "name":
                    f"{cycle_name}_Diageo_"
                    f"{timestamp_suffix}",

                "ips":
                    diageo_ips
            })

            logging.info(
                f"Created Diageo group with "
                f"{len(diageo_ips)} IPs - "
                f"Name: {cycle_name}_Diageo_"
                f"{timestamp_suffix}"
            )

    else:

        # Original single-group behavior
        groups_for_creation.append({
            "name":
                f"{cycle_name}_{timestamp_suffix}",

            "ips":
                all_ips
        })

        logging.info(
            f"Created single group "
            f"'{cycle_name}_{timestamp_suffix}' "
            f"with {len(all_ips)} IPs"
        )

    return {
        "groupsForCreation":
            groups_for_creation
    }


def should_skip_ip(
    asset,
    error_callback
):
    """
    Determine if an IP should be skipped based on
    Skip Scan and Error/Corrected columns.
    """

    # Get Skip Scan value
    skip_scan = asset.get("Skip Scan")

    skip_scan_is_true = False

    skip_scan_is_empty = (
        skip_scan is None
        or str(skip_scan).strip() == ""
        or pd.isna(skip_scan)
    )

    if not skip_scan_is_empty:

        skip_scan_str = (
            str(skip_scan)
            .strip()
            .lower()
        )

        skip_scan_is_true = (
            skip_scan_str == "true"
            or skip_scan_str == "1.0"
            or skip_scan_str == "1"
        )

    # error_callback=False:
    # only check Skip Scan
    if not error_callback:

        if skip_scan_is_true:

            logging.info(
                "error_callback=False: "
                "Skipping because Skip Scan=True"
            )

            return True

        else:

            return False

    # error_callback=True:
    # check Skip Scan and Error/Corrected
    error_corrected = asset.get(
        "Error/Corrected"
    )

    error_corrected_str = (
        str(error_corrected).strip()
        if (
            error_corrected is not None
            and not pd.isna(error_corrected)
        )
        else ""
    )

    error_corrected_is_empty = (
        error_corrected_str == ""
    )

    error_corrected_is_error = (
        error_corrected_str.lower()
        == "error"
    )

    error_corrected_is_corrected = (
        error_corrected_str.lower()
        == "corrected"
    )

    # Rule 1
    if (
        skip_scan_is_true
        and error_corrected_is_error
    ):

        logging.info(
            "Rule 1: Skip Scan=True "
            "AND Error/Corrected=Error"
        )

        return True

    # Rule 2
    if (
        skip_scan_is_true
        and error_corrected_is_empty
    ):

        logging.info(
            "Rule 2: Skip Scan=True "
            "AND Error/Corrected=empty"
        )

        return True

    # Rule 3
    if (
        skip_scan_is_true
        and error_corrected_is_corrected
    ):

        logging.info(
            "Rule 3: Skip Scan=True "
            "AND Error/Corrected=Corrected"
        )

        return True

    # Rule 4
    if (
        skip_scan_is_empty
        and error_corrected_is_error
    ):

        logging.info(
            "Rule 4: Skip Scan=empty "
            "AND Error/Corrected=Error"
        )

        return True

    # Rule 5
    if (
        skip_scan_is_empty
        and error_corrected_is_corrected
    ):

        logging.info(
            "Rule 5: Skip Scan=empty "
            "AND Error/Corrected=Corrected - INCLUDE"
        )

        return False

    # Default: include IP
    return False