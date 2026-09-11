import logging
import pandas as pd
import numpy as np
import io
from io import StringIO
import os
import datetime
import re
import tempfile
import traceback
import time
from azure.core.exceptions import (
    ResourceExistsError,
    ResourceNotFoundError,
    ServiceRequestError
)
import xlsxwriter
import base64
import pandas as pd
import io
import base64
import xlsxwriter

# ============================================================
# QUALYS COLUMN MAPPING
# ============================================================

# FIXED - Qualys columns should NOT be altered - keep exact column names
QUALYS_COLUMN_MAPPING = {
    # Core identification - NO CHANGES
    'Import Id': 'Import Id',
    'IP': 'IP',
    'DNS': 'Qualys Server Name',
    'OS': 'Operating System',
    'Title': 'Title',
    'QID': 'QID',

    # Vulnerability details - NO CHANGES
    'Type': 'Vulnerability Type',
    'Threat': 'Threat',
    'Impact': 'Impact',
    'Solution': 'Solution',
    'Severity': 'Severity',
    'Exploitability': 'Exploitable',
    'Port': 'Port',
    'CVE ID': 'CVE ID',
    'Results': 'Results',
    'Vuln Status': 'Vuln Status',
    'Associated Malware': 'Associated Malware',

    # Risk scoring - NO CHANGES
    'QDS': 'QDS',
    'ARS': 'ARS',
    'ACS': 'ACS',
    'TruRisk Score': 'TruRisk Score',
    'Last Fixed': 'Last Fixed'
}


# ============================================================
# DFN COLUMN MAPPING
# ============================================================

DFN_COLUMN_MAPPING = {
    'Import ID': 'Import Id',
    'ID': 'ID',
    'Exploitation Criteria': 'Exploitation Criteria',
    'Vulnerability Category': 'Vulnerability Category',
    'Vulnerability Class': 'Vulnerability Class',
    'Vulnerability Ownership': 'Vulnerability Ownership',
    'Tags': 'Tags',
    'Tag': 'Tags',
    'tags': 'Tags',
    'TAGS': 'Tags',
    'Status (IVM)': 'Status (IVM)',
    'Status (Server Owner)': 'Status (Server Owner)',
    'Rescan Date': 'Rescan Date',
    'Scope Identification': 'OLD Scope Identification',
    'Reported Date': 'Reported Date',
    'RAG': 'RAG',
    'Exception Number': 'OLD Exception Number',
    'Remediation Ownership': 'OLD Remediation Ownership',
    'IVM Remarks': 'IVM Remarks',
    'VM Status': 'VM Status',
    'Exception Expiry Date': 'Exception Expiry Date',
    'Actual Mitigation Date': 'Actual Mitigation Date',
    'Notified': 'Notified',
    'Last Fixed': 'Last Fixed'
}


# ============================================================
# CMDB COLUMN MAPPING
# ============================================================

# FIXED to prevent Operating System overwrite
CMDB_COLUMN_MAPPING = {
    'IP Address': 'IP',
    'IP': 'IP',
    'ip address': 'IP',
    'ip': 'IP',

    'Name': 'CMDB Host Name',
    'Host name': 'CMDB Host Name',
    'Hostname': 'CMDB Host Name',
    'Server Name': 'CMDB Host Name',
    'Computer Name': 'CMDB Host Name',
    'name': 'CMDB Host Name',
    'host name': 'CMDB Host Name',

    'Owned by': 'Server Owner',
    'Server Owner': 'Server Owner',
    'Owner': 'Server Owner',
    'Asset Owner': 'Server Owner',
    'owned by': 'Server Owner',
    'server owner': 'Server Owner',

    'Value Stream': 'Value stream',
    'Value stream': 'Value stream',
    'Business Value Stream': 'Value stream',
    'value stream': 'Value stream',

    'Sub Value Stream': 'Sub Value Stream',
    'Sub-Value Stream': 'Sub Value Stream',
    'sub value stream': 'Sub Value Stream',
    'sub-value stream': 'Sub Value Stream',

    # FIXED:
    # CMDB OS goes into separate column so that
    # Qualys Operating System is preserved.
    'Operating System': 'CMDB Operating System',
    'OS': 'CMDB Operating System',
    'operating system': 'CMDB Operating System',
    'os': 'CMDB Operating System',

    'Install Status': 'Install Status',
    'install status': 'Install Status',

    'Classification': 'Classification',
    'Asset Classification': 'Classification',
    'CI Classification': 'Classification',
    'classification': 'Classification',

    'Server Tier': 'Server Tier',
    'Tier': 'Server Tier',
    'Environment Tier': 'Server Tier',
    'server tier': 'Server Tier',
    'tier': 'Server Tier',

    'Class': 'Class',
    'CI Class': 'Class',
    'Asset Class': 'Class',
    'class': 'Class',

    'Application Notes': 'Application run',
    'Application run': 'Application run',
    'Application': 'Application run',
    'Business Application': 'Application run',
    'application notes': 'Application run',
    'application run': 'Application run',

    'Support group': 'Server Support Group',
    'Server Support Group': 'Server Support Group',
    'Support Group': 'Server Support Group',
    'Assignment Group': 'Server Support Group',
    'support group': 'Server Support Group',
    'server support group': 'Server Support Group',

    'Location': 'Location',
    'location': 'Location',

    'Attributes': 'Attributes',
    'attributes': 'Attributes',

    'Skip Scan': 'Skip Scan',
    'skip scan': 'Skip Scan',

    'Category': 'Category',
    'Subcategory': 'Subcategory',

    'Assigned to': 'Assigned to',
    'Operational status': 'Operational status',
    'OS Version': 'OS Version',
    'Used for': 'Used for',
    'Environment': 'Environment',
    'Manufacturer': 'Manufacturer',
    'Model ID': 'Model ID',
    'Is Virtual': 'Is Virtual',
    'Description': 'Description',
    'Asset tag': 'Asset tag',
    'Company': 'Company',
    'Updated': 'Updated',
    'Updates': 'Updates',
    'Updated by': 'Updated by'
}


# ============================================================
# FINAL TARGET COLUMNS
# ============================================================

FINAL_TARGET_COLUMNS = [
    'Import Id',
    'IP',
    'Qualys Server Name',
    'Server',
    'CMDB Host Name',
    'Legacy/Non-Legacy',
    'Classification',
    'Class',
    'Server Tier',
    'Operating System',
    'ID',
    'Title',
    'QID',
    'QID CTI',
    'Vulnerability Type',
    'Exploitation Criteria',
    'Threat',
    'Impact',
    'Solution',
    'Severity',
    'QID Severity',
    'Exploitable',
    'Port',
    'Vulnerability Category',
    'Vulnerability Class',
    'CVE ID',
    'Server Owner',
    'Server Support Group',
    'Application run',
    'Vulnerability Ownership',
    'Sub Value Stream',
    'Tags',
    'Status (IVM)',
    'Status (Server Owner)',
    'Rescan Date',
    'OLD Scope Identification',
    'Scope Identification',
    'Reported Date',
    'RAG',
    'OLD Exception Number',
    'Exception Number',
    'OLD Remediation Ownership',
    'Remediation Ownership',
    'IVM Remarks',
    'VM Status',
    'Results',
    'Vuln Status',
    'Exception Expiry Date',
    'Actual Mitigation Date',
    'Associated Malware',
    'Value stream',
    'Location',
    'Attributes',
    'Install Status',
    'QDS',
    'ARS',
    'ACS',
    'TruRisk Score',
    'Last Fixed'
]


