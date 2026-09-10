import logging
import json
import os
import time
import zipfile

import requests
import pandas as pd
import azure.functions as func

from datetime import datetime, timedelta
from io import StringIO, BytesIO


# ============================================================
# DFN REPORT CLIENT
# ============================================================

class DFNReportClient:
    """
    Client for retrieving DFN reports from Decision Focus APIs
    with automatic token management.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        auth_base_url: str = None,
        api_base_url: str = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret

        # ----------------------------------------------------
        # Base URLs
        # ----------------------------------------------------
        self.auth_base_url = (
            auth_base_url
            or os.environ.get(
                "DFN_AUTH_BASE_URL",
                "https://diageo-dev-auth.decisionfocus.com"
            )
        )

        self.api_base_url = (
            api_base_url
            or os.environ.get(
                "DFN_API_BASE_URL",
                "https://diageo-dev-converter.decisionfocus.com"
            )
        )

        # ----------------------------------------------------
        # Default report configuration
        # ----------------------------------------------------
        self.default_report_id = os.environ.get(
            "DFN_DEFAULT_REPORT_ID",
            "07e93e493ac70e52a4cb0cdf1e0198cf"
        )

        self.default_workspace_id = os.environ.get(
            "DFN_DEFAULT_WORKSPACE_ID",
            "3031fb573e7433ebafbcac6dcc0015be"
        )

        # ----------------------------------------------------
        # Token state
        # ----------------------------------------------------
        self.access_token = None
        self.token_type = None
        self.token_expires_at = None

        # ----------------------------------------------------
        # Last request error
        # ----------------------------------------------------
        self.last_error = None

        logging.info("DFN Client initialized:")
        logging.info(f"  Auth URL: {self.auth_base_url}")
        logging.info(f"  API URL: {self.api_base_url}")
        logging.info(f"  Default Report ID: {self.default_report_id}")
        logging.info(
            f"  Default Workspace ID: {self.default_workspace_id}"
        )

    # ========================================================
    # AUTHENTICATION
    # ========================================================

    def authenticate(self) -> bool:
        """
        Authenticate against DFN OAuth API and obtain access token.
        """

        try:
            token_url = (
                f"{self.auth_base_url}/v1/api/oauth/token"
            )

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            logging.info(
                f"Authenticating at: {token_url}"
            )

            response = requests.post(
                token_url,
                headers=headers,
                data=data,
                timeout=30
            )

            response.raise_for_status()

            token_data = response.json()

            self.access_token = token_data.get(
                "access_token"
            )

            self.token_type = token_data.get(
                "token_type",
                "bearer"
            )

            # ------------------------------------------------
            # Calculate token expiration
            # ------------------------------------------------
            expires_in = token_data.get(
                "expires_in",
                3600
            )

            self.token_expires_at = (
                datetime.now()
                + timedelta(seconds=expires_in - 60)
            )

            logging.info(
                "Authentication successful."
            )

            logging.info(
                f"Token type: {self.token_type}"
            )

            logging.info(
                f"Token expires at: "
                f"{self.token_expires_at}"
            )

            return True

        except requests.exceptions.RequestException as e:

            logging.error(
                f"Authentication failed: {e}"
            )

            if (
                hasattr(e, "response")
                and e.response is not None
            ):
                logging.error(
                    f"Response status: "
                    f"{e.response.status_code}"
                )

                logging.error(
                    f"Response body: "
                    f"{e.response.text}"
                )

            return False

    # ========================================================
    # TOKEN VALIDATION
    # ========================================================

    def is_token_valid(self) -> bool:
        """
        Check whether the current access token is still valid.
        """

        return (
            self.access_token is not None
            and self.token_type is not None
            and self.token_expires_at is not None
            and datetime.now() < self.token_expires_at
        )

    # ========================================================
    # ENSURE AUTHENTICATED
    # ========================================================

    def ensure_authenticated(self) -> bool:
        """
        Ensure that a valid authentication token exists.
        Re-authenticate when required.
        """

        if not self.is_token_valid():

            logging.info(
                "Token expired or invalid. "
                "Re-authenticating..."
            )

            return self.authenticate()

        logging.info(
            "Using existing valid token."
        )

        return True

    # ========================================================
    # GET DFN REPORT
    # ========================================================

    def get_dfn_report(
        self,
        report_id: str = None,
        workspace_id: str = None,
        output_format: str = "csv",
        timeout: int = None,
        max_retries: int = None
    ) -> tuple:
        """
        Retrieve DFN report from the Excel API.

        Returns:
            (data, data_type)

        data_type:
            'text'   -> CSV/text response
            'binary' -> Excel/ZIP/binary response
        """

        if not self.ensure_authenticated():

            logging.error(
                "Failed to authenticate."
            )

            return None, None

        # ----------------------------------------------------
        # Use configured defaults when parameters are missing
        # ----------------------------------------------------
        report_id = (
            report_id
            or self.default_report_id
        )

        workspace_id = (
            workspace_id
            or self.default_workspace_id
        )

        # ----------------------------------------------------
        # Request configuration
        # ----------------------------------------------------
        if timeout is None:

            timeout = int(
                os.environ.get(
                    "DFN_REQUEST_TIMEOUT",
                    "90"
                )
            )

        if max_retries is None:

            max_retries = int(
                os.environ.get(
                    "DFN_MAX_RETRIES",
                    "2"
                )
            )

        last_error = None

        # ----------------------------------------------------
        # Retry loop
        # ----------------------------------------------------
        for attempt in range(max_retries + 1):

            try:

                url = (
                    f"{self.api_base_url}"
                    f"/v1/api/excel/{report_id}"
                )

                headers = {
                    "Authorization":
                        f"{self.token_type.title()} "
                        f"{self.access_token}"
                }

                # ------------------------------------------------
                # Accept header
                # ------------------------------------------------
                if output_format.lower() == "csv":

                    headers["Accept"] = "text/csv"

                elif output_format.lower() in [
                    "excel",
                    "xlsx"
                ]:

                    headers["Accept"] = (
                        "application/"
                        "vnd.openxmlformats-officedocument."
                        "spreadsheetml.sheet"
                    )

                params = {
                    "workspaceId": workspace_id
                }

                logging.info(
                    f"Attempt {attempt + 1}/"
                    f"{max_retries + 1}: "
                    f"Requesting DFN report"
                )

                logging.info(
                    f"URL: {url}"
                )

                # ------------------------------------------------
                # Never log complete token
                # ------------------------------------------------
                token_preview = (
                    self.access_token[:10]
                    if self.access_token
                    else ""
                )

                logging.info(
                    "Using authorization: "
                    f"{self.token_type.title()} "
                    f"{token_preview}..."
                )

                logging.info(
                    "Accept header: "
                    f"{headers.get('Accept', 'Not set')}"
                )

                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=timeout
                )

                response.raise_for_status()

                # ------------------------------------------------
                # Response information
                # ------------------------------------------------
                content_type = (
                    response.headers
                    .get("content-type", "")
                    .lower()
                )

                logging.info(
                    f"Response content-type: "
                    f"{content_type}"
                )

                logging.info(
                    f"Response size: "
                    f"{len(response.content)} bytes"
                )

                # ------------------------------------------------
                # Determine response type
                # ------------------------------------------------
                if (
                    "text/csv" in content_type
                    or headers.get("Accept") == "text/csv"
                ):

                    try:

                        text_content = (
                            response.content
                            .decode("utf-8")
                        )

                        logging.info(
                            "CSV response first "
                            f"200 chars: "
                            f"{text_content[:200]}"
                        )

                        return text_content, "text"

                    except UnicodeDecodeError:

                        # ----------------------------------------
                        # Try alternate encodings
                        # ----------------------------------------
                        for encoding in [
                            "utf-16",
                            "latin-1"
                        ]:

                            try:

                                text_content = (
                                    response.content
                                    .decode(encoding)
                                )

                                logging.info(
                                    f"CSV decoded with "
                                    f"{encoding}"
                                )

                                return (
                                    text_content,
                                    "text"
                                )

                            except UnicodeDecodeError:
                                continue

                        return (
                            response.content,
                            "binary"
                        )

                # ------------------------------------------------
                # Excel / binary
                # ------------------------------------------------
                return response.content, "binary"

            # ====================================================
            # TIMEOUT
            # ====================================================
            except requests.exceptions.Timeout as e:

                last_error = e

                logging.warning(
                    f"Attempt {attempt + 1} "
                    f"timed out after "
                    f"{timeout} seconds: {e}"
                )

                if attempt < max_retries:

                    wait_time = (
                        (attempt + 1) * 15
                    )

                    logging.info(
                        f"Retrying in "
                        f"{wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                    # --------------------------------------------
                    # Re-authenticate if required
                    # --------------------------------------------
                    if not self.is_token_valid():

                        logging.info(
                            "Token may have expired "
                            "during retry. "
                            "Re-authenticating..."
                        )

                        if not self.authenticate():

                            logging.error(
                                "Re-authentication failed."
                            )

                            return None, None

                    continue

                logging.error(
                    f"All {max_retries + 1} "
                    "attempts failed due to timeout."
                )

            # ====================================================
            # REQUEST ERROR
            # ====================================================
            except requests.exceptions.RequestException as e:

                last_error = e

                logging.error(
                    f"Request failed on attempt "
                    f"{attempt + 1}: {e}"
                )

                status_code = None

                if (
                    hasattr(e, "response")
                    and e.response is not None
                ):

                    status_code = (
                        e.response.status_code
                    )

                    logging.error(
                        f"Response status: "
                        f"{status_code}"
                    )

                    logging.error(
                        f"Response body: "
                        f"{e.response.text}"
                    )

                # --------------------------------------------
                # Retry server errors
                # --------------------------------------------
                if (
                    attempt < max_retries
                    and status_code in [
                        502,
                        503,
                        504
                    ]
                ):

                    wait_time = (
                        (attempt + 1) * 10
                    )

                    logging.info(
                        f"Retrying in "
                        f"{wait_time} seconds "
                        "due to server error..."
                    )

                    time.sleep(wait_time)

                    continue

                # --------------------------------------------
                # Don't retry normal 4xx
                # --------------------------------------------
                if (
                    status_code is not None
                    and 400 <= status_code < 500
                    and status_code != 429
                ):

                    logging.error(
                        "Client error - "
                        "not retrying."
                    )

                    break

                if attempt == max_retries:

                    logging.error(
                        f"All {max_retries + 1} "
                        "attempts failed."
                    )

            # ====================================================
            # UNEXPECTED ERROR
            # ====================================================
            except Exception as e:

                last_error = e

                logging.error(
                    f"Unexpected error on "
                    f"attempt {attempt + 1}: {e}"
                )

                if attempt == max_retries:

                    logging.error(
                        f"All {max_retries + 1} "
                        "attempts failed with "
                        "unexpected error."
                    )

                    break

        # --------------------------------------------------------
        # Save last error
        # --------------------------------------------------------
        self.last_error = last_error

        return None, None


# ============================================================
# GLOBAL DFN CLIENT
# ============================================================

_dfn_client = None


def get_dfn_client():
    """
    Get or create the global DFN client.

    The global instance allows the Azure Function worker
    to reuse the authentication token between invocations.
    """

    global _dfn_client

    # --------------------------------------------------------
    # Credentials
    # --------------------------------------------------------
    client_id = os.environ.get(
        "CLIENT_ID"
    )

    client_secret = os.environ.get(
        "CLIENT_SECRET"
    )

    if not client_id or not client_secret:

        logging.error(
            "CLIENT_ID and CLIENT_SECRET "
            "must be configured."
        )

        return None

    # --------------------------------------------------------
    # URLs
    # --------------------------------------------------------
    auth_base_url = os.environ.get(
        "DFN_AUTH_BASE_URL"
    )

    api_base_url = os.environ.get(
        "DFN_API_BASE_URL"
    )

    expected_auth_url = (
        auth_base_url
        or "https://diageo-dev-auth.decisionfocus.com"
    )

    expected_api_url = (
        api_base_url
        or "https://diageo-dev-converter.decisionfocus.com"
    )

    # --------------------------------------------------------
    # Create client if required
    # --------------------------------------------------------
    if (
        _dfn_client is None
        or _dfn_client.client_id != client_id
        or _dfn_client.auth_base_url != expected_auth_url
        or _dfn_client.api_base_url != expected_api_url
    ):

        logging.info(
            "Creating new DFN client instance."
        )

        _dfn_client = DFNReportClient(
            client_id=client_id,
            client_secret=client_secret,
            auth_base_url=auth_base_url,
            api_base_url=api_base_url
        )

    return _dfn_client


# ============================================================
# IMPORT ID
# ============================================================

def fill_missing_import_id(
    df: pd.DataFrame
) -> pd.DataFrame:
    """
    Fill missing Import ID values ONLY.

    Format:
        IP_QID_Port

    If Port is empty:
        IP_QID_

    No other columns or values are intentionally modified.
    """

    def create_import_id(row):

        # ----------------------------------------------------
        # IP Address
        # ----------------------------------------------------
        ip = (
            str(row.get("IP Address", "")).strip()
            if pd.notna(row.get("IP Address"))
            else ""
        )

        # ----------------------------------------------------
        # QID
        # ----------------------------------------------------
        qid = (
            str(row.get("QID", "")).strip()
            if pd.notna(row.get("QID"))
            else ""
        )

        # ----------------------------------------------------
        # Port
        # ----------------------------------------------------
        port = (
            str(row.get("Port", "")).strip()
            if pd.notna(row.get("Port"))
            else ""
        )

        # ----------------------------------------------------
        # Normalize empty port values
        # ----------------------------------------------------
        if port.lower() in [
            "",
            "na",
            "none",
            "null"
        ] or port == "nan":

            port = ""

        return f"{ip}_{qid}_{port}"

    # --------------------------------------------------------
    # Import ID already exists
    # --------------------------------------------------------
    if "Import ID" in df.columns:

        empty_import_id_mask = (
            df["Import ID"].isna()
            |
            (
                df["Import ID"]
                .astype(str)
                .str.strip()
                == ""
            )
            |
            (
                df["Import ID"]
                .astype(str)
                .str.lower()
                == "nan"
            )
        )

        df.loc[
            empty_import_id_mask,
            "Import ID"
        ] = df[
            empty_import_id_mask
        ].apply(
            create_import_id,
            axis=1
        )

        logging.info(
            f"Filled "
            f"{empty_import_id_mask.sum()} "
            "missing Import ID values."
        )

    # --------------------------------------------------------
    # Import ID doesn't exist
    # --------------------------------------------------------
    else:

        df["Import ID"] = df.apply(
            create_import_id,
            axis=1
        )

        logging.info(
            "Created Import ID column "
            "with generated values."
        )

    return df


# ============================================================
# CSV PARSING
# ============================================================

def parse_csv_preserving_structure(
    csv_data: str
) -> pd.DataFrame:
    """
    Parse CSV while preserving the original structure
    and data as much as possible.
    """

    try:

        df = pd.read_csv(
            StringIO(csv_data)
        )

        logging.info(
            f"Successfully parsed CSV "
            f"with shape: {df.shape}"
        )

        return df

    except Exception as e:

        logging.warning(
            f"Standard CSV parsing failed: {e}"
        )

        try:

            df = pd.read_csv(
                StringIO(csv_data),
                on_bad_lines="skip"
            )

            logging.info(
                f"CSV parsed with bad lines "
                f"skipped, shape: {df.shape}"
            )

            return df

        except Exception as e2:

            logging.error(
                f"All CSV parsing attempts "
                f"failed: {e2}"
            )

            raise Exception(
                f"Could not parse CSV data: {e2}"
            )


# ============================================================
# EXCEL RESPONSE HELPER
# ============================================================

def create_excel_http_response(
    df: pd.DataFrame,
    report_id: str
) -> func.HttpResponse:
    """
    Convert DataFrame to Excel and return HTTP response.
    """

    excel_buffer = BytesIO()

    try:

        with pd.ExcelWriter(
            excel_buffer,
            engine="xlsxwriter"
        ) as writer:

            df.to_excel(
                writer,
                sheet_name="Vulnerabilities",
                index=False
            )

            workbook = writer.book
            worksheet = writer.sheets[
                "Vulnerabilities"
            ]

            # ------------------------------------------------
            # Minimal header formatting
            # ------------------------------------------------
            header_format = workbook.add_format(
                {"bold": True}
            )

            for col_num, value in enumerate(
                df.columns.values
            ):

                worksheet.write(
                    0,
                    col_num,
                    value,
                    header_format
                )

    except ImportError:

        logging.warning(
            "xlsxwriter not available. "
            "Falling back to openpyxl."
        )

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl"
        ) as writer:

            df.to_excel(
                writer,
                sheet_name="Vulnerabilities",
                index=False
            )

    excel_buffer.seek(0)

    excel_data = excel_buffer.getvalue()

    return func.HttpResponse(
        excel_data,
        status_code=200,
        mimetype=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                f"attachment; "
                f"filename=vulnerabilities_report_"
                f"{report_id}.xlsx",

            "Content-Type":
                (
                    "application/"
                    "vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                )
        }
    )


# ============================================================
# CSV RESPONSE HELPER
# ============================================================

def create_csv_http_response(
    df: pd.DataFrame,
    report_id: str
) -> func.HttpResponse:
    """
    Convert DataFrame to CSV and return HTTP response.
    """

    csv_buffer = StringIO()

    df.to_csv(
        csv_buffer,
        index=False
    )

    processed_csv = (
        csv_buffer.getvalue()
    )

    return func.HttpResponse(
        processed_csv,
        status_code=200,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                f"attachment; "
                f"filename=vulnerabilities_report_"
                f"{report_id}.csv"
        }
    )


# ============================================================
# EXCEL OUTPUT PROCESSING
# ============================================================

def handle_excel_output_minimal(
    report_data,
    data_type,
    report_id
):
    """
    Handle Excel output with minimal processing.

    ONLY:
        1. Read the DFN data
        2. Fill missing Import ID
        3. Return Excel

    No vulnerability data transformation is performed.
    """

    try:

        # ====================================================
        # BINARY DATA
        # ====================================================

        if data_type == "binary":

            logging.info(
                "Processing binary data "
                "for Excel output."
            )

            # ------------------------------------------------
            # First attempt: direct Excel
            # ------------------------------------------------
            try:

                excel_buffer = BytesIO(
                    report_data
                )

                df = pd.read_excel(
                    excel_buffer,
                    engine="openpyxl"
                )

                logging.info(
                    "Successfully read Excel data. "
                    f"Original shape: {df.shape}"
                )

                # ONLY modification
                df = fill_missing_import_id(df)

                return create_excel_http_response(
                    df,
                    report_id
                )

            except Exception as excel_read_error:

                logging.warning(
                    "Binary data is not valid "
                    f"Excel: {excel_read_error}"
                )

            # ------------------------------------------------
            # Second attempt: ZIP
            # ------------------------------------------------
            if report_data.startswith(b"PK"):

                try:

                    zip_buffer = BytesIO(
                        report_data
                    )

                    with zipfile.ZipFile(
                        zip_buffer,
                        "r"
                    ) as zip_file:

                        file_list = (
                            zip_file.namelist()
                        )

                        logging.info(
                            f"ZIP file contains: "
                            f"{file_list}"
                        )

                        for filename in file_list:

                            # =================================
                            # CSV inside ZIP
                            # =================================
                            if filename.lower().endswith(
                                ".csv"
                            ):

                                extracted_data = (
                                    zip_file.read(
                                        filename
                                    )
                                )

                                try:

                                    csv_text = (
                                        extracted_data
                                        .decode("utf-8")
                                    )

                                except UnicodeDecodeError:

                                    csv_text = (
                                        extracted_data
                                        .decode(
                                            "latin-1"
                                        )
                                    )

                                df = (
                                    parse_csv_preserving_structure(
                                        csv_text
                                    )
                                )

                                df = (
                                    fill_missing_import_id(
                                        df
                                    )
                                )

                                return (
                                    create_excel_http_response(
                                        df,
                                        report_id
                                    )
                                )

                            # =================================
                            # Excel inside ZIP
                            # =================================
                            elif filename.lower().endswith(
                                (".xlsx", ".xls")
                            ):

                                extracted_data = (
                                    zip_file.read(
                                        filename
                                    )
                                )

                                excel_buffer = BytesIO(
                                    extracted_data
                                )

                                df = pd.read_excel(
                                    excel_buffer,
                                    engine="openpyxl"
                                )

                                df = (
                                    fill_missing_import_id(
                                        df
                                    )
                                )

                                return (
                                    create_excel_http_response(
                                        df,
                                        report_id
                                    )
                                )

                except Exception as zip_error:

                    logging.error(
                        "Failed to process ZIP file: "
                        f"{zip_error}"
                    )

                    raise Exception(
                        "Received binary data but "
                        "couldn't process as Excel "
                        "or ZIP"
                    )

            else:

                raise Exception(
                    "Binary data is not Excel "
                    "format and not a ZIP file"
                )

        # ====================================================
        # TEXT / CSV DATA
        # ====================================================

        else:

            logging.info(
                "Processing text data "
                "for Excel output."
            )

            df = (
                parse_csv_preserving_structure(
                    report_data
                )
            )

            # ONLY modification
            df = fill_missing_import_id(df)

            logging.info(
                f"Excel processing complete. "
                f"Final shape: {df.shape}"
            )

            return create_excel_http_response(
                df,
                report_id
            )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        logging.error(
            "Error processing Excel "
            f"with Import ID fill: {e}"
        )

        debug_data = report_data

        if isinstance(
            report_data,
            bytes
        ):

            debug_data = (
                "Binary data, first 100 bytes: "
                f"{report_data[:100]}"
            )

        return func.HttpResponse(
            json.dumps(
                {
                    "error":
                        "Failed to process Excel "
                        "with Import ID fill",

                    "message":
                        str(e),

                    "debug_info":
                        {
                            "data_type":
                                data_type,

                            "raw_data_preview":
                                (
                                    debug_data[:1000]
                                    if isinstance(
                                        debug_data,
                                        str
                                    )
                                    else str(
                                        debug_data
                                    )
                                ),

                            "data_length":
                                (
                                    len(report_data)
                                    if report_data
                                    else 0
                                )
                        }
                }
            ),
            status_code=500,
            mimetype="application/json"
        )


# ============================================================
# CSV OUTPUT PROCESSING
# ============================================================

def handle_csv_output_minimal(
    report_data,
    data_type,
    report_id
):
    """
    Handle CSV output with minimal processing.

    ONLY fills missing Import ID values.
    """

    try:

        # ====================================================
        # TEXT DATA
        # ====================================================

        if data_type == "text":

            df = (
                parse_csv_preserving_structure(
                    report_data
                )
            )

            df = fill_missing_import_id(df)

            return create_csv_http_response(
                df,
                report_id
            )

        # ====================================================
        # BINARY DATA
        # ====================================================

        else:

            logging.info(
                "Converting binary data "
                "to CSV with Import ID fill."
            )

            converted_csv = None

            # ------------------------------------------------
            # Try ZIP
            # ------------------------------------------------
            if report_data.startswith(b"PK"):

                try:

                    zip_buffer = BytesIO(
                        report_data
                    )

                    with zipfile.ZipFile(
                        zip_buffer,
                        "r"
                    ) as zip_file:

                        file_list = (
                            zip_file.namelist()
                        )

                        for filename in file_list:

                            # =================================
                            # CSV inside ZIP
                            # =================================
                            if filename.lower().endswith(
                                ".csv"
                            ):

                                csv_data = (
                                    zip_file.read(
                                        filename
                                    )
                                )

                                try:

                                    csv_data = (
                                        csv_data.decode(
                                            "utf-8"
                                        )
                                    )

                                except UnicodeDecodeError:

                                    csv_data = (
                                        csv_data.decode(
                                            "latin-1"
                                        )
                                    )

                                df = (
                                    parse_csv_preserving_structure(
                                        csv_data
                                    )
                                )

                                df = (
                                    fill_missing_import_id(
                                        df
                                    )
                                )

                                csv_buffer = StringIO()

                                df.to_csv(
                                    csv_buffer,
                                    index=False
                                )

                                converted_csv = (
                                    csv_buffer.getvalue()
                                )

                                break

                            # =================================
                            # Excel inside ZIP
                            # =================================
                            elif filename.lower().endswith(
                                (".xlsx", ".xls")
                            ):

                                excel_data = (
                                    zip_file.read(
                                        filename
                                    )
                                )

                                excel_buffer = BytesIO(
                                    excel_data
                                )

                                df = pd.read_excel(
                                    excel_buffer,
                                    engine="openpyxl"
                                )

                                df = (
                                    fill_missing_import_id(
                                        df
                                    )
                                )

                                csv_buffer = StringIO()

                                df.to_csv(
                                    csv_buffer,
                                    index=False
                                )

                                converted_csv = (
                                    csv_buffer.getvalue()
                                )

                                break

                except Exception as zip_error:

                    logging.warning(
                        "ZIP processing failed: "
                        f"{zip_error}"
                    )

            # ------------------------------------------------
            # Try direct Excel
            # ------------------------------------------------
            if not converted_csv:

                try:

                    excel_buffer = BytesIO(
                        report_data
                    )

                    df = pd.read_excel(
                        excel_buffer,
                        engine="openpyxl"
                    )

                    df = fill_missing_import_id(
                        df
                    )

                    csv_buffer = StringIO()

                    df.to_csv(
                        csv_buffer,
                        index=False
                    )

                    converted_csv = (
                        csv_buffer.getvalue()
                    )

                except Exception as excel_error:

                    logging.warning(
                        "Excel to CSV conversion "
                        f"failed: {excel_error}"
                    )

            # ------------------------------------------------
            # Try text decoding
            # ------------------------------------------------
            if not converted_csv:

                for encoding in [
                    "utf-8",
                    "utf-16",
                    "latin-1"
                ]:

                    try:

                        text_data = (
                            report_data.decode(
                                encoding
                            )
                        )

                        if (
                            "," in text_data
                            and "\n" in text_data
                        ):

                            df = (
                                parse_csv_preserving_structure(
                                    text_data
                                )
                            )

                            df = (
                                fill_missing_import_id(
                                    df
                                )
                            )

                            csv_buffer = StringIO()

                            df.to_csv(
                                csv_buffer,
                                index=False
                            )

                            converted_csv = (
                                csv_buffer.getvalue()
                            )

                            break

                    except UnicodeDecodeError:

                        continue

            # ------------------------------------------------
            # Return converted CSV
            # ------------------------------------------------
            if converted_csv:

                return func.HttpResponse(
                    converted_csv,
                    status_code=200,
                    mimetype="text/csv",
                    headers={
                        "Content-Disposition":
                            f"attachment; "
                            f"filename="
                            f"vulnerabilities_report_"
                            f"{report_id}.csv"
                    }
                )

            # ------------------------------------------------
            # Conversion failed
            # ------------------------------------------------
            return func.HttpResponse(
                json.dumps(
                    {
                        "error":
                            "Cannot convert binary "
                            "data to CSV format",

                        "message":
                            "Try using "
                            "format=excel instead"
                    }
                ),
                status_code=400,
                mimetype="application/json"
            )

    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as conversion_error:

        logging.error(
            "Error during CSV processing: "
            f"{conversion_error}"
        )

        return func.HttpResponse(
            json.dumps(
                {
                    "error":
                        "Failed to process CSV",

                    "message":
                        str(conversion_error)
                }
            ),
            status_code=500,
            mimetype="application/json"
        )