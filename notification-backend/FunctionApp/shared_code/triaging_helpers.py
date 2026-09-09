import logging
import base64
import os
import tempfile
import traceback
from io import BytesIO

import pandas as pd


# ============================================================
# Constants
# ============================================================

# Columns that must exist and contain values
REQUIRED_COLUMNS_WITH_VALUES = [
    "IP",
    "QID",
    "Severity",
    "Scope Identification",
]


# All expected columns
EXPECTED_COLUMNS = [
    "IP",
    "Server",
    "QID",
    "Title",
    "Severity",
    "Scope Identification",
]


# Column mapping for validation
COLUMN_MAPPING = {
    "IP Address": "IP",
    "Server Name": "Server",
    "QID": "QID",
    "Vulnerability Title": "Title",
    "Severity": "Severity",
    "Scope Identification": "Scope Identification",
}


# ============================================================
# Excel Sheet Detection
# ============================================================

def find_best_excel_sheet(excel_filename):
    """
    Intelligently find the best Excel sheet for triaging validation.

    Priority:
        1. Vulnerability Report
        2. Other known vulnerability/triage sheets
        3. Score all sheets based on expected columns
        4. First non-empty sheet as final fallback

    Args:
        excel_filename: Path to Excel file

    Returns:
        Tuple of (sheet_name, DataFrame)
    """

    logging.info(
        "Finding best sheet for triaging data in Excel file"
    )

    try:
        # ----------------------------------------------------
        # Get all sheet names
        # ----------------------------------------------------

        xls = pd.ExcelFile(excel_filename)
        sheet_names = xls.sheet_names

        logging.info(
            f"Found {len(sheet_names)} sheets: "
            f"{', '.join(sheet_names)}"
        )

        # ----------------------------------------------------
        # First priority:
        # Vulnerability Report
        # ----------------------------------------------------

        if "Vulnerability Report" in sheet_names:

            try:
                df = pd.read_excel(
                    excel_filename,
                    sheet_name="Vulnerability Report"
                )

                if len(df) > 0:

                    logging.info(
                        "Found 'Vulnerability Report' sheet "
                        f"with {len(df)} rows - using it directly"
                    )

                    return "Vulnerability Report", df

            except Exception as e:

                logging.warning(
                    "Error reading 'Vulnerability Report' sheet: "
                    f"{str(e)}"
                )

        # ----------------------------------------------------
        # Priority sheet names
        # ----------------------------------------------------

        priority_sheets = [
            "VulnerabilityData",
            "Vulnerability Report",
            "Triage",
            "Vulnerabilities",
            "Data",
        ]

        # ----------------------------------------------------
        # Key columns used for scoring
        # ----------------------------------------------------

        key_columns = [
            "IP Address",
            "Server Name",
            "QID",
            "Vulnerability Title",
            "Severity",
        ]

        # ----------------------------------------------------
        # Sheets to skip
        # ----------------------------------------------------

        skip_sheets = [
            "Summary",
            "Dashboard",
            "Instructions",
            "README",
            "Cover",
            "Contents",
            "Index",
        ]

        # ----------------------------------------------------
        # Best sheet tracking
        # ----------------------------------------------------

        best_sheet = None
        best_score = -1
        best_df = None
        best_row_count = 0

        # ----------------------------------------------------
        # Look for priority sheet names
        # ----------------------------------------------------

        for priority in priority_sheets:

            for sheet in sheet_names:

                if priority.lower() in sheet.lower():

                    try:

                        df = pd.read_excel(
                            excel_filename,
                            sheet_name=sheet
                        )

                        if len(df) > 0:

                            logging.info(
                                f"Found priority sheet match: "
                                f"'{sheet}' with {len(df)} rows"
                            )

                            return sheet, df

                    except Exception as e:

                        logging.warning(
                            f"Error reading priority sheet "
                            f"'{sheet}': {str(e)}"
                        )

        # ----------------------------------------------------
        # Analyze all sheets
        # ----------------------------------------------------

        for sheet in sheet_names:

            # Skip summary-type sheets
            if any(
                skip.lower() in sheet.lower()
                for skip in skip_sheets
            ):

                logging.info(
                    f"Skipping likely summary sheet: '{sheet}'"
                )

                continue

            try:

                df = pd.read_excel(
                    excel_filename,
                    sheet_name=sheet
                )

                # Skip empty or almost-empty sheets
                if len(df) < 2:

                    logging.info(
                        f"Skipping nearly empty sheet: "
                        f"'{sheet}' with {len(df)} rows"
                    )

                    continue

                score = 0

                # ------------------------------------------------
                # Score key columns
                # ------------------------------------------------

                for col in key_columns:

                    for actual_col in df.columns:

                        if col.lower() in str(actual_col).lower():

                            score += 1

                            # Exact match gets extra score
                            if (
                                col.lower()
                                == str(actual_col).lower()
                            ):
                                score += 0.5

                # ------------------------------------------------
                # Check triage status
                # ------------------------------------------------

                has_triage_status = any(
                    "triage" in str(col).lower()
                    and "status" in str(col).lower()
                    for col in df.columns
                )

                if has_triage_status:
                    score += 3

                # ------------------------------------------------
                # Check severity data
                # ------------------------------------------------

                for col in df.columns:

                    if "severity" in str(col).lower():

                        severity_values = (
                            df[col]
                            .astype(str)
                            .str.strip()
                            .str.lower()
                            .dropna()
                            .unique()
                        )

                        valid_severity_values = [
                            "critical",
                            "high",
                            "medium",
                            "low",
                            "1",
                            "2",
                            "3",
                            "4",
                            "5",
                        ]

                        if any(
                            value in valid_severity_values
                            for value in severity_values
                        ):

                            score += 3
                            break

                logging.info(
                    f"Sheet '{sheet}' scored {score} "
                    f"for triaging data "
                    f"(rows: {len(df)})"
                )

                # ------------------------------------------------
                # Select best sheet
                # ------------------------------------------------

                if (
                    score > best_score
                    or (
                        score == best_score
                        and len(df) > best_row_count
                    )
                ):

                    best_score = score
                    best_sheet = sheet
                    best_df = df
                    best_row_count = len(df)

            except Exception as e:

                logging.warning(
                    f"Error analyzing sheet '{sheet}': {str(e)}"
                )

        # ----------------------------------------------------
        # Return best match
        # ----------------------------------------------------

        if best_sheet and best_df is not None:

            logging.info(
                f"Selected sheet '{best_sheet}' "
                f"with score {best_score} "
                f"and {best_row_count} rows"
            )

            return best_sheet, best_df

        # ----------------------------------------------------
        # Final fallback:
        # first non-empty sheet
        # ----------------------------------------------------

        for sheet in sheet_names:

            try:

                df = pd.read_excel(
                    excel_filename,
                    sheet_name=sheet
                )

                if len(df) > 0:

                    logging.info(
                        f"Using fallback sheet '{sheet}' "
                        f"with {len(df)} rows"
                    )

                    return sheet, df

            except Exception:
                pass

        # ----------------------------------------------------
        # Nothing usable found
        # ----------------------------------------------------

        logging.error(
            "No usable sheet found in Excel file"
        )

        raise ValueError(
            "No usable data sheet found in the Excel file"
        )

    except Exception as e:

        logging.error(
            f"Error finding best Excel sheet: {str(e)}"
        )

        raise