# ============================================================
# COLUMNS TO REMOVE
# ============================================================

COLUMNS_TO_REMOVE = [
    'Protocol',
    'CVSS Base',
    'CVSS Temporal',
    'CVSS3 Base',
    'CVSS3 Temporal',
    'First Found',
    'Last Found',
    'Last Update',
    'PCI Flag',
    'Assigned to',
    'OS Version',
    'Used for',
    'Environment',
    'Manufacturer',
    'Model ID',
    'Is Virtual',
    'Description',
    'Updated',
    'Updates',
    'Updated by',
    'IP Address',
    'Exception Approval',
    'Delete?',
    'Created By',
    'Created Date',
    'Last Changed Date',
    'Last Changed By',
    'Security Team',
    'Reason Code',
    'Pending',
    'Reason_old',
    'Expiry Category',
    'Exception Status_old',
    'Asset tag',
    'Company',
    'CMDB Operating System'
]


# ============================================================
# SAFE STRING CONVERSION
# ============================================================

def safe_str_conversion(value):
    """
    Safely convert value to string,
    handling None and NaN.
    """
    if pd.isna(value) or value is None:
        return ''

    return str(value).strip()


# ============================================================
# NORMALIZE IMPORT ID
# ============================================================

def normalize_import_id(ip, qid, port):
    """
    Normalize Import ID format consistently
    across all data sources.

    Format:
        IP_QID_PORT

    If port is empty:
        IP_QID_
    """

    try:
        # Clean IP and QID first
        clean_ip = safe_str_conversion(ip)
        clean_qid = safe_str_conversion(qid)

        if not clean_ip or not clean_qid:
            logging.warning(
                f"Missing required data for Import ID - "
                f"IP: {ip}, QID: {qid}"
            )

            return f"{clean_ip}_{clean_qid}_"

        # Handle port
        port_str = ''

        if pd.notna(port) and str(port).strip():

            port_val = str(port).strip().upper()

            if port_val not in ['NA', 'NULL', 'NONE', '']:

                try:
                    # Normalize numeric ports
                    if '.' in port_val:
                        port_str = str(int(float(port_val)))
                    else:
                        port_str = str(int(port_val))

                except (ValueError, TypeError):
                    port_str = port_val

        # Always create consistent format
        if port_str:
            return f"{clean_ip}_{clean_qid}_{port_str}"

        return f"{clean_ip}_{clean_qid}_"

    except Exception as e:

        logging.warning(
            f"Error normalizing import ID for "
            f"IP:{ip}, QID:{qid}, Port:{port} - {str(e)}"
        )

        return (
            f"{safe_str_conversion(ip)}_"
            f"{safe_str_conversion(qid)}_"
        )


# ============================================================
# CALCULATE SEVERITY
# ============================================================

def calculate_severity_from_trurisk_matrix(acs, qds):
    """
    Calculate severity based on TruRisk Matrix.
    """

    try:

        acs_val = 0
        qds_val = 0

        if pd.notna(acs) and str(acs).strip() != '':
            try:
                acs_val = float(str(acs).strip())
            except (ValueError, TypeError):
                acs_val = 0

        if pd.notna(qds) and str(qds).strip() != '':
            try:
                qds_val = float(str(qds).strip())
            except (ValueError, TypeError):
                qds_val = 0

        # TruRisk Matrix
        if acs_val == 5:

            if qds_val >= 70:
                return 'Critical'
            else:
                return 'High'

        elif acs_val == 4:

            if qds_val >= 70:
                return 'High'
            else:
                return 'Medium'

        elif acs_val == 3:

            if qds_val >= 40:
                return 'Medium'
            else:
                return 'Low'

        elif acs_val == 2:

            if qds_val >= 90:
                return 'Medium'
            else:
                return 'Low'

        else:
            return 'Low'

    except Exception as e:

        logging.warning(
            f"Error calculating severity from "
            f"TruRisk matrix: {str(e)}"
        )

        return 'Low'


# ============================================================
# UPDATE SEVERITY WHEN ACS = 0
# ============================================================

def update_severity_for_zero_acs(row):
    """
    Update severity based on QID Severity
    when ACS is 0.
    """

    try:

        acs_val = 0

        if (
            pd.notna(row.get('ACS'))
            and str(row.get('ACS', '')).strip() != ''
        ):
            try:
                acs_val = float(
                    str(row['ACS']).strip()
                )
            except (ValueError, TypeError):
                acs_val = 0

        if acs_val == 0:

            qid_severity = safe_str_conversion(
                row.get('QID Severity', '')
            )

            if qid_severity in ['4', '5']:
                return 'High'

            elif qid_severity == '3':
                return 'Medium'

            elif qid_severity in ['1', '2']:
                return 'Low'

            else:
                return row.get('Severity', 'Low')

        return row.get('Severity', 'Low')

    except Exception as e:

        logging.warning(
            f"Error updating severity for zero ACS: {str(e)}"
        )

        return row.get('Severity', 'Low')


# ============================================================
# OVERWRITE TAGS FROM DFN
# ============================================================

def overwrite_tags_from_dfn(merged_df, dfn_df):
    """
    Completely overwrite Tags column
    with values from DFN data.
    """

    logging.info("=== OVERWRITING TAGS FROM DFN ===")

    # Initialize Tags
    if 'Tags' not in merged_df.columns:
        merged_df['Tags'] = ''
    else:
        merged_df['Tags'] = ''

    if dfn_df.empty:
        logging.warning(
            "DFN dataframe is empty - keeping Tags empty"
        )
        return merged_df

    if 'Tags' not in dfn_df.columns:
        logging.warning(
            "DFN data missing Tags column - keeping Tags empty"
        )
        return merged_df

    if 'Import Id' not in dfn_df.columns:
        logging.warning(
            "DFN data missing Import Id column - keeping Tags empty"
        )
        return merged_df

    # Build Tags mapping
    tags_mapping = {}

    for idx, row in dfn_df.iterrows():

        try:

            import_id = safe_str_conversion(
                row['Import Id']
            )

            tag_value = row.get('Tags')

            if (
                pd.notna(tag_value)
                and str(tag_value).strip()
            ):
                tags_mapping[import_id] = (
                    str(tag_value).strip()
                )

        except Exception as e:

            logging.warning(
                f"Error processing DFN row {idx} "
                f"for tags: {str(e)}"
            )

            continue

    logging.info(
        f"Built tags mapping from DFN with "
        f"{len(tags_mapping)} entries"
    )

    def get_tag_from_dfn(import_id):

        if pd.isna(import_id):
            return ''

        return tags_mapping.get(
            safe_str_conversion(import_id),
            ''
        )

    merged_df['Tags'] = (
        merged_df['Import Id']
        .apply(get_tag_from_dfn)
    )

    populated_tags = (
        merged_df['Tags']
        .fillna('')
        .astype(str)
        .str.strip()
        .ne('')
        .sum()
    )

    logging.info(
        f"Tags overwrite complete: "
        f"{populated_tags}/{len(merged_df)} "
        f"rows have tags from DFN"
    )

    return merged_df


