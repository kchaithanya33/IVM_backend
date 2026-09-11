import base64
import binascii
import io
import logging
import re

import pandas as pd


def extract_date_only(date_value):
    """
    Extract date portion only from various date formats.

    Returns:
        str: Date in YYYY-MM-DD format.
        None: If parsing fails or value is empty.
    """
    if pd.isna(date_value):
        return None

    try:
        if isinstance(date_value, pd.Timestamp):
            return date_value.strftime("%Y-%m-%d")

        elif isinstance(date_value, str):
            from datetime import datetime

            date_str = date_value.strip()

            formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%m/%d/%Y %H:%M",
                "%d/%m/%Y %H:%M",
                "%Y/%m/%d",
                "%d-%m-%Y",
                "%m-%d-%Y",
            ]

            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        return None

    except Exception as e:
        logging.warning(
            f"Error parsing date value '{date_value}': {str(e)}"
        )
        return None


def get_vulnerability_status_mapping():
    """
    Return mapping of vulnerability statuses.

    True  = fixed/resolved
    False = open/active
    """
    return {
        "fixed": True,
        "closed": True,
        "resolved": True,
        "mitigated": True,
        "remediated": True,
        "patched": True,
        "completed": True,
        "open": False,
        "active": False,
        "new": False,
        "pending": False,
        "in_progress": False,
        "assigned": False,
    }


def validate_required_columns(vuln_df, dfn_df):
    """
    Validate required columns in vulnerability and DFN reports.

    Returns:
        tuple:
            errors
            detected_columns
    """
    errors = []

    vuln_import_id_col = find_column_by_patterns(
        vuln_df,
        ["Import ID", "ImportID", "ID"]
    )

    vuln_status_col = find_column_by_patterns(
        vuln_df,
        [
            "Vuln Scan",
            "Status",
            "Vuln Status",
            "Scan Status",
        ]
    )

    dfn_import_id_col = find_column_by_patterns(
        dfn_df,
        ["Import ID", "ImportID", "ID"]
    )

    dfn_ivm_status_col = find_column_by_patterns(
        dfn_df,
        [
            "Status (IVM)",
            "Status(IVM)",
            "IVM Status",
        ]
    )

    if not vuln_import_id_col:
        errors.append(
            "Missing Import ID column in vulnerability report"
        )

    if not vuln_status_col:
        errors.append(
            "Missing Vuln Scan/Status column in vulnerability report"
        )

    if not dfn_import_id_col:
        errors.append(
            "Missing Import ID column in DFN report"
        )

    if not dfn_ivm_status_col:
        errors.append(
            "Missing Status (IVM) column in DFN report"
        )

    return errors, {
        "vuln_import_id_col": vuln_import_id_col,
        "vuln_status_col": vuln_status_col,
        "dfn_import_id_col": dfn_import_id_col,
        "dfn_ivm_status_col": dfn_ivm_status_col,
    }


def decode_file_content(base64_content):
    """
    Decode Base64 encoded file content.

    Supports:
    - normal Base64
    - padded Base64
    - URL-safe Base64
    - data URLs
    - bytes input
    """
    if not base64_content:
        raise ValueError("File content is empty")

    if isinstance(base64_content, bytes):
        return base64_content

    if not isinstance(base64_content, str):
        raise ValueError(
            "File content must be a Base64 string or bytes"
        )

    content = base64_content.strip()

    # Handle data URL:
    # data:application/vnd.openxmlformats-officedocument...
    if content.startswith("data:"):
        if "," not in content:
            raise ValueError("Invalid data URL")

        content = content.split(",", 1)[1]

    # Remove whitespace/newlines
    content = re.sub(r"\s+", "", content)

    # Try standard Base64
    try:
        padding = len(content) % 4

        if padding:
            content += "=" * (4 - padding)

        return base64.b64decode(
            content,
            validate=False
        )

    except (binascii.Error, ValueError):
        pass

    # Try URL-safe Base64
    try:
        padding = len(content) % 4

        if padding:
            content += "=" * (4 - padding)

        return base64.urlsafe_b64decode(content)

    except Exception as e:
        raise ValueError(
            f"Unable to decode Base64 file content: {str(e)}"
        )