# ============================================================
# Legacy Mismatch Validation
# ============================================================

def check_legacy_mismatches(df):
    """
    Check for Legacy/Non-Legacy and Vulnerability Class mismatches.

    Returns:
        Tuple:
            (
                has_mismatches,
                mismatch_count,
                mismatch_details
            )
    """

    try:

        # ----------------------------------------------------
        # Required columns
        # ----------------------------------------------------

        required_cols = [
            "IP",
            "Server",
            "Legacy/Non-Legacy",
            "Vulnerability Class",
        ]

        # ----------------------------------------------------
        # Check columns
        # ----------------------------------------------------

        missing_cols = [
            col
            for col in required_cols
            if col not in df.columns
        ]

        if missing_cols:

            logging.warning(
                "Cannot check legacy mismatches - "
                f"missing columns: {', '.join(missing_cols)}"
            )

            return (
                False,
                0,
                "Cannot check legacy mismatches - "
                f"missing columns: {', '.join(missing_cols)}",
            )

        # ----------------------------------------------------
        # Deduplicate
        # ----------------------------------------------------

        analysis_df = (
            df[required_cols]
            .drop_duplicates()
            .copy()
        )

        # ----------------------------------------------------
        # Normalize values
        # ----------------------------------------------------

        analysis_df["Legacy_clean"] = (
            analysis_df["Legacy/Non-Legacy"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        analysis_df["VulnClass_clean"] = (
            analysis_df["Vulnerability Class"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # ----------------------------------------------------
        # Mismatch conditions
        # ----------------------------------------------------

        cond1 = (
            (analysis_df["Legacy_clean"] == "legacy")
            &
            (
                analysis_df["VulnClass_clean"]
                == "non legacy"
            )
        )

        cond2 = (
            (
                analysis_df["Legacy_clean"]
                == "non legacy"
            )
            &
            (
                analysis_df["VulnClass_clean"]
                == "legacy"
            )
        )

        mismatch1_count = cond1.sum()
        mismatch2_count = cond2.sum()

        total_mismatches = (
            mismatch1_count
            + mismatch2_count
        )

        # ----------------------------------------------------
        # Return mismatch information
        # ----------------------------------------------------

        if total_mismatches > 0:

            details = (
                f"Found {total_mismatches} "
                "legacy classification mismatches: "
            )

            details += (
                f"{mismatch1_count} "
                "Legacy→Non-Legacy conflicts, "
            )

            details += (
                f"{mismatch2_count} "
                "Non-Legacy→Legacy conflicts"
            )

            return (
                True,
                total_mismatches,
                details,
            )

        return (
            False,
            0,
            "No legacy classification mismatches found",
        )

    except Exception as e:

        error_msg = (
            f"Error checking legacy mismatches: {str(e)}"
        )

        logging.error(error_msg)

        return (
            False,
            0,
            error_msg,
        )


# ============================================================
# Generate Legacy Mismatch Excel
# ============================================================

def generate_legacy_mismatch_excel(df):
    """
    Generate an Excel file containing Legacy classification
    mismatches.

    Returns:
        Base64-encoded Excel file content,
        or None if no mismatches exist.
    """

    try:

        # ----------------------------------------------------
        # Output columns
        # ----------------------------------------------------

        output_columns = [
            "IP",
            "Server",
            "Legacy/Non-Legacy",
            "Vulnerability Class",
        ]

        # ----------------------------------------------------
        # Validate columns
        # ----------------------------------------------------

        missing_columns = [
            col
            for col in output_columns
            if col not in df.columns
        ]

        if missing_columns:

            logging.warning(
                "Missing required columns for Excel export: "
                f"{', '.join(missing_columns)}"
            )

            return None

        # ----------------------------------------------------
        # Deduplicate
        # ----------------------------------------------------

        analysis_df = (
            df[output_columns]
            .drop_duplicates()
            .copy()
        )

        # ----------------------------------------------------
        # Normalize values
        # ----------------------------------------------------

        analysis_df["Legacy_clean"] = (
            analysis_df["Legacy/Non-Legacy"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        analysis_df["VulnClass_clean"] = (
            analysis_df["Vulnerability Class"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # ----------------------------------------------------
        # Mismatch conditions
        # ----------------------------------------------------

        cond1 = (
            (analysis_df["Legacy_clean"] == "legacy")
            &
            (
                analysis_df["VulnClass_clean"]
                == "non legacy"
            )
        )

        cond2 = (
            (
                analysis_df["Legacy_clean"]
                == "non legacy"
            )
            &
            (
                analysis_df["VulnClass_clean"]
                == "legacy"
            )
        )

        # ----------------------------------------------------
        # Build mismatch tables
        # ----------------------------------------------------

        table1_data = (
            analysis_df[cond1][output_columns]
            .reset_index(drop=True)
        )

        table2_data = (
            analysis_df[cond2][output_columns]
            .reset_index(drop=True)
        )

        # ----------------------------------------------------
        # No mismatches
        # ----------------------------------------------------

        if (
            table1_data.empty
            and table2_data.empty
        ):

            logging.info(
                "No legacy mismatches found - "
                "skipping Excel generation"
            )

            return None

        # ----------------------------------------------------
        # Create Excel in memory
        # ----------------------------------------------------

        excel_buffer = BytesIO()

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl"
        ) as writer:

            # ------------------------------------------------
            # Legacy → Non-Legacy
            # ------------------------------------------------

            if not table1_data.empty:

                table1_data.to_excel(
                    writer,
                    sheet_name="Legacy to Non-Legacy",
                    index=False,
                )

            else:

                pd.DataFrame(
                    columns=output_columns
                ).to_excel(
                    writer,
                    sheet_name="Legacy to Non-Legacy",
                    index=False,
                )

            # ------------------------------------------------
            # Non-Legacy → Legacy
            # ------------------------------------------------

            if not table2_data.empty:

                table2_data.to_excel(
                    writer,
                    sheet_name="Non-Legacy to Legacy",
                    index=False,
                )

            else:

                pd.DataFrame(
                    columns=output_columns
                ).to_excel(
                    writer,
                    sheet_name="Non-Legacy to Legacy",
                    index=False,
                )

            # ------------------------------------------------
            # Summary
            # ------------------------------------------------

            summary_data = {
                "Mismatch Type": [
                    "Legacy → Non-Legacy Conflicts",
                    "Non-Legacy → Legacy Conflicts",
                    "Total Mismatches",
                ],
                "Count": [
                    len(table1_data),
                    len(table2_data),
                    len(table1_data)
                    + len(table2_data),
                ],
            }

            summary_df = pd.DataFrame(
                summary_data
            )

            summary_df.to_excel(
                writer,
                sheet_name="Summary",
                index=False,
            )

        # ----------------------------------------------------
        # Encode as Base64
        # ----------------------------------------------------

        excel_buffer.seek(0)

        excel_base64 = base64.b64encode(
            excel_buffer.read()
        ).decode("utf-8")

        logging.info(
            "Generated Excel file with "
            f"{len(table1_data)} "
            "Legacy→Non-Legacy and "
            f"{len(table2_data)} "
            "Non-Legacy→Legacy mismatches"
        )

        return excel_base64

    except Exception as e:

        logging.error(
            "Error generating mismatch Excel file: "
            f"{str(e)}"
        )

        logging.error(
            traceback.format_exc()
        )

        return None


# ============================================================
# Generate Legacy Mismatch HTML Tables
# ============================================================

def generate_legacy_mismatch_tables(df):
    """
    Generate HTML tables for Legacy/Non-Legacy and
    Vulnerability Class mismatches.

    The generated HTML is designed for email clients.
    """

    try:

        # ----------------------------------------------------
        # Output columns
        # ----------------------------------------------------

        output_columns = [
            "IP",
            "Server",
            "Legacy/Non-Legacy",
            "Vulnerability Class",
        ]

        # ----------------------------------------------------
        # Validate columns
        # ----------------------------------------------------

        missing_columns = [
            col
            for col in output_columns
            if col not in df.columns
        ]

        if missing_columns:

            error_msg = (
                "Missing required columns: "
                f"{', '.join(missing_columns)}"
            )

            return (
                f"<p>{error_msg}</p>",
                f"<p>{error_msg}</p>",
            )

        # ----------------------------------------------------
        # Deduplicate
        # ----------------------------------------------------

        analysis_df = (
            df[output_columns]
            .drop_duplicates()
            .copy()
        )

        # ----------------------------------------------------
        # Normalize
        # ----------------------------------------------------

        analysis_df["Legacy_clean"] = (
            analysis_df["Legacy/Non-Legacy"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        analysis_df["VulnClass_clean"] = (
            analysis_df["Vulnerability Class"]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        # ----------------------------------------------------
        # Mismatch conditions
        # ----------------------------------------------------

        cond1 = (
            (analysis_df["Legacy_clean"] == "legacy")
            &
            (
                analysis_df["VulnClass_clean"]
                == "non legacy"
            )
        )

        cond2 = (
            (
                analysis_df["Legacy_clean"]
                == "non legacy"
            )
            &
            (
                analysis_df["VulnClass_clean"]
                == "legacy"
            )
        )

        table1_data = (
            analysis_df[cond1][output_columns]
        )

        table2_data = (
            analysis_df[cond2][output_columns]
        )

        # ====================================================
        # HTML table builder
        # ====================================================

        def create_html_table(data, columns):

            if data.empty:
                return None

            parts = []

            # ------------------------------------------------
            # Outer table
            # ------------------------------------------------

            parts.append(
                '<table align="center" '
                'cellpadding="0" cellspacing="0" border="0" '
                'style="width:100%;max-width:600px;'
                'border-collapse:collapse;'
                'font-family:Arial,sans-serif;'
                'margin:15px auto;'
                'line-height:1.2;'
                'mso-line-height-rule:exactly;'
                'table-layout:fixed;'
                'word-wrap:break-word;">'
            )

            parts.append("<tr><td>")

            # ------------------------------------------------
            # Inner table
            # ------------------------------------------------

            parts.append(
                '<table width="100%" '
                'cellpadding="0" cellspacing="0" border="1" '
                'style="border-collapse:collapse;'
                'margin:0;padding:0;'
                'line-height:1.2;'
                'mso-line-height-rule:exactly;'
                'table-layout:fixed;'
                'word-wrap:break-word;">'
            )

            # ------------------------------------------------
            # Header
            # ------------------------------------------------

            parts.append(
                '<thead>'
                '<tr style="background-color:#e0e0e0;'
                'height:50px;">'
            )

            for col in columns:

                parts.append(
                    '<th style="'
                    'padding:8px;'
                    'text-align:center;'
                    'vertical-align:middle;'
                    'font-weight:bold;'
                    'font-size:13px;'
                    'line-height:1.2;'
                    'mso-line-height-rule:exactly;'
                    'word-break:break-word;'
                    'white-space:normal;">'
                    f"{col}"
                    "</th>"
                )

            parts.append(
                "</tr>"
                "</thead>"
                "<tbody>"
            )

            # ------------------------------------------------
            # Rows
            # ------------------------------------------------

            for i, (_, row) in enumerate(
                data.iterrows()
            ):

                bg = (
                    "#ffffff"
                    if i % 2 == 0
                    else "#f9f9f9"
                )

                parts.append(
                    f'<tr style="'
                    f'background-color:{bg};'
                    'height:40px;">'
                )

                for col in columns:

                    val = (
                        row[col]
                        if pd.notna(row[col])
                        else ""
                    )

                    # Server column width
                    style_extra = ""

                    if col == "Server":

                        style_extra = (
                            "max-width:120px;"
                            "overflow-wrap:break-word;"
                        )

                    parts.append(
                        '<td style="'
                        'padding:8px;'
                        'text-align:center;'
                        'vertical-align:middle;'
                        'font-size:13px;'
                        'line-height:1.2;'
                        'mso-line-height-rule:exactly;'
                        'word-break:break-word;'
                        'white-space:normal;'
                        f'{style_extra}">'
                        f"{val}"
                        "</td>"
                    )

                parts.append("</tr>")

            # ------------------------------------------------
            # Close tables
            # ------------------------------------------------

            parts.append(
                "</tbody>"
                "</table>"
                "</td></tr>"
                "</table>"
            )

            return "".join(parts)

        # ====================================================
        # Build both tables
        # ====================================================

        table1_html = (
            create_html_table(
                table1_data,
                output_columns,
            )
            or
            (
                "<div style='text-align:center;"
                "font-family:Arial;"
                "font-size:13px;'>"
                "No mismatches found "
                "(Legacy → Non Legacy)"
                "</div>"
            )
        )

        table2_html = (
            create_html_table(
                table2_data,
                output_columns,
            )
            or
            (
                "<div style='text-align:center;"
                "font-family:Arial;"
                "font-size:13px;'>"
                "No mismatches found "
                "(Non Legacy → Legacy)"
                "</div>"
            )
        )

        return (
            table1_html,
            table2_html,
        )

    except Exception as e:

        error_msg = (
            f"Error generating mismatch tables: {str(e)}"
        )

        logging.error(error_msg)

        return (
            (
                "<div style='text-align:center;"
                "font-family:Arial;"
                "font-size:13px;'>"
                f"{error_msg}"
                "</div>"
            ),
            (
                "<div style='text-align:center;"
                "font-family:Arial;"
                "font-size:13px;'>"
                f"{error_msg}"
                "</div>"
            ),
        )


# ============================================================
# Main Excel Validation
# ============================================================

def validate_excel_file(excel_io, cycle_id):
    """
    Validate Excel file for required columns and data.

    Args:
        excel_io:
            BytesIO object containing Excel file

        cycle_id:
            Cycle ID for reference

    Returns:
        Tuple:

            (
                validation_issues,
                mismatch_tables,
                mismatch_excel
            )

        mismatch_tables:
            Tuple containing two HTML strings

        mismatch_excel:
            Base64 encoded Excel file or None
    """

    validation_issues = []

    temp_file = None

    mismatch_tables = (
        "",
        "",
    )

    mismatch_excel = None

    try:

        # ====================================================
        # Save Excel content to temporary file
        # ====================================================

        try:

            with tempfile.NamedTemporaryFile(
                suffix=".xlsx",
                delete=False,
            ) as temp:

                if isinstance(excel_io, BytesIO):

                    temp.write(
                        excel_io.getvalue()
                    )

                else:

                    temp.write(
                        excel_io.read()
                    )

                temp_file = temp.name

            # ------------------------------------------------
            # Find best sheet
            # ------------------------------------------------

            sheet_name, df = find_best_excel_sheet(
                temp_file
            )

            logging.info(
                f"Using sheet '{sheet_name}' "
                "for triaging validation"
            )

        except Exception as e:

            logging.error(
                f"Failed to read Excel file: {str(e)}"
            )

            validation_issues.append(
                f"Failed to read Excel file: {str(e)}"
            )

            return (
                validation_issues,
                mismatch_tables,
                mismatch_excel,
            )

        # ====================================================
        # Check empty DataFrame
        # ====================================================

        if df.empty:

            validation_issues.append(
                "Excel file contains no data"
            )

            return (
                validation_issues,
                mismatch_tables,
                mismatch_excel,
            )

        # ====================================================
        # Generate mismatch HTML tables
        # ====================================================

        try:

            mismatch_tables = (
                generate_legacy_mismatch_tables(df)
            )

        except Exception as e:

            logging.warning(
                "Could not generate mismatch tables: "
                f"{str(e)}"
            )

            mismatch_tables = (
                f"<p>Error generating mismatch tables: "
                f"{str(e)}</p>",
                f"<p>Error generating mismatch tables: "
                f"{str(e)}</p>",
            )

        # ====================================================
        # Generate mismatch Excel
        # ====================================================

        try:

            mismatch_excel = (
                generate_legacy_mismatch_excel(df)
            )

            if mismatch_excel:

                logging.info(
                    "Successfully generated "
                    "mismatch Excel file"
                )

        except Exception as e:

            logging.warning(
                "Could not generate mismatch Excel file: "
                f"{str(e)}"
            )

        # ====================================================
        # Required columns and values
        # ====================================================

        missing_required_values = []

        for col in REQUIRED_COLUMNS_WITH_VALUES:

            # ------------------------------------------------
            # Column doesn't exist
            # ------------------------------------------------

            if col not in df.columns:

                missing_required_values.append(
                    f"Column '{col}' not found"
                )

                continue

            # =================================================
            # Scope Identification
            # =================================================

            if col == "Scope Identification":

                cleaned_values = (
                    df[col]
                    .astype(str)
                    .str.strip()
                )

                truly_missing = (
                    (cleaned_values == "")
                    |
                    (
                        cleaned_values
                        .str.lower()
                        == "nan"
                    )
                    |
                    (
                        cleaned_values
                        .str.lower()
                        == "none"
                    )
                    |
                    (
                        cleaned_values
                        .str.lower()
                        == "null"
                    )
                    |
                    df[col].isna()
                )

                total_missing = truly_missing.sum()

                # ------------------------------------------------
                # All values missing
                # ------------------------------------------------

                if total_missing == len(df):

                    missing_required_values.append(
                        f"Column '{col}' has no values "
                        "(all empty)"
                    )

                # ------------------------------------------------
                # Some values missing
                # ------------------------------------------------

                elif total_missing > 0:

                    rows_with_missing = (
                        df[truly_missing]
                        .index
                        .tolist()
                    )

                    # Excel row number starts at 2
                    rows_display = [
                        str(i + 2)
                        for i in rows_with_missing[:5]
                    ]

                    if len(rows_with_missing) > 5:

                        rows_display.append(
                            f"... and "
                            f"{len(rows_with_missing) - 5} "
                            "more"
                        )

                    missing_required_values.append(
                        f"Column '{col}' has "
                        f"{total_missing} missing values "
                        "in rows: "
                        f"{', '.join(rows_display)}"
                    )

                    logging.info(
                        "Scope Identification missing "
                        f"values details: Found "
                        f"{total_missing} truly missing values"
                    )

                    sample_missing = (
                        cleaned_values[
                            truly_missing
                        ]
                        .head(5)
                        .tolist()
                    )

                    logging.info(
                        "Sample missing Scope Identification "
                        f"values: {sample_missing}"
                    )

            # =================================================
            # IP
            # =================================================

            elif col == "IP":

                # Use robust missing detection
                cleaned_ip = (
                    df[col]
                    .astype(str)
                    .str.strip()
                )

                missing_mask = (
                    df[col].isna()
                    |
                    (cleaned_ip == "")
                    |
                    (
                        cleaned_ip.str.lower()
                        .isin(
                            [
                                "nan",
                                "none",
                                "null",
                            ]
                        )
                    )
                )

                total_missing = missing_mask.sum()

                if total_missing == len(df):

                    missing_required_values.append(
                        f"Column '{col}' has no values "
                        "(all empty)"
                    )

                elif total_missing > 0:

                    missing_required_values.append(
                        f"Column '{col}' has "
                        f"{total_missing} missing values"
                    )

            # =================================================
            # Other required columns
            # =================================================

            else:

                cleaned_values = (
                    df[col]
                    .astype(str)
                    .str.strip()
                )

                missing_mask = (
                    df[col].isna()
                    |
                    (cleaned_values == "")
                    |
                    (
                        cleaned_values.str.lower()
                        .isin(
                            [
                                "nan",
                                "none",
                                "null",
                            ]
                        )
                    )
                )

                total_missing = missing_mask.sum()

                # ------------------------------------------------
                # All empty
                # ------------------------------------------------

                if total_missing == len(df):

                    missing_required_values.append(
                        f"Column '{col}' has no values "
                        "(all empty)"
                    )

                # ------------------------------------------------
                # Some missing
                # ------------------------------------------------

                elif total_missing > 0:

                    rows_with_missing = (
                        df[missing_mask]
                        .index
                        .tolist()
                    )

                    rows_display = [
                        str(i + 2)
                        for i in rows_with_missing[:5]
                    ]

                    if len(rows_with_missing) > 5:

                        rows_display.append(
                            f"... and "
                            f"{len(rows_with_missing) - 5} "
                            "more"
                        )

                    missing_required_values.append(
                        f"Column '{col}' has "
                        f"{total_missing} missing values "
                        "in rows: "
                        f"{', '.join(rows_display)}"
                    )

        # ----------------------------------------------------
        # Add required-value issues
        # ----------------------------------------------------

        if missing_required_values:

            validation_issues.extend(
                missing_required_values
            )

        # ====================================================
        # Empty IP addresses
        # ====================================================

        if "IP" in df.columns:

            cleaned_ip = (
                df["IP"]
                .astype(str)
                .str.strip()
            )

            empty_ips = (
                df["IP"].isna()
                |
                (cleaned_ip == "")
                |
                cleaned_ip.str.lower().isin(
                    [
                        "nan",
                        "none",
                        "null",
                    ]
                )
            )

            empty_ip_count = empty_ips.sum()

            if empty_ip_count > 0:

                validation_issues.append(
                    "Empty IP addresses found: "
                    f"{empty_ip_count} missing values"
                )

        # ====================================================
        # Empty QIDs
        # ====================================================

        if "QID" in df.columns:

            cleaned_qid = (
                df["QID"]
                .astype(str)
                .str.strip()
            )

            empty_qids = (
                df["QID"].isna()
                |
                (cleaned_qid == "")
                |
                cleaned_qid.str.lower().isin(
                    [
                        "nan",
                        "none",
                        "null",
                    ]
                )
            )

            empty_qid_indexes = (
                df[empty_qids]
                .index
                .tolist()
            )

            if empty_qid_indexes:

                rows = [
                    str(i + 2)
                    for i in empty_qid_indexes
                ]

                validation_issues.append(
                    "Empty QID in rows: "
                    f"{', '.join(rows)}"
                )

        # ====================================================
        # Empty vulnerability titles
        # ====================================================

        if "Title" in df.columns:

            cleaned_title = (
                df["Title"]
                .astype(str)
                .str.strip()
            )

            empty_titles = (
                df["Title"].isna()
                |
                (cleaned_title == "")
                |
                cleaned_title.str.lower().isin(
                    [
                        "nan",
                        "none",
                        "null",
                    ]
                )
            )

            empty_title_indexes = (
                df[empty_titles]
                .index
                .tolist()
            )

            if empty_title_indexes:

                rows = [
                    str(i + 2)
                    for i in empty_title_indexes
                ]

                validation_issues.append(
                    "Empty vulnerability title "
                    "in rows: "
                    f"{', '.join(rows)}"
                )

        # ====================================================
        # Legacy mismatches
        # ====================================================

        try:

            (
                has_mismatches,
                mismatch_count,
                mismatch_details,
            ) = check_legacy_mismatches(df)

            if has_mismatches:

                validation_issues.append(
                    "Legacy Classification Mismatches: "
                    f"{mismatch_details}"
                )

                logging.warning(
                    "Legacy mismatches detected: "
                    f"{mismatch_details}"
                )

        except Exception as e:

            logging.warning(
                "Could not check legacy mismatches: "
                f"{str(e)}"
            )

        # ====================================================
        # Validation summary
        # ====================================================

        logging.info(
            "Validation completed. "
            f"Found {len(validation_issues)} issues."
        )

        if validation_issues:

            logging.info(
                "Validation issues found:"
            )

            for issue in validation_issues:

                logging.info(
                    f"  - {issue}"
                )

        else:

            logging.info(
                "No validation issues found - "
                "Excel file is valid for processing."
            )

        return (
            validation_issues,
            mismatch_tables,
            mismatch_excel,
        )

    except Exception as e:

        logging.error(
            f"Error validating Excel file: {str(e)}"
        )

        validation_issues.append(
            f"Error validating Excel file: {str(e)}"
        )

        return (
            validation_issues,
            mismatch_tables,
            mismatch_excel,
        )

    finally:

        # ====================================================
        # Delete temporary file
        # ====================================================

        if (
            temp_file
            and os.path.exists(temp_file)
        ):

            try:

                os.unlink(temp_file)

                logging.info(
                    f"Cleaned up temporary file: "
                    f"{temp_file}"
                )

            except Exception as e:

                logging.warning(
                    f"Failed to delete temporary file "
                    f"{temp_file}: {str(e)}"
                )