# ============================================================
# CLEAN CVE ID
# ============================================================

def clean_cve_id(cve_value):
    """
    Clean CVE ID column.
    """

    if pd.isna(cve_value):
        return ''

    cve_str = str(cve_value).strip()

    if cve_str.lower() in [
        'no cve information available',
        'no cve',
        'n/a',
        'na',
        'none'
    ]:
        return ''

    return cve_str


# ============================================================
# FLEXIBLE COLUMN MAPPING
# ============================================================

def apply_flexible_column_mapping(df, column_mapping):
    """
    Apply column mapping with
    case-insensitive matching.
    """

    if df.empty:
        return df

    try:

        actual_columns = {
            col.lower().strip(): col
            for col in df.columns
        }

        mapping_lower = {
            key.lower().strip(): value
            for key, value in column_mapping.items()
        }

        rename_dict = {}

        for lower_key, target_name in mapping_lower.items():

            if lower_key in actual_columns:

                actual_col = actual_columns[lower_key]

                if actual_col != target_name:
                    rename_dict[actual_col] = target_name

        if rename_dict:

            df = df.rename(
                columns=rename_dict
            )

            logging.info(
                f"Applied flexible column mapping: "
                f"{rename_dict}"
            )

        return df

    except Exception as e:

        logging.warning(
            f"Error in flexible column mapping: {str(e)}"
        )

        return df


# ============================================================
# FIX PORT COLUMN
# ============================================================

def fix_port_column(df):
    """
    Convert Port column from float to integer,
    handling NaN values.
    """

    if 'Port' not in df.columns:
        return df

    try:

        def convert_port(port_val):

            # NaN / None
            if pd.isna(port_val) or port_val is None:
                return ''

            port_str = (
                str(port_val)
                .strip()
                .upper()
            )

            # Null values
            if port_str in [
                '',
                'NA',
                'NULL',
                'NONE',
                'NAN'
            ]:
                return ''

            try:

                port_float = float(port_str)

                if port_float.is_integer():
                    return str(int(port_float))

                return str(
                    int(round(port_float))
                )

            except (ValueError, TypeError):

                return port_str

        # Apply conversion
        df['Port'] = (
            df['Port']
            .apply(convert_port)
        )

        non_empty_ports = (
            df['Port']
            .ne('')
            .sum()
        )

        total_ports = len(df)

        logging.info(
            f"Converted Port column from float "
            f"to integer: {non_empty_ports}/"
            f"{total_ports} rows have port values"
        )

        if non_empty_ports > 0:

            sample_ports = (
                df['Port']
                [df['Port'] != '']
                .head(10)
                .tolist()
            )

            logging.info(
                f"Sample converted port values: "
                f"{sample_ports}"
            )

    except Exception as e:

        logging.warning(
            f"Error fixing port column: {str(e)}"
        )

    return df


# ============================================================
# REMOVE DUPLICATE EXPLOITABLE COLUMNS
# ============================================================

def remove_duplicate_exploitable_columns(df):
    """
    Remove duplicate Exploitable columns,
    keeping only one.
    """

    try:

        exploitable_columns = [
            col
            for col in df.columns
            if 'exploitable' in col.lower()
        ]

        if len(exploitable_columns) > 1:

            for col in exploitable_columns[1:]:

                if col in df.columns:

                    df = df.drop(
                        columns=[col]
                    )

                    logging.info(
                        f"Removed duplicate "
                        f"Exploitable column: {col}"
                    )

    except Exception as e:

        logging.warning(
            f"Error removing duplicate "
            f"exploitable columns: {str(e)}"
        )

    return df


# ============================================================
# ENSURE SINGLE QID CTI COLUMN
# ============================================================

def ensure_single_qid_cti_column(df):
    """
    Ensure only one 'QID CTI' column exists,
    placed immediately after QID.
    """

    try:

        drop_cols = [
            c
            for c in df.columns
            if c.replace('-', ' ')
                .replace('_', ' ')
                .strip()
                .lower()
                == "qid cti"
        ]

        df = df.drop(
            columns=drop_cols,
            errors='ignore'
        )

        if (
            'QID' in df.columns
            and 'QID CTI' not in df.columns
        ):

            cols = list(df.columns)

            idx = cols.index('QID') + 1

            cols = (
                cols[:idx]
                + ['QID CTI']
                + cols[idx:]
            )

            df['QID CTI'] = ''

            df = df[cols]

        logging.info(
            "Ensured single QID CTI column after QID"
        )

    except Exception as e:

        logging.warning(
            f"Error ensuring QID CTI column: {str(e)}"
        )

    return df


# ============================================================
# PRESERVE QUALYS DATA INTEGRITY
# ============================================================