def read_excel_from_base64(base64_content, report_type):
    """
    Read Excel file from Base64 content.

    Multiple Excel-reading strategies are attempted because
    incoming reports may have different Excel formats/layouts.
    """
    try:
        file_bytes = decode_file_content(base64_content)

        strategies = [
            {
                "engine": "openpyxl",
                "sheet_name": 0,
            },
            {
                "engine": "xlrd",
                "sheet_name": 0,
            },
            {
                "engine": "openpyxl",
                "sheet_name": 0,
                "header": 0,
            },
            {
                "engine": "openpyxl",
                "sheet_name": 0,
                "header": 1,
            },
        ]

        for index, strategy in enumerate(strategies):
            try:
                df = pd.read_excel(
                    io.BytesIO(file_bytes),
                    **strategy
                )

                if not df.empty:
                    logging.info(
                        f"Successfully read {report_type} "
                        f"with strategy {index + 1}"
                    )

                    return df

            except Exception as e:
                logging.warning(
                    f"Strategy {index + 1} failed for "
                    f"{report_type}: {str(e)}"
                )
                continue

        raise Exception(
            f"Unable to read {report_type} with any strategy"
        )

    except Exception as e:
        logging.error(
            f"Error reading {report_type}: {str(e)}"
        )
        raise


def normalize_column_names(df):
    """
    Normalize DataFrame column names.

    Removes:
    - leading/trailing spaces
    - newline characters
    - carriage returns
    """
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace("\n", " ", regex=False)
        .str.replace("\r", " ", regex=False)
    )

    return df


def find_column_by_patterns(df, patterns):
    """
    Find a DataFrame column using a list of possible column names.

    Matching is case-insensitive and whitespace-insensitive.
    """
    if df is None or df.empty:
        return None

    normalized_columns = {
        re.sub(r"\s+", " ", str(column).strip()).lower(): column
        for column in df.columns
    }

    # First try exact normalized match
    for pattern in patterns:
        normalized_pattern = re.sub(
            r"\s+",
            " ",
            str(pattern).strip()
        ).lower()

        if normalized_pattern in normalized_columns:
            return normalized_columns[normalized_pattern]

    # Then try partial matching
    for pattern in patterns:
        normalized_pattern = re.sub(
            r"\s+",
            " ",
            str(pattern).strip()
        ).lower()

        for normalized_column, original_column in normalized_columns.items():
            if normalized_pattern in normalized_column:
                return original_column

    return None


def validate_dataframe(df, dataframe_name="DataFrame"):
    """
    Basic validation for a DataFrame.
    """
    if df is None:
        raise ValueError(
            f"{dataframe_name} is None"
        )

    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            f"{dataframe_name} must be a pandas DataFrame"
        )

    if df.empty:
        logging.warning(
            f"{dataframe_name} is empty"
        )

    return True


def clean_qid_value(qid_value):
    """
    Clean QID values.

    Examples:
        12345.0 -> 12345
        "12345.0" -> "12345"
        " 12345 " -> "12345"
    """
    if qid_value is None:
        return ""

    try:
        if pd.isna(qid_value):
            return ""

        value = str(qid_value).strip()

        if not value:
            return ""

        # Remove Excel-generated decimal suffix
        if re.match(r"^\d+\.0+$", value):
            value = value.split(".")[0]

        return value

    except Exception as e:
        logging.warning(
            f"Invalid QID value '{qid_value}': {str(e)}"
        )
        return ""


def clean_ip_address(ip_address):
    """
    Clean and validate IPv4 addresses.
    """
    if ip_address is None:
        return ""

    try:
        if pd.isna(ip_address):
            return ""

        value = str(ip_address).strip()

        if not value:
            return ""

        # Handle Excel-style values such as 10.10.10.10.0
        parts = value.split(".")

        if len(parts) == 5 and parts[-1] == "0":
            value = ".".join(parts[:4])

        parts = value.split(".")

        if len(parts) != 4:
            return value

        if all(
            part.isdigit() and 0 <= int(part) <= 255
            for part in parts
        ):
            return value

        return value

    except Exception as e:
        logging.warning(
            f"Invalid IP address '{ip_address}': {str(e)}"
        )
        return ""


def normalize_status_value(status):
    """
    Normalize vulnerability status values.
    """
    if status is None:
        return ""

    try:
        if pd.isna(status):
            return ""

        return (
            str(status)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

    except Exception:
        return ""