def preserve_qualys_data_integrity(qualys_df):
    """
    Preserve ALL Qualys data before processing.
    """

    logging.info(
        "=== PRESERVING QUALYS DATA INTEGRITY ==="
    )

    # --------------------------------------------------------
    # Create Import ID FIRST
    # --------------------------------------------------------

    logging.info(
        "Step 1: Creating Import IDs for Qualys data"
    )

    def create_secure_import_id(row):

        ip = row.get('IP', '')
        qid = row.get('QID', '')
        port = row.get('Port', '')

        return normalize_import_id(
            ip,
            qid,
            port
        )

    qualys_df['Import Id'] = (
        qualys_df
        .apply(create_secure_import_id, axis=1)
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    total_records = len(qualys_df)

    empty_port_records = (
        qualys_df['Port'].isnull().sum()
        +
        (
            qualys_df['Port']
            .astype(str)
            .str.strip()
            == ''
        ).sum()
    )

    logging.info(
        f"Qualys data: {total_records} total records, "
        f"{empty_port_records} with empty ports"
    )

    # --------------------------------------------------------
    # Required Qualys columns
    # --------------------------------------------------------

    critical_qualys_columns = [
        'IP',
        'QID',
        'Title',
        'Type',
        'Threat',
        'Impact',
        'Solution',
        'Severity'
    ]

    missing_critical = [
        col
        for col in critical_qualys_columns
        if col not in qualys_df.columns
    ]

    if missing_critical:

        logging.error(
            f"CRITICAL: Missing essential "
            f"Qualys columns: {missing_critical}"
        )

        raise ValueError(
            f"Missing essential Qualys columns: "
            f"{missing_critical}"
        )

    # --------------------------------------------------------
    # Check completeness
    # --------------------------------------------------------

    for col in critical_qualys_columns:

        if col in qualys_df.columns:

            missing_count = (
                qualys_df[col]
                .isnull()
                .sum()
            )

            empty_count = (
                qualys_df[col]
                .astype(str)
                .str.strip()
                == ''
            ).sum()

            total_missing = (
                missing_count
                + empty_count
            )

            if total_missing > 0:

                logging.warning(
                    f"Column '{col}' has "
                    f"{total_missing} missing/empty "
                    f"values out of {total_records}"
                )

    logging.info(
        "Qualys data integrity preserved successfully"
    )

    return qualys_df


# ============================================================
# PRESERVE QUALYS OPERATING SYSTEM
# ============================================================

def preserve_qualys_operating_system(
    result_df,
    qualys_df
):
    """
    Preserve Operating System data from
    Qualys after merging.
    """

    logging.info(
        "=== PRESERVING QUALYS OPERATING SYSTEM DATA ==="
    )

    if 'Operating System' not in qualys_df.columns:

        logging.warning(
            "No Operating System column found in Qualys data"
        )

        return result_df

    if (
        'Import Id' not in qualys_df.columns
        or
        'Import Id' not in result_df.columns
    ):

        logging.warning(
            "Missing Import Id column for OS preservation"
        )

        return result_df

    # Build mapping
    qualys_os_mapping = {}

    for idx, row in qualys_df.iterrows():

        try:

            import_id = safe_str_conversion(
                row['Import Id']
            )

            os_value = row.get(
                'Operating System'
            )

            if (
                pd.notna(os_value)
                and str(os_value).strip()
            ):

                qualys_os_mapping[import_id] = (
                    str(os_value).strip()
                )

        except Exception as e:

            logging.warning(
                f"Error processing Qualys row {idx} "
                f"for OS mapping: {str(e)}"
            )

            continue

    logging.info(
        f"Built Qualys OS mapping with "
        f"{len(qualys_os_mapping)} entries"
    )

    # Restore Qualys OS
    def restore_qualys_os(import_id):

        if pd.isna(import_id):
            return ''

        return qualys_os_mapping.get(
            safe_str_conversion(import_id),
            ''
        )

    # Restore values
    for idx, row in result_df.iterrows():

        import_id = safe_str_conversion(
            row['Import Id']
        )

        if import_id in qualys_os_mapping:

            result_df.loc[
                idx,
                'Operating System'
            ] = qualys_os_mapping[import_id]

    preserved_os_count = sum(
        1
        for import_id in result_df['Import Id']
        if safe_str_conversion(import_id)
        in qualys_os_mapping
    )

    logging.info(
        f"Preserved Qualys Operating System data "
        f"for {preserved_os_count}/{len(result_df)} rows"
    )

    return result_df


# ============================================================
# PRESERVE QUALYS EXPLOITABLE
# ============================================================

def preserve_qualys_exploitable(
    result_df,
    qualys_df
):
    """
    Preserve Exploitable data from
    Qualys after merging.
    """

    logging.info(
        "=== PRESERVING QUALYS EXPLOITABLE DATA ==="
    )

    if 'Exploitable' not in qualys_df.columns:

        logging.warning(
            "No Exploitable column found in Qualys data"
        )

        return result_df

    if (
        'Import Id' not in qualys_df.columns
        or
        'Import Id' not in result_df.columns
    ):

        logging.warning(
            "Missing Import Id column "
            "for Exploitable preservation"
        )

        return result_df

    # Build mapping
    qualys_exploitable_mapping = {}

    for idx, row in qualys_df.iterrows():

        try:

            import_id = safe_str_conversion(
                row['Import Id']
            )

            exploitable_value = row.get(
                'Exploitable'
            )

            if (
                pd.notna(exploitable_value)
                and str(exploitable_value).strip()
            ):

                qualys_exploitable_mapping[
                    import_id
                ] = str(
                    exploitable_value
                ).strip()

        except Exception as e:

            logging.warning(
                f"Error processing Qualys row {idx} "
                f"for Exploitable mapping: {str(e)}"
            )

            continue

    logging.info(
        f"Built Qualys Exploitable mapping with "
        f"{len(qualys_exploitable_mapping)} entries"
    )

    # Initialize column
    if 'Exploitable' not in result_df.columns:
        result_df['Exploitable'] = ''

    # Restore values
    for idx, row in result_df.iterrows():

        import_id = safe_str_conversion(
            row['Import Id']
        )

        if import_id in qualys_exploitable_mapping:

            result_df.loc[
                idx,
                'Exploitable'
            ] = qualys_exploitable_mapping[
                import_id
            ]

    preserved_exploitable_count = sum(
        1
        for import_id in result_df['Import Id']
        if safe_str_conversion(import_id)
        in qualys_exploitable_mapping
    )

    logging.info(
        f"Preserved Qualys Exploitable data "
        f"for {preserved_exploitable_count}/"
        f"{len(result_df)} rows"
    )

    return result_df


# ============================================================
# CLEAN AND PROCESS DATA
# ============================================================

def clean_and_process_data(df):
    """
    Apply all data cleaning and processing rules.
    """

    try:

        # ----------------------------------------------------
        # Remove duplicate columns
        # ----------------------------------------------------

        df = df.loc[
            :,
            ~df.columns.duplicated()
        ]

        logging.info(
            "Removed duplicate columns"
        )

        # ----------------------------------------------------
        # Remove duplicate Exploitable columns
        # ----------------------------------------------------

        df = remove_duplicate_exploitable_columns(df)

        # ----------------------------------------------------
        # Fix Port
        # ----------------------------------------------------

        df = fix_port_column(df)

        # ----------------------------------------------------
        # Clean CVE ID
        # ----------------------------------------------------

        if 'CVE ID' in df.columns:

            df['CVE ID'] = (
                df['CVE ID']
                .apply(clean_cve_id)
            )

            logging.info(
                "Cleaned CVE ID column"
            )

        # ----------------------------------------------------
        # Preserve original Severity as QID Severity
        # ----------------------------------------------------

        if 'Severity' in df.columns:

            df['QID Severity'] = (
                df['Severity']
            )

            logging.info(
                "Copied original Severity values "
                "to QID Severity column"
            )

        # ----------------------------------------------------
        # Calculate new Severity
        # ----------------------------------------------------

        if all(
            col in df.columns
            for col in ['ACS', 'QDS']
        ):

            df['Severity'] = df.apply(
                lambda row:
                    calculate_severity_from_trurisk_matrix(
                        row.get('ACS'),
                        row.get('QDS')
                    ),
                axis=1
            )

            logging.info(
                "Updated Severity column using "
                "TruRisk Matrix based on ACS/QDS"
            )

        # ----------------------------------------------------
        # Handle ACS = 0
        # ----------------------------------------------------

        if all(
            col in df.columns
            for col in [
                'ACS',
                'QID Severity',
                'Severity'
            ]
        ):

            df['Severity'] = (
                df.apply(
                    update_severity_for_zero_acs,
                    axis=1
                )
            )

            logging.info(
                "Updated Severity column for "
                "ACS=0 cases using QID Severity"
            )

        # ----------------------------------------------------
        # Fix Import ID
        # ----------------------------------------------------

        if 'Import Id' in df.columns:

            df['Import Id'] = (
                df['Import Id']
                .apply(
                    lambda x:
                        str(x)
                        .replace('_NA', '_')
                        if pd.notna(x)
                        else x
                )
            )

            logging.info(
                "Updated Import Id format - "
                "removed '_NA' for empty ports"
            )

        # ----------------------------------------------------
        # Remove duplicate Import IDs
        # ----------------------------------------------------

        if 'Import Id' in df.columns:

            initial_rows = len(df)

            df = df.drop_duplicates(
                subset=['Import Id'],
                keep='first'
            )

            final_rows = len(df)

            removed_duplicates = (
                initial_rows - final_rows
            )

            if removed_duplicates > 0:

                logging.info(
                    f"Removed {removed_duplicates} "
                    f"duplicate Import Id rows"
                )

        # ----------------------------------------------------
        # Remove unwanted columns
        # ----------------------------------------------------

        columns_to_drop = [
            col
            for col in COLUMNS_TO_REMOVE
            if col in df.columns
        ]

        if columns_to_drop:

            df = df.drop(
                columns=columns_to_drop
            )

            logging.info(
                f"Removed columns: "
                f"{', '.join(columns_to_drop)}"
            )

    except Exception as e:

        logging.error(
            f"Error in clean_and_process_data: {str(e)}"
        )

        raise

    return df


# ============================================================
# FIND BEST EXCEL SHEET
# ============================================================

def find_best_excel_sheet(
    excel_filename,
    report_type
):
    """
    Analyze an Excel file and find the
    most appropriate sheet based on report type.
    """

    try:

        excel_file = pd.ExcelFile(
            excel_filename
        )

        sheet_names = excel_file.sheet_names

        logging.info(
            f"Excel file contains sheets: "
            f"{sheet_names}"
        )

        # ----------------------------------------------------
        # Direct Qualys sheet
        # ----------------------------------------------------

        if report_type.lower() == "qualys":

            if "Vulnerability Report" in sheet_names:

                logging.info(
                    "Found 'Vulnerability Report' "
                    "sheet - using it directly"
                )

                df = pd.read_excel(
                    excel_filename,
                    sheet_name="Vulnerability Report"
                )

                return (
                    "Vulnerability Report",
                    df
                )

        # ----------------------------------------------------
        # Priority sheets
        # ----------------------------------------------------

        priority_sheets = {

            "qualys": [
                "Vulnerability Report",
                "Vulnerabilities",
                "Qualys",
                "Report",
                "Data",
                "Details"
            ],

            "cmdb": [
                "CMDB",
                "Assets",
                "Servers",
                "Configuration Items",
                "CI"
            ],

            "dfn": [
                "DFN",
                "Vulnerability Data",
                "Previous Findings",
                "Historical",
                "RAW"
            ]
        }

        # ----------------------------------------------------
        # Key columns
        # ----------------------------------------------------

        key_columns = {

            "qualys": [
                "QID",
                "IP",
                "Title",
                "Severity",
                "CVE",
                "Port",
                "DNS",
                "OS",
                "Type",
                "Vulnerability Type"
            ],

            "cmdb": [
                "IP",
                "Name",
                "Server",
                "Class",
                "Classification",
                "Host Name",
                "Server Name",
                "Location",
                "Owner"
            ],

            "dfn": [
                "ID",
                "Status",
                "Vulnerability",
                "Remediation",
                "IP",
                "QID",
                "Severity",
                "Import ID",
                "Import Id",
                "Tags"
            ]
        }

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
            "Index"
        ]

        best_sheet = None
        best_score = -1
        best_df = None
        best_row_count = 0

        # ----------------------------------------------------
        # Check priority sheets
        # ----------------------------------------------------

        if report_type.lower() in priority_sheets:

            for sheet in priority_sheets[
                report_type.lower()
            ]:

                if sheet in sheet_names:

                    try:

                        logging.info(
                            f"Found priority sheet "
                            f"'{sheet}' for "
                            f"{report_type} report"
                        )

                        df = pd.read_excel(
                            excel_filename,
                            sheet_name=sheet
                        )

                        if df.empty:
                            continue

                        column_score = 0

                        if report_type.lower() in key_columns:

                            for col in key_columns[
                                report_type.lower()
                            ]:

                                for actual_col in df.columns:

                                    if (
                                        col.lower()
                                        in actual_col.lower()
                                    ):
                                        column_score += 1

                        if (
                            column_score > 2
                            and len(df) > 5
                        ):

                            return (
                                sheet,
                                df
                            )

                    except Exception as e:

                        logging.warning(
                            f"Error reading priority "
                            f"sheet '{sheet}': "
                            f"{str(e)}"
                        )

                        continue

        # ----------------------------------------------------
        # Analyze all remaining sheets
        # ----------------------------------------------------

        for sheet in sheet_names:

            if any(
                skip.lower() in sheet.lower()
                for skip in skip_sheets
            ):

                logging.info(
                    f"Skipping likely summary "
                    f"sheet: '{sheet}'"
                )

                continue

            try:

                df = pd.read_excel(
                    excel_filename,
                    sheet_name=sheet
                )

                if len(df) < 2:

                    logging.info(
                        f"Skipping nearly empty "
                        f"sheet: '{sheet}' "
                        f"with {len(df)} rows"
                    )

                    continue

                score = 0

                # Score based on key columns
                if report_type.lower() in key_columns:

                    for col in key_columns[
                        report_type.lower()
                    ]:

                        for actual_col in df.columns:

                            if (
                                col.lower()
                                in actual_col.lower()
                            ):

                                score += 1

                                if (
                                    col.lower()
                                    == actual_col.lower()
                                ):
                                    score += 0.5

                # Extra DFN scoring
                if report_type.lower() == "dfn":

                    has_import_id = any(
                        "import" in col.lower()
                        and "id" in col.lower()
                        for col in df.columns
                    )

                    if has_import_id:
                        score += 5

                    has_tags = any(
                        "tag" in col.lower()
                        for col in df.columns
                    )

                    if has_tags:
                        score += 3

                    vuln_indicators = [
                        "vulnerability",
                        "qid",
                        "severity",
                        "status"
                    ]

                    for indicator in vuln_indicators:

                        if any(
                            indicator in col.lower()
                            for col in df.columns
                        ):
                            score += 2

                logging.info(
                    f"Sheet '{sheet}' scored "
                    f"{score} for "
                    f"{report_type} report type "
                    f"(rows: {len(df)})"
                )

                # Select best sheet
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
                    f"Error analyzing sheet "
                    f"'{sheet}': {str(e)}"
                )

        # ----------------------------------------------------
        # Return best sheet
        # ----------------------------------------------------

        if (
            best_sheet
            and best_score > 0
        ):

            logging.info(
                f"Selected sheet '{best_sheet}' "
                f"with score {best_score} "
                f"for {report_type} report"
            )

            return (
                best_sheet,
                best_df
            )

        # ----------------------------------------------------
        # Fallback to first sheet
        # ----------------------------------------------------

        if len(sheet_names) > 0:

            df = pd.read_excel(
                excel_filename,
                sheet_name=sheet_names[0]
            )

            logging.info(
                f"No good match found, "
                f"using first sheet "
                f"'{sheet_names[0]}' "
                f"for {report_type} report"
            )

            return (
                sheet_names[0],
                df
            )

    except Exception as e:

        logging.error(
            f"Error in find_best_excel_sheet: "
            f"{str(e)}"
        )

        try:

            df = pd.read_excel(
                excel_filename
            )

            return (
                "Sheet1",
                df
            )

        except Exception as read_err:

            logging.error(
                f"Failed to read Excel file "
                f"in fallback mode: "
                f"{str(read_err)}"
            )

            raise


# ============================================================
# CREATE EXCEL WORKBOOK
# ============================================================

def create_excel_with_xlsxwriter(
    result_df,
    cycle_id,
    report_title="Vulnerability Report"
):
    """
    Create Excel workbook using xlsxwriter
    with dropdown validations and formatting.
    """

    logging.info(
        "Creating Excel workbook with xlsxwriter"
    )

    try:

        excel_buffer = io.BytesIO()

        workbook = xlsxwriter.Workbook(
            excel_buffer,
            {'in_memory': True}
        )

        worksheet = workbook.add_worksheet(
            report_title
        )

        # ----------------------------------------------------
        # Formats
        # ----------------------------------------------------

        header_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#D9D9D9',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True
        })

        data_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
            'text_wrap': True
        })

        # ----------------------------------------------------
        # Severity formats
        # ----------------------------------------------------

        critical_format = workbook.add_format({
            'bg_color': '#FF0000',
            'border': 1,
            'font_color': 'white'
        })

        high_format = workbook.add_format({
            'bg_color': '#FFA500',
            'border': 1
        })

        medium_format = workbook.add_format({
            'bg_color': '#FFFF00',
            'border': 1
        })

        low_format = workbook.add_format({
            'bg_color': '#00FF00',
            'border': 1
        })

        # ----------------------------------------------------
        # Write headers
        # ----------------------------------------------------

        for col_num, column_name in enumerate(
            result_df.columns
        ):

            worksheet.write(
                0,
                col_num,
                column_name,
                header_format
            )

        # ----------------------------------------------------
        # Write data
        # ----------------------------------------------------

        for row_num, (_, row_data) in enumerate(
            result_df.iterrows(),
            1
        ):

            for col_num, cell_value in enumerate(
                row_data
            ):

                column_name = (
                    result_df.columns[col_num]
                )

                display_value = (
                    ''
                    if pd.isna(cell_value)
                    else str(cell_value)
                )

                # Severity formatting
                if column_name == 'Severity':

                    if display_value == 'Critical':

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            critical_format
                        )

                    elif display_value == 'High':

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            high_format
                        )

                    elif display_value == 'Medium':

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            medium_format
                        )

                    elif display_value == 'Low':

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            low_format
                        )

                    else:

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            data_format
                        )

                # QID Severity formatting
                elif column_name == 'QID Severity':

                    if display_value == '5':

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            critical_format
                        )

                    elif display_value == '4':

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            high_format
                        )

                    elif display_value == '3':

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            medium_format
                        )

                    elif display_value in (
                        '2',
                        '1'
                    ):

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            low_format
                        )

                    else:

                        worksheet.write(
                            row_num,
                            col_num,
                            display_value,
                            data_format
                        )

                else:

                    worksheet.write(
                        row_num,
                        col_num,
                        display_value,
                        data_format
                    )

        # ----------------------------------------------------
        # Dropdown validations
        # ----------------------------------------------------

        dropdown_validations = {

            'Legacy/Non-Legacy': [
                'Non Legacy',
                'Legacy'
            ],

            'Scope Identification': [
                'App Dependency',
                'In Scope - BAU',
                'Scope - Others'
            ],

            'Status (IVM)': [
                'Closed',
                'Exception',
                'Open'
            ],

            'Vulnerability Class': [
                'Legacy',
                'Non Legacy'
            ],

            'RAG': [
                '-Not Set-'
            ]
        }

        for col_num, column_name in enumerate(
            result_df.columns
        ):

            if column_name in dropdown_validations:

                last_row = len(result_df)

                if last_row > 0:

                    worksheet.data_validation(
                        1,
                        col_num,
                        last_row,
                        col_num,
                        {
                            'validate': 'list',
                            'source':
                                dropdown_validations[
                                    column_name
                                ],
                            'error_message':
                                f'Please select a valid '
                                f'{column_name}'
                        }
                    )

        # ----------------------------------------------------
        # Column widths
        # ----------------------------------------------------

        for col_num, column_name in enumerate(
            result_df.columns
        ):

            header_len = len(
                str(column_name)
            )

            max_content_len = 0

            sample_data = result_df.iloc[
                :min(100, len(result_df)),
                col_num
            ]

            for value in sample_data:

                if value is not None:

                    max_content_len = max(
                        max_content_len,
                        len(str(value))
                    )

            if header_len > 20:

                width = min(
                    header_len + 5,
                    60
                )

            else:

                width = min(
                    max(
                        header_len,
                        max_content_len
                    ) + 2,
                    50
                )

            width = max(
                width,
                12
            )

            worksheet.set_column(
                col_num,
                col_num,
                width
            )

        # ----------------------------------------------------
        # Freeze panes
        # ----------------------------------------------------

        worksheet.freeze_panes(
            1,
            2
        )

        # ----------------------------------------------------
        # Close workbook
        # ----------------------------------------------------

        workbook.close()

        excel_buffer.seek(0)

        return excel_buffer.read()

    except Exception as e:

        logging.error(
            f"Error creating Excel workbook: "
            f"{str(e)}"
        )

        raise


# ============================================================
# PROCESS FILE CONTENT
# ============================================================

def process_file_content(
    content,
    file_type,
    report_type
):
    """
    Process file content directly from
    HTTP request without blob storage.
    """

    try:

        if not content:

            raise ValueError(
                f"No content provided "
                f"for {report_type} file"
            )

        # ----------------------------------------------------
        # Decode Base64
        # ----------------------------------------------------

        binary_content = base64.b64decode(
            content
        )

        # ----------------------------------------------------
        # Detect file type
        # ----------------------------------------------------

        if not file_type:

            if binary_content.startswith(b"PK"):
                file_type = 'xlsx'
            else:
                file_type = 'csv'

        logging.info(
            f"Processing {report_type} file "
            f"as {file_type}"
        )

        # ----------------------------------------------------
        # Excel
        # ----------------------------------------------------

        if file_type == 'xlsx':

            with tempfile.NamedTemporaryFile(
                suffix='.xlsx',
                delete=False
            ) as temp_file:

                temp_file.write(
                    binary_content
                )

                temp_filename = (
                    temp_file.name
                )

            try:

                sheet_name, df = (
                    find_best_excel_sheet(
                        temp_filename,
                        report_type
                    )
                )

                logging.info(
                    f"Using '{sheet_name}' sheet "
                    f"from {report_type} Excel file "
                    f"with {len(df)} rows"
                )

                if df.empty:

                    raise ValueError(
                        f"{report_type} Excel file "
                        f"contains no data"
                    )

                return df

            finally:

                try:

                    os.unlink(
                        temp_filename
                    )

                except Exception as e:

                    logging.warning(
                        f"Failed to delete temp file "
                        f"{temp_filename}: {str(e)}"
                    )

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        else:

            try:

                csv_str = (
                    binary_content
                    .decode('utf-8')
                )

            except UnicodeDecodeError:

                try:

                    csv_str = (
                        binary_content
                        .decode('latin-1')
                    )

                except UnicodeDecodeError:

                    csv_str = (
                        binary_content
                        .decode(
                            'utf-8',
                            errors='replace'
                        )
                    )

            df = pd.read_csv(
                StringIO(csv_str)
            )

            if df.empty:

                raise ValueError(
                    f"{report_type} CSV file "
                    f"contains no data"
                )

            logging.info(
                f"Processed {report_type} file "
                f"as CSV with {len(df)} rows"
            )

            return df

    except Exception as e:

        logging.error(
            f"Error processing "
            f"{report_type} content: "
            f"{str(e)}\n"
            f"{traceback.format_exc()}"
        )

        raise


# ============================================================
# MERGE CMDB DATA BY IP
# ============================================================

def merge_cmdb_data_by_ip_only(
    qualys_df,
    cmdb_df
):
    """
    Simple CMDB merge.

    Match by IP Address and apply CMDB
    information to ALL Qualys rows
    having the same IP.
    """

    if cmdb_df.empty:

        logging.warning(
            "CMDB dataframe is empty"
        )

        return qualys_df

    try:

        # ----------------------------------------------------
        # Remove duplicate columns
        # ----------------------------------------------------

        qualys_df = qualys_df.loc[
            :,
            ~qualys_df.columns.duplicated()
        ]

        cmdb_df = cmdb_df.loc[
            :,
            ~cmdb_df.columns.duplicated()
        ]

        logging.info(
            f"Original CMDB columns: "
            f"{list(cmdb_df.columns)}"
        )

        # ----------------------------------------------------
        # Apply CMDB mapping
        # ----------------------------------------------------

        cmdb_df = apply_flexible_column_mapping(
            cmdb_df,
            CMDB_COLUMN_MAPPING
        )

        logging.info(
            f"CMDB columns after mapping: "
            f"{list(cmdb_df.columns)}"
        )

        # ----------------------------------------------------
        # Validate IP
        # ----------------------------------------------------

        if 'IP' not in cmdb_df.columns:

            logging.error(
                "CMDB data missing 'IP' column "
                "after mapping"
            )

            return qualys_df

        # ----------------------------------------------------
        # Clean IP values
        # ----------------------------------------------------

        qualys_df['IP'] = (
            qualys_df['IP']
            .astype(str)
            .str.strip()
        )

        cmdb_df['IP'] = (
            cmdb_df['IP']
            .astype(str)
            .str.strip()
        )

        logging.info(
            f"Before merge - Qualys rows: "
            f"{len(qualys_df)}, "
            f"CMDB rows: {len(cmdb_df)}"
        )

        logging.info(
            f"Unique IPs - Qualys: "
            f"{qualys_df['IP'].nunique()}, "
            f"CMDB: {cmdb_df['IP'].nunique()}"
        )

        # ----------------------------------------------------
        # Remove duplicate CMDB IPs
        # ----------------------------------------------------

        initial_cmdb_count = len(
            cmdb_df
        )

        cmdb_unique = (
            cmdb_df
            .drop_duplicates(
                subset=['IP'],
                keep='first'
            )
        )

        final_cmdb_count = len(
            cmdb_unique
        )

        if (
            initial_cmdb_count
            > final_cmdb_count
        ):

            logging.info(
                f"CMDB deduplication: "
                f"{initial_cmdb_count} → "
                f"{final_cmdb_count} records"
            )

        # ----------------------------------------------------
        # Merge by IP
        # ----------------------------------------------------

        result_df = pd.merge(
            qualys_df,
            cmdb_unique,
            on='IP',
            how='left'
        )

        logging.info(
            f"After merge - Result rows: "
            f"{len(result_df)}"
        )

        # ----------------------------------------------------
        # Verify merge
        # ----------------------------------------------------

        verification_columns = [
            'CMDB Host Name',
            'Classification',
            'Class',
            'Server Tier',
            'Server Owner',
            'Server Support Group',
            'Application run',
            'Value stream'
        ]

        logging.info(
            "CMDB merge verification:"
        )

        for col in verification_columns:

            if col in result_df.columns:

                populated = (
                    result_df[col]
                    .fillna('')
                    .astype(str)
                    .str.strip()
                    .ne('')
                    .sum()
                )

                logging.info(
                    f"- {col} populated: "
                    f"{populated}/{len(result_df)} rows"
                )

        return result_df

    except Exception as e:

        logging.error(
            f"Error in CMDB merge: {str(e)}"
        )

        return qualys_df


# ============================================================
# CLEANUP TEMPORARY FILES
# ============================================================

def cleanup_temp_files(file_list):
    """
    Clean up temporary files created
    during processing.
    """

    for file_path in file_list:

        try:

            if os.path.exists(file_path):

                os.remove(file_path)

                logging.info(
                    f"Removed temporary file: "
                    f"{file_path}"
                )

        except Exception as e:

            logging.warning(
                f"Failed to remove temporary "
                f"file {file_path}: {str(e)}"
            )


# ============================================================
# ENSURE BLOB CONTAINER EXISTS
# ============================================================

def ensure_container_exists(
    blob_service_client,
    container_name
):
    """
    Ensure that the specified blob container
    exists, creating it if necessary.
    """

    try:

        container_client = (
            blob_service_client
            .get_container_client(
                container_name
            )
        )

        container_client.get_container_properties()

        logging.info(
            f"Container '{container_name}' "
            f"already exists"
        )

    except ResourceNotFoundError:

        logging.info(
            f"Container '{container_name}' "
            f"not found, creating..."
        )

        try:

            container_client = (
                blob_service_client
                .create_container(
                    container_name
                )
            )

            logging.info(
                f"Container '{container_name}' "
                f"created successfully"
            )

        except ResourceExistsError:

            logging.info(
                f"Container '{container_name}' "
                f"was created by another process"
            )

            container_client = (
                blob_service_client
                .get_container_client(
                    container_name
                )
            )

        except Exception as e:

            logging.error(
                f"Failed to create container "
                f"'{container_name}': {str(e)}"
            )

            raise

    except Exception as e:

        logging.error(
            f"Error checking container "
            f"'{container_name}': {str(e)}"
        )

        raise

    return container_client


def to_excel_bytes(df):
    """
    Convert a pandas DataFrame into Excel bytes.
    """

    buf = io.BytesIO()

    with pd.ExcelWriter(
        buf,
        engine="xlsxwriter"
    ) as writer:

        df.to_excel(
            writer,
            index=False
        )

    buf.seek(0)

    return buf.getvalue()


def to_excel_multi_sheet(sheets_dict):
    """
    Create an Excel workbook containing
    multiple DataFrame sheets.
    """

    buf = io.BytesIO()

    with pd.ExcelWriter(
        buf,
        engine="xlsxwriter"
    ) as writer:

        for sheet_name, df in sheets_dict.items():

            df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False
            )

    buf.seek(0)

    return buf.getvalue()


def merge_qualys_reports(body):
    """
    Merge Qualys reports and identify DFN records
    that are missing from the merged Qualys report.
    """

    qualys1_b = base64.b64decode(
        body["qualysReportContent"]
    )

    qualys2_content = body.get(
        "qualysReportContent2",
        ""
    )

    dfn_b = base64.b64decode(
        body["dfnReportContent"]
    )

    logging.info(
        f"Qualys1 bytes size: {len(qualys1_b)}, "
        f"DFN bytes size: {len(dfn_b)}"
    )

    qualys1 = pd.read_excel(
        io.BytesIO(qualys1_b)
    )

    logging.info(
        f"Qualys1 shape: {qualys1.shape}"
    )

    has_qualys2 = (
        qualys2_content
        and qualys2_content.strip() != ""
    )

    if has_qualys2:

        qualys2_b = base64.b64decode(
            qualys2_content
        )

        logging.info(
            f"Qualys2 bytes size: {len(qualys2_b)}"
        )

        qualys2 = pd.read_excel(
            io.BytesIO(qualys2_b)
        )

        logging.info(
            f"Qualys2 shape: {qualys2.shape}"
        )

        qualys_merged = (
            pd.concat(
                [qualys1, qualys2],
                ignore_index=True
            )
            .drop_duplicates()
        )

    else:

        logging.info(
            "Qualys2 content is empty or null, "
            "using only Qualys1"
        )

        qualys_merged = qualys1.copy()

    logging.info(
        f"Merged Qualys shape after deduplication: "
        f"{qualys_merged.shape}"
    )

    dfn = pd.read_excel(
        io.BytesIO(dfn_b)
    )

    logging.info(
        f"DFN shape: {dfn.shape}"
    )

    merged_ids = set(
        qualys_merged["Import Id"].astype(str)
    )

    logging.info(
        f"Merged Qualys unique Import Id count: "
        f"{len(merged_ids)}"
    )

    missing_dfn = dfn[
        ~dfn["Import ID"]
        .astype(str)
        .isin(merged_ids)
    ]

    logging.info(
        f"Missing DFN shape: {missing_dfn.shape}"
    )

    output_dfn = missing_dfn[
        [
            "Import ID",
            "IP Address",
            "ID",
            "Status (IVM)"
        ]
    ]

    logging.info(
        f"Output DFN shape: {output_dfn.shape}"
    )

    # --------------------------------------------------------
    # Create merged Qualys Excel
    # --------------------------------------------------------

    merged_excel_b64 = base64.b64encode(
        to_excel_bytes(qualys_merged)
    ).decode("utf-8")

    # --------------------------------------------------------
    # Create missing DFN Excel
    # --------------------------------------------------------

    missing_dfn_excel_b64 = base64.b64encode(
        to_excel_bytes(output_dfn)
    ).decode("utf-8")

    # --------------------------------------------------------
    # Create multi-sheet Excel
    # --------------------------------------------------------

    if has_qualys2:

        sheets = {
            "Merged Qualys Report": qualys_merged,
            "1st Download": qualys1,
            "2nd Download": qualys2
        }

        logging.info(
            "Created multi-sheet Excel with 3 sheets"
        )

    else:

        sheets = {
            "Merged Qualys Report": qualys_merged,
            "1st Download": qualys1
        }

        logging.info(
            "Created multi-sheet Excel with 2 sheets "
            "(no 2nd download)"
        )

    merge_qualys_sheet_b64 = base64.b64encode(
        to_excel_multi_sheet(sheets)
    ).decode("utf-8")

    return {
        "merge_qualys_report": merged_excel_b64,
        "missing_dfn_report": missing_dfn_excel_b64,
        "missing_count": len(output_dfn),
        "merge_qualys_sheet": merge_qualys_sheet_b64
    }
    

def extract_missing_dfn_ips(body):
    qualys_b = base64.b64decode(body["qualysReportContent"])
    dfn_b = base64.b64decode(body["dfnReportContent"])

    logging.info(
        f"Qualys bytes size: {len(qualys_b)}, "
        f"DFN bytes size: {len(dfn_b)}"
    )

    qualys = pd.read_excel(io.BytesIO(qualys_b))
    logging.info(f"Qualys shape: {qualys.shape}")

    dfn = pd.read_excel(io.BytesIO(dfn_b))
    logging.info(f"DFN shape: {dfn.shape}")

    # Get unique Import Ids from Qualys report
    qualys_ids = set(
        qualys["Import Id"].astype(str)
    )

    logging.info(
        f"Qualys unique Import Id count: {len(qualys_ids)}"
    )

    # Find DFN records whose Import ID is not in Qualys
    missing_dfn = dfn[
        ~dfn["Import ID"].astype(str).isin(qualys_ids)
    ]

    logging.info(
        f"Missing DFN records count: {len(missing_dfn)}"
    )

    # Extract unique IP addresses from missing records
    missing_ips = (
        missing_dfn["IP Address"]
        .dropna()
        .unique()
        .tolist()
    )

    logging.info(
        f"Missing unique IP addresses count: "
        f"{len(missing_ips)}"
    )

    return {
        "missing_ips": missing_ips,
        "missing_count": len(missing_ips)
    }