import logging
import json
import pandas as pd
import numpy as np
import io
import datetime
import traceback
import time
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import PatternFill, Border, Side, Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
import xlsxwriter
import base64
import tempfile
from io import StringIO, BytesIO
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import math


def convert_numpy_types(obj):
    """
    Convert numpy types to Python native types for JSON serialization.
    """
    if isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


def safe_value_conversion(value):
    """
    Safely convert any cell value for Excel writing (handles Series, NaN, etc.).
    """
    try:
        # Series: Take first value if exists, else empty string
        if isinstance(value, pd.Series):
            if len(value) == 0:
                return ""
            value = value.iloc[0]
        # NaN or None: Excel expects empty
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return ""
        return value
    except Exception:
        return str(value)  # Fallback: string representation


def find_best_excel_sheet(excel_filename, report_type):
    """
    Analyzes an Excel file to find the most appropriate sheet based on the report type.
    """
    try:
        wb = openpyxl.load_workbook(excel_filename, read_only=True)
        sheet_names = wb.sheetnames
        logging.info(f"Excel file contains sheets: {sheet_names}")
        
        # Priority sheet lists for different report types
        priority_sheets = {
            "merged": ["New Vulnerabilities", "Vulnerability Report", "Vulnerabilities", "Report", "Data", "Details"],
            "qid": ["QID", "QIDs", "Vulnerability IDs", "IDs", "Data", "Sheet1"],
            "legacy": ["Legacy", "Legacy IPs", "IPs", "Legacy Data", "Data", "Sheet1"],
            "allvuln": ["All Vulnerabilities", "Vulnerabilities", "Report", "Data", "Details", "Sheet1"],
            "newvuln": ["New Vulnerabilities", "Vulnerabilities", "Report", "Data", "Details", "Sheet1"]
        }
        
        # Try exact matches with priority sheet names
        if report_type.lower() in priority_sheets:
            for sheet in priority_sheets[report_type.lower()]:
                if sheet in sheet_names:
                    logging.info(f"Found priority sheet '{sheet}' for {report_type} report")
                    df = pd.read_excel(excel_filename, sheet_name=sheet)
                    if len(df) > 0:
                        return sheet, df

        # Fallback to first sheet
        if len(sheet_names) > 0:
            df = pd.read_excel(excel_filename, sheet_name=sheet_names[0])
            logging.info(f"Using first sheet '{sheet_names[0]}' for {report_type} report")
            return sheet_names[0], df
        
    except Exception as e:
        logging.error(f"Error in find_best_excel_sheet: {str(e)}")
        try:
            df = pd.read_excel(excel_filename)
            return "Sheet1", df
        except Exception as read_err:
            logging.error(f"Failed to read Excel file in fallback mode: {str(read_err)}")
            raise


def process_file_content(content, file_type, report_type):
    """
    Process file content from request directly without using blob storage.
    """
    try:
        # Decode base64 content
        binary_content = base64.b64decode(content)
        
        # Determine file type if not specified
        if not file_type:
            if binary_content.startswith(b"PK"):  # Excel files are zip archives
                file_type = 'xlsx'
            else:
                file_type = 'csv'
                
        logging.info(f"Processing {report_type} file as {file_type}")
        
        # Process based on file type
        if file_type == 'xlsx':
            with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
                temp_file.write(binary_content)
                temp_filename = temp_file.name
                
            sheet_name, df = find_best_excel_sheet(temp_filename, report_type)
            logging.info(f"Using '{sheet_name}' sheet from {report_type} Excel file with {len(df)} rows")
            
            try:
                os.unlink(temp_filename)
            except Exception as e:
                logging.warning(f"Failed to delete temp file {temp_filename}: {str(e)}")
                
            return df
        else:
            try:
                csv_str = binary_content.decode('utf-8')
            except UnicodeDecodeError:
                csv_str = binary_content.decode('utf-8', errors='replace')
                
            df = pd.read_csv(StringIO(csv_str))
            logging.info(f"Processed {report_type} file as CSV with {len(df)} rows")
            return df
            
    except Exception as e:
        logging.error(f"Error processing {report_type} content: {str(e)}\n{traceback.format_exc()}")
        raise


def update_new_vulnerabilities_before_merge(new_vuln_df):
    """
    Update new vulnerabilities with today's date for Reported Date and RAG = Green
    before merging with all vulnerabilities.
    """
    try:
        logging.info("Updating new vulnerabilities with Reported Date and RAG before merge")
        
        # Get today's date in dd/mm/yyyy format
        today_str = datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Ensure columns exist and update them
        if 'Reported Date' not in new_vuln_df.columns:
            new_vuln_df['Reported Date'] = today_str
            logging.info("Created 'Reported Date' column")
        else:
            new_vuln_df['Reported Date'] = today_str
            logging.info("Updated existing 'Reported Date' column")
        
        if 'RAG' not in new_vuln_df.columns:
            new_vuln_df['RAG'] = 'Green'
            logging.info("Created 'RAG' column")
        else:
            new_vuln_df['RAG'] = 'Green'
            logging.info("Updated existing 'RAG' column")
        
        logging.info(f"Updated {len(new_vuln_df)} new vulnerability records:")
        logging.info(f"  - Reported Date: {today_str}")
        logging.info(f"  - RAG: Green")
        
        return new_vuln_df
        
    except Exception as e:
        logging.error(f"Error in update_new_vulnerabilities_before_merge: {str(e)}")
        raise


def preprocess_old_columns_before_merge(df):
    """
    Merge OLD columns into their target columns before main merge.
    This prevents data loss during the merge process.
    """
    try:
        logging.info("Preprocessing OLD columns before merge")
        
        df_processed = df.copy()
        
        # Define OLD column mappings
        old_column_mappings = {
            'OLD Scope Identification': 'Scope Identification',
            'OLD Exception Number': 'Exception Number', 
            'OLD Remediation Ownership': 'Remediation Ownership'
        }
        
        updated_counts = {}
        
        # Process each OLD column mapping
        for old_col, target_col in old_column_mappings.items():
            if old_col in df_processed.columns:
                # Ensure target column exists
                if target_col not in df_processed.columns:
                    df_processed[target_col] = ''
                    logging.info(f"Created '{target_col}' column")
                
                # Create mask for non-empty OLD values
                old_values = df_processed[old_col].fillna('')
                mask = (old_values.astype(str).str.strip() != '') & (old_values.astype(str).str.strip().str.lower() != 'nan')
                
                # Update target column with OLD values where OLD is not empty
                df_processed.loc[mask, target_col] = df_processed.loc[mask, old_col]
                updated_count = mask.sum()
                updated_counts[old_col] = updated_count
                
                # Remove OLD column
                df_processed = df_processed.drop(columns=[old_col])
                
                logging.info(f"Processed {old_col}: {updated_count} values merged into {target_col}")
        
        total_old_columns_processed = len(updated_counts)
        logging.info(f"OLD columns preprocessing completed: {total_old_columns_processed} OLD columns processed")
        
        return df_processed, updated_counts
        
    except Exception as e:
        logging.error(f"Error in preprocess_old_columns_before_merge: {str(e)}")
        raise


def merge_vulnerability_data(all_vuln_df, new_vuln_df):
    """
    Merge new vulnerabilities into all vulnerabilities based on Import ID.
    UPDATED: Preprocesses OLD columns BEFORE merge to prevent data loss.
    """
    try:
        logging.info("Starting vulnerability data merge process with OLD column preprocessing")
        
        # Store original column order
        original_column_order = list(all_vuln_df.columns)
        
        # Validate Import Id columns
        if 'Import Id' not in new_vuln_df.columns:
            raise ValueError("'Import Id' column not found in new vulnerabilities data")
        if 'Import Id' not in all_vuln_df.columns:
            raise ValueError("'Import Id' column not found in all vulnerabilities data")
        
        # STEP 1: Preprocess OLD columns in BOTH datasets
        logging.info("Step 1: Preprocessing OLD columns in all vulnerabilities dataset...")
        all_vuln_processed, all_vuln_old_counts = preprocess_old_columns_before_merge(all_vuln_df)
        
        logging.info("Step 1: Preprocessing OLD columns in new vulnerabilities dataset...")
        new_vuln_processed, new_vuln_old_counts = preprocess_old_columns_before_merge(new_vuln_df)
        
        # STEP 2: Now perform standard merge without OLD column complications
        logging.info("Step 2: Performing standard merge on preprocessed data...")
        
        # Get Import IDs for tracking
        new_import_ids = set(new_vuln_processed['Import Id'].tolist())
        existing_import_ids = set(all_vuln_processed['Import Id'].tolist())
        override_ids = new_import_ids.intersection(existing_import_ids)
        new_ids = new_import_ids - existing_import_ids
        
        logging.info(f"Found {len(override_ids)} entries to override")
        logging.info(f"Found {len(new_ids)} new entries to add")
        
        # Remove existing entries that will be overridden
        original_count = len(all_vuln_processed)
        if override_ids:
            all_vuln_processed = all_vuln_processed[~all_vuln_processed['Import Id'].isin(override_ids)]
            logging.info(f"Removed {original_count - len(all_vuln_processed)} existing entries for override")
        
        # Get entries to add (both override and new)
        entries_to_add = new_vuln_processed[new_vuln_processed['Import Id'].isin(new_import_ids)].copy()
        
        # Align columns
        all_vuln_columns = set(all_vuln_processed.columns.tolist())
        new_vuln_columns = set(entries_to_add.columns.tolist())
        
        # Final column order: start with original, add new ones
        final_column_order = original_column_order.copy()
        new_columns_to_add = new_vuln_columns - all_vuln_columns
        
        if new_columns_to_add:
            logging.info(f"Adding {len(new_columns_to_add)} new columns: {list(new_columns_to_add)}")
            final_column_order.extend(sorted(list(new_columns_to_add)))
        
        # Add missing columns to both DataFrames
        for col in final_column_order:
            if col not in all_vuln_processed.columns:
                all_vuln_processed[col] = None
            if col not in entries_to_add.columns:
                entries_to_add[col] = None
        
        # Reorder columns
        all_vuln_processed = all_vuln_processed[final_column_order]
        entries_to_add = entries_to_add[final_column_order]
        
        # Concatenate DataFrames
        merged_df = pd.concat([all_vuln_processed, entries_to_add], ignore_index=True)
        
        # Sort by Import Id
        merged_df = merged_df.sort_values('Import Id').reset_index(drop=True)
        
        logging.info(f"Successfully merged vulnerability data:")
        logging.info(f"  - Original all vulnerabilities: {original_count} records")
        logging.info(f"  - New vulnerabilities to process: {len(new_vuln_df)} records")
        logging.info(f"  - Overridden existing records: {len(override_ids)}")
        logging.info(f"  - Added new records: {len(new_ids)}")
        logging.info(f"  - Final merged dataset: {len(merged_df)} records")
        logging.info(f"  - OLD columns preprocessed and removed")
        
        return merged_df, len(override_ids), len(new_ids)
        
    except Exception as e:
        logging.error(f"Error in merge_vulnerability_data: {str(e)}")
        raise

        
    except Exception as e:
        logging.error(f"Error in merge_vulnerability_data: {str(e)}")
        raise


def clean_vulnerability_category_typos(merged_df):
    """
    Clean up typos in Vulnerability Category column - standardize to 'NON-OS Level'
    """
    try:
        logging.info("Cleaning Vulnerability Category typos")
        
        if 'Vulnerability Category' not in merged_df.columns:
            merged_df['Vulnerability Category'] = ''
            logging.info("Created 'Vulnerability Category' column")
            return merged_df, 0
        
        # Count records before cleaning
        before_cleaning = merged_df['Vulnerability Category'].value_counts().to_dict()
        
        # Standardize the values - strip whitespace and fix typos
        merged_df['Vulnerability Category'] = merged_df['Vulnerability Category'].astype(str).str.strip()
        merged_df['Vulnerability Category'] = merged_df['Vulnerability Category'].replace({
            'Non-OS Level': 'NON-OS Level',  # Fix the typo
            'non-os level': 'NON-OS Level',  # Handle lowercase
            'Non-Os Level': 'NON-OS Level',  # Handle mixed case
            'NON-Os Level': 'NON-OS Level'   # Handle mixed case
        })
        
        # Count records after cleaning
        after_cleaning = merged_df['Vulnerability Category'].value_counts().to_dict()
        fixed_count = before_cleaning.get('Non-OS Level', 0)
        
        logging.info(f"Vulnerability Category cleaning completed:")
        logging.info(f"  - Fixed 'Non-OS Level' typos: {fixed_count} records")
        logging.info(f"  - After cleaning: {after_cleaning}")
        
        return merged_df, fixed_count
        
    except Exception as e:
        logging.error(f"Error in clean_vulnerability_category_typos: {str(e)}")
        raise


def normalize_value_streams(merged_df):
    """
    Normalize Value Stream and Sub Value Stream columns according to business rules.
    """
    try:
        logging.info("Normalizing Value Stream and Sub Value Stream columns")
        
        # Handle Value Stream column name - check for both variations
        value_stream_col = None
        if 'Value Stream' in merged_df.columns:
            value_stream_col = 'Value Stream'
        elif 'Value stream' in merged_df.columns:
            value_stream_col = 'Value stream'
        else:
            merged_df['Value Stream'] = ''
            value_stream_col = 'Value Stream'
            logging.info("Created 'Value Stream' column")
        
        # Ensure Sub Value Stream exists
        if 'Sub Value Stream' not in merged_df.columns:
            merged_df['Sub Value Stream'] = ''
            logging.info("Created 'Sub Value Stream' column")
        
        # Define mapping rules for Value Stream
        value_stream_mapping = {
            'Corporate': 'Corporate Functions',
            'Enterprise Services - Digital Foundation': 'Digital Foundation',
            'Consumer': 'MarTech',
            'NA': 'VS-TBD',
            '': 'VS-TBD',  # Empty or blank
            'nan': 'VS-TBD'  # Handle 'nan' strings
        }
        
        # Define mapping rules for Sub Value Stream
        sub_value_stream_mapping = {
            'DA&I Strategy, Innovation and Transforma': 'DA&I Strategy, Innovation and Transformation',
            'Global Data Platforms, Engineering and O': 'Global Data Platforms, Engineering and Operations',
            'Azure & Compute': 'Azure, Compute & EUC',
            'EUC': 'Azure, Compute & EUC',
            'Azure, Compute & EUC': 'Azure, Compute & EUC',
            'Customer Execution': 'Customer',
            'Customer': 'Customer',
            'IADM': 'IDAM',
            'IDAM': 'IDAM',
            'Networks, DC & CRES': 'Networks, DC, CRES & UCC',
            'UC_Collaboration': 'Networks, DC, CRES & UCC',
            'Network': 'Networks, DC, CRES & UCC',
            'Networks & DC': 'Networks, DC, CRES & UCC',
            'CRES': 'Networks, DC, CRES & UCC',
            'Consumer': 'MarTech',
            'NA': 'SVS-TBD',
            '': 'SVS-TBD',  # Empty or blank
            'nan': 'SVS-TBD'  # Handle 'nan' strings
        }
        
        value_stream_updated = 0
        sub_value_stream_updated = 0
        
        # Apply normalization rules
        for idx, row in merged_df.iterrows():
            # Handle Value Stream normalization
            val_stream = str(row.get(value_stream_col, '')).strip()
            if pd.isna(row.get(value_stream_col)) or val_stream.lower() == 'nan':
                val_stream = ''
            
            new_val_stream = value_stream_mapping.get(val_stream, val_stream)
            if new_val_stream != val_stream:
                merged_df.at[idx, value_stream_col] = new_val_stream
                value_stream_updated += 1
            
            # Handle Sub Value Stream normalization
            sub_val_stream = str(row.get('Sub Value Stream', '')).strip()
            if pd.isna(row.get('Sub Value Stream')) or sub_val_stream.lower() == 'nan':
                sub_val_stream = ''
            
            new_sub_val_stream = sub_value_stream_mapping.get(sub_val_stream, sub_val_stream)
            if new_sub_val_stream != sub_val_stream:
                merged_df.at[idx, 'Sub Value Stream'] = new_sub_val_stream
                sub_value_stream_updated += 1
        
        logging.info(f"Value Stream normalization completed:")
        logging.info(f"  - Value Stream records updated: {value_stream_updated}")
        logging.info(f"  - Sub Value Stream records updated: {sub_value_stream_updated}")
        
        return merged_df, value_stream_updated, sub_value_stream_updated
        
    except Exception as e:
        logging.error(f"Error in normalize_value_streams: {str(e)}")
        raise


def apply_legacy_classification(merged_df, legacy_df):
    """
    Update ONLY Vulnerability Class column based on IP addresses in legacy data.
    Only updates rows where Vulnerability Class column is blank/empty.
    """
    try:
        logging.info("Applying legacy classification to Vulnerability Class column based on IP addresses")
        
        # Create lookup set for efficient checking
        legacy_ip_set = set()
        if not legacy_df.empty and 'IP' in legacy_df.columns:
            # Convert IPs to string and remove any NaN/empty values
            legacy_ips = legacy_df['IP'].astype(str).dropna()
            legacy_ip_set = set(ip.strip() for ip in legacy_ips if ip.strip() and ip.strip().lower() != 'nan')
            logging.info(f"Legacy IP set contains {len(legacy_ip_set)} IP addresses")
        else:
            logging.warning("Legacy data is empty or missing 'IP' column")
        
        # Ensure Vulnerability Class column exists
        if 'Vulnerability Class' not in merged_df.columns:
            merged_df['Vulnerability Class'] = ''
            logging.info("Created 'Vulnerability Class' column")
        
        # Check if IP column exists in merged data
        if 'IP' not in merged_df.columns:
            logging.warning("'IP' column not found in merged data. Cannot apply legacy classification")
            return merged_df, 0, 0, len(merged_df)
        
        legacy_count = 0
        non_legacy_count = 0
        skipped_count = 0
        
        # Apply legacy classification ONLY to Vulnerability Class
        for idx, row in merged_df.iterrows():
            # Check if Vulnerability Class column is blank/empty
            current_vuln_class = str(row.get('Vulnerability Class', '')).strip()
            
            # Only process if Vulnerability Class is blank/empty/NaN
            if not current_vuln_class or current_vuln_class == '' or current_vuln_class.lower() == 'nan':
                ip = str(row.get('IP', '')).strip()
                
                if ip and ip.lower() != 'nan' and ip in legacy_ip_set:
                    merged_df.at[idx, 'Vulnerability Class'] = 'Legacy'
                    legacy_count += 1
                else:
                    merged_df.at[idx, 'Vulnerability Class'] = 'Non Legacy'
                    non_legacy_count += 1
            else:
                # Skip rows that already have a value in Vulnerability Class
                skipped_count += 1
        
        logging.info(f"Vulnerability Class classification completed:")
        logging.info(f"  - Updated to Legacy: {legacy_count} records")
        logging.info(f"  - Updated to Non Legacy: {non_legacy_count} records")
        logging.info(f"  - Skipped (already had values): {skipped_count} records")
        
        return merged_df, legacy_count, non_legacy_count, skipped_count
        
    except Exception as e:
        logging.error(f"Error in apply_legacy_classification: {str(e)}")
        raise


def apply_qid_cti_classification(merged_df, qid_df):
    """
    Update QID CTI column based on QID values in QID data.
    If QID is not present in QID data, mark as 'Vulnerability Normal'.
    """
    try:
        logging.info("Applying QID CTI classification based on QID values")
        
        # Create lookup set for efficient checking
        qid_set = set()
        if not qid_df.empty and 'QID' in qid_df.columns:
            # Convert QIDs to string and remove any NaN/empty values
            qids = qid_df['QID'].astype(str).dropna()
            qid_set = set(qid.strip() for qid in qids if qid.strip() and qid.strip().lower() != 'nan')
            logging.info(f"QID set contains {len(qid_set)} QIDs")
        else:
            logging.warning("QID data is empty or missing 'QID' column")
        
        # Ensure QID CTI column exists
        if 'QID CTI' not in merged_df.columns:
            merged_df['QID CTI'] = ''
            logging.info("Created 'QID CTI' column")
        
        # Check if QID column exists in merged data
        if 'QID' not in merged_df.columns:
            logging.warning("'QID' column not found in merged data. Setting all QID CTI entries to 'Vulnerability Normal'")
            merged_df['QID CTI'] = 'Vulnerability Normal'
            return merged_df, 0, 0, len(merged_df)
        
        highly_exploitable_count = 0
        vulnerability_normal_count = 0
        
        # Apply QID CTI classification
        for idx, row in merged_df.iterrows():
            qid = str(row.get('QID', '')).strip()
            
            if qid and qid.lower() != 'nan' and qid in qid_set:
                merged_df.at[idx, 'QID CTI'] = 'Highly Exploitable'
                highly_exploitable_count += 1
            else:
                # QID not in QID data or QID is empty/NaN
                merged_df.at[idx, 'QID CTI'] = 'Normal Vulnerability'
                vulnerability_normal_count += 1
        
        logging.info(f"QID CTI classification completed:")
        logging.info(f"  - Marked as Highly Exploitable: {highly_exploitable_count} records")
        logging.info(f"  - Marked as VNormal Vulnerability: {vulnerability_normal_count} records")
        
        return merged_df, highly_exploitable_count, vulnerability_normal_count
        
    except Exception as e:
        logging.error(f"Error in apply_qid_cti_classification: {str(e)}")
        raise


def apply_tags_logic(merged_df):
    """
    Update Tags column based on Vulnerability Class and QID CTI combinations,
    and add current FY Quarter for non-exploitable entries.
    
    FY Quarter mapping (Financial Year ends in June, starts in July):
    - July to September (2025) = FY26-Q1
    - October to December (2025) = FY26-Q2
    - January to March (2026) = FY26-Q3
    - April to June (2026) = FY26-Q4
    - July to September (2026) = FY27-Q1
    
    IMPORTANT: Highly Exploitable Legacy/Non Legacy entries get ONLY exploitable tags, no FY quarters.
    """
    try:
        logging.info("Applying Tags logic with complete replacement for Highly Exploitable entries")
        
        # Calculate current FY and Quarter - CORRECTED LOGIC
        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        
        # Financial year starts in July - FY number represents the ending year
        if current_month >= 7:  # July to December
            fiscal_year = current_year + 1  # 2025 + 1 = 2026
            # July=Q1, Aug=Q1, Sep=Q1, Oct=Q2, Nov=Q2, Dec=Q2
            if 7 <= current_month <= 9:
                quarter = "Q1"
            else:  # 10-12
                quarter = "Q2"
        else:  # January to June
            fiscal_year = current_year  # 2026 stays 2026
            # Jan=Q3, Feb=Q3, Mar=Q3, Apr=Q4, May=Q4, Jun=Q4
            if 1 <= current_month <= 3:
                quarter = "Q3"
            else:  # 4-6
                quarter = "Q4"
        
        current_fy_quarter = f"FY{str(fiscal_year)[-2:]}-{quarter}"
        logging.info(f"Current FY Quarter: {current_fy_quarter}")  # FY26-Q1 for September 2025
        
        # Ensure Tags column exists
        if 'Tags' not in merged_df.columns:
            merged_df['Tags'] = ''
        
        exploitable_tags_count = 0
        fy_quarter_added_count = 0
        fy_quarter_already_present_count = 0
        
        def add_fy_quarter_to_tags(current_tags_str, fy_quarter):
            """Add FY Quarter to existing tags if not already present."""
            if not current_tags_str or current_tags_str.strip() == '' or pd.isna(current_tags_str):
                return fy_quarter, True
            
            # Split existing tags and filter out empty/nan values
            existing_tags = [
                tag.strip() for tag in str(current_tags_str).split('\n') 
                if tag.strip() and tag.strip().lower() != 'nan'
            ]
            
            # Check if current FY quarter already exists
            if fy_quarter in existing_tags:
                return '\n'.join(sorted(existing_tags)), False
            
            # Add current FY quarter
            existing_tags.append(fy_quarter)
            return '\n'.join(sorted(existing_tags)), True
        
        # Apply Tags logic
        for idx, row in merged_df.iterrows():
            vulnerability_class = str(row.get('Vulnerability Class', '')).strip()
            qid_cti = str(row.get('QID CTI', '')).strip()
            current_tags = str(row.get('Tags', '')).strip()
            
            # COMPLETE REPLACEMENT: Legacy + Highly Exploitable
            if vulnerability_class == "Legacy" and qid_cti == "Highly Exploitable":
                merged_df.at[idx, 'Tags'] = "Legacy Highly Exploitable"
                exploitable_tags_count += 1
            
            # COMPLETE REPLACEMENT: Non Legacy + Highly Exploitable  
            elif vulnerability_class == "Non Legacy" and qid_cti == "Highly Exploitable":
                merged_df.at[idx, 'Tags'] = "Non-Legacy Highly Exploitable"
                exploitable_tags_count += 1
            
            # For all other cases, add FY Quarter (append mode)
            else:
                updated_tags, was_added = add_fy_quarter_to_tags(current_tags, current_fy_quarter)
                merged_df.at[idx, 'Tags'] = updated_tags
                
                if was_added:
                    fy_quarter_added_count += 1
                else:
                    fy_quarter_already_present_count += 1
        
        logging.info(f"Tags logic completed:")
        logging.info(f"  - Set exploitable tags (COMPLETE REPLACEMENT): {exploitable_tags_count} records")
        logging.info(f"  - Added FY Quarter ({current_fy_quarter}): {fy_quarter_added_count} records")
        logging.info(f"  - FY Quarter already present: {fy_quarter_already_present_count} records")
        
        return merged_df, exploitable_tags_count, fy_quarter_added_count, fy_quarter_already_present_count
        
    except Exception as e:
        logging.error(f"Error in apply_tags_logic: {str(e)}")
        raise


def rename_scope_identification_values(merged_df):
    """
    Rename values in 'Scope Identification' column during merge process:
    - 'Application Dependent' → 'App Dependency'
    - 'out-of-scope' → 'Scope - Others'
    """
    try:
        logging.info("Renaming Scope Identification column values")
        
        # Ensure Scope Identification column exists
        if 'Scope Identification' not in merged_df.columns:
            merged_df['Scope Identification'] = ''
            logging.info("Created 'Scope Identification' column")
            return merged_df, 0
        
        # Define the renaming map
        rename_mapping = {
            'Application Dependent': 'App Dependency',
            'out-of-scope': 'Scope - Others'
        }
        
        renamed_count = 0
        
        # Apply renaming for each mapping
        for old_value, new_value in rename_mapping.items():
            # Create mask for exact matches (case-sensitive, strip whitespace)
            mask = merged_df['Scope Identification'].astype(str).str.strip() == old_value
            count_for_this_mapping = mask.sum()
            
            # Update values
            merged_df.loc[mask, 'Scope Identification'] = new_value
            renamed_count += count_for_this_mapping
            
            if count_for_this_mapping > 0:
                logging.info(f"  - Renamed '{old_value}' → '{new_value}': {count_for_this_mapping} records")
        
        logging.info(f"Scope Identification renaming completed:")
        logging.info(f"  - Total values renamed: {renamed_count} records")
        
        return merged_df, renamed_count
        
    except Exception as e:
        logging.error(f"Error in rename_scope_identification_values: {str(e)}")
        raise


def update_exception_records(merged_df):
    """
    Update records based on Exception Number and Exception Expiry Date:
    If Exception Number is present AND Exception Expiry Date > today AND Status (IVM) is not "Closed"
    → Update Status (IVM), Exception Number, IVM Remarks, Exception Expiry Date
    """
    try:
        logging.info("Updating records based on Exception rules")
        
        # Ensure required columns exist
        required_columns = ['Exception Number', 'Exception Expiry Date', 'Status (IVM)', 'IVM Remarks']
        for col in required_columns:
            if col not in merged_df.columns:
                merged_df[col] = ''
                logging.info(f"Created '{col}' column")
        
        today = datetime.datetime.now().date()
        updated_count = 0
        
        # Process each row
        for idx, row in merged_df.iterrows():
            exception_number = str(row.get('Exception Number', '')).strip()
            exception_expiry_raw = row.get('Exception Expiry Date', '')
            status_ivm = str(row.get('Status (IVM)', '')).strip()
            ivm_remarks = str(row.get('IVM Remarks', '')).strip()
            
            # Skip if no exception number
            if not exception_number or exception_number.lower() in ['', 'nan', 'none']:
                continue
            
            # Parse Exception Expiry Date
            try:
                if isinstance(exception_expiry_raw, datetime.datetime):
                    expiry_date = exception_expiry_raw.date()
                elif isinstance(exception_expiry_raw, datetime.date):
                    expiry_date = exception_expiry_raw
                elif isinstance(exception_expiry_raw, str) and exception_expiry_raw.strip():
                    # Try multiple date formats
                    date_str = exception_expiry_raw.strip()
                    if date_str.lower() in ['nan', 'none', '']:
                        continue
                    try:
                        expiry_date = datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
                    except ValueError:
                        try:
                            expiry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        except ValueError:
                            try:
                                expiry_date = datetime.datetime.strptime(date_str, '%m/%d/%Y').date()
                            except ValueError:
                                continue
                else:
                    continue
            except Exception:
                continue
            
            # Check conditions: Exception Expiry Date > today AND Status (IVM) is not "Closed"
            if expiry_date > today and status_ivm.lower() != 'closed':
                # Update Status (IVM)
                merged_df.at[idx, 'Status (IVM)'] = 'Exception'
                
                # Update Exception Number (ensure it's preserved exactly as provided)
                merged_df.at[idx, 'Exception Number'] = exception_number
                
                # Update IVM Remarks - append "Under Exception" if not already present
                if 'under exception' not in ivm_remarks.lower():
                    if ivm_remarks and ivm_remarks.lower() not in ['', 'nan', 'none']:
                        new_remarks = ivm_remarks + ', Under Exception'
                        merged_df.at[idx, 'IVM Remarks'] = new_remarks
                    else:
                        merged_df.at[idx, 'IVM Remarks'] = 'Under Exception'
                
                # Update Exception Expiry Date (ensure proper format)
                merged_df.at[idx, 'Exception Expiry Date'] = expiry_date.strftime('%d/%m/%Y')
                
                updated_count += 1
                logging.debug(f"Row {idx}: Updated for Exception {exception_number} expiring {expiry_date}")
        
        logging.info(f"Exception records updates completed:")
        logging.info(f"  - Exception records updated: {updated_count}")
        logging.info(f"  - Rule: Exception Number present AND Exception Expiry Date > today AND Status (IVM) ≠ 'Closed'")
        logging.info(f"    → Status (IVM) = 'Exception', append 'Under Exception' to IVM Remarks")
        
        return merged_df, updated_count
        
    except Exception as e:
        logging.error(f"Error in update_exception_records: {str(e)}")
        raise


def update_vulnerability_category(merged_df):
    """
    Update Vulnerability Category column based on Scope Identification and Value Stream values.
    """
    try:
        logging.info("Updating Vulnerability Category based on Scope Identification and Value Stream")
        
        # Ensure Vulnerability Category column exists
        if 'Vulnerability Category' not in merged_df.columns:
            merged_df['Vulnerability Category'] = ''
            logging.info("Created 'Vulnerability Category' column")
        
        # Check if required columns exist - handle both Value stream variations
        if 'Scope Identification' not in merged_df.columns:
            logging.warning("'Scope Identification' column not found. Cannot apply Scope-based rules")
        
        # Check for both possible Value Stream column names
        value_stream_col = None
        if 'Value Stream' in merged_df.columns:
            value_stream_col = 'Value Stream'
        elif 'Value stream' in merged_df.columns:
            value_stream_col = 'Value stream'
        else:
            logging.warning("Neither 'Value Stream' nor 'Value stream' column found. Cannot apply Value Stream-based rules")
        
        os_level_count = 0
        non_os_level_count = 0
        not_set_count = 0
        
        # Apply Vulnerability Category logic
        for idx, row in merged_df.iterrows():
            scope_identification = str(row.get('Scope Identification', '')).strip()
            value_stream = str(row.get(value_stream_col, '')).strip() if value_stream_col else ''
            
            # Priority Rule: If Value Stream is "Mey Diageo" - highest priority
            if value_stream == "Mey Diageo":
                merged_df.at[idx, 'Vulnerability Category'] = '-Not Set-'
                not_set_count += 1
            
            # Rule 1: If Scope Identification is "In Scope - BAU"
            elif scope_identification == "In Scope - BAU":
                merged_df.at[idx, 'Vulnerability Category'] = 'OS Level'
                os_level_count += 1
            
            # Rule 2: If Scope Identification is "App Dependency"
            elif scope_identification == "App Dependency":
                merged_df.at[idx, 'Vulnerability Category'] = 'NON-OS Level'
                non_os_level_count += 1
            
            # Rule 3: If Scope Identification is "Scope - Others"
            elif scope_identification == "Scope - Others":
                merged_df.at[idx, 'Vulnerability Category'] = 'NON-OS Level'
                non_os_level_count += 1
            
            # Rule 4: If Scope Identification is "Application Dependent"
            elif scope_identification == "Application Dependent":
                merged_df.at[idx, 'Vulnerability Category'] = 'NON-OS Level'
                non_os_level_count += 1

            # Rule 5: If Scope Identification is "out-of-scope"
            elif scope_identification == "out-of-scope":
                merged_df.at[idx, 'Vulnerability Category'] = 'NON-OS Level'
                non_os_level_count += 1
            
            # Rule 6: If Scope Identification is blank or empty
            elif scope_identification == '' or scope_identification == 'nan':
                merged_df.at[idx, 'Vulnerability Category'] = 'NON-OS Level'
                non_os_level_count += 1
            
            # SPACE FOR 3 ADDITIONAL CONDITIONS - TO BE ADDED LATER
            # Rule 7: [CONDITION TO BE ADDED]
            # elif scope_identification == "[YOUR_CONDITION]":
            #     merged_df.at[idx, 'Vulnerability Category'] = '[YOUR_VALUE]'
            #     [appropriate_counter] += 1
            
            # Rule 8: [CONDITION TO BE ADDED]
            # elif scope_identification == "[YOUR_CONDITION]":
            #     merged_df.at[idx, 'Vulnerability Category'] = '[YOUR_VALUE]'
            #     [appropriate_counter] += 1
            
            # Rule 9: [CONDITION TO BE ADDED]
            # elif scope_identification == "[YOUR_CONDITION]":
            #     merged_df.at[idx, 'Vulnerability Category'] = '[YOUR_VALUE]'
            #     [appropriate_counter] += 1
        
        logging.info(f"Vulnerability Category updates completed:")
        logging.info(f"  - Set to 'OS Level': {os_level_count} records")
        logging.info(f"  - Set to 'NON-OS Level': {non_os_level_count} records")
        logging.info(f"  - Set to '-Not Set-' (Mey Diageo): {not_set_count} records")
        
        return merged_df, os_level_count, non_os_level_count, not_set_count
        
    except Exception as e:
        logging.error(f"Error in update_vulnerability_category: {str(e)}")
        raise


def update_blank_status_ivm(merged_df):
    """
    Update records where Status (IVM) is blank:
    - Set Status (IVM) to 'Open'
    - Set IVM Remarks to 'Open Vuln'
    """
    try:
        logging.info("Updating blank Status (IVM) records")
        
        # Ensure required columns exist
        if 'Status (IVM)' not in merged_df.columns:
            merged_df['Status (IVM)'] = ''
            logging.info("Created 'Status (IVM)' column")
        
        if 'IVM Remarks' not in merged_df.columns:
            merged_df['IVM Remarks'] = ''
            logging.info("Created 'IVM Remarks' column")
        
        updated_count = 0
        
        # Process each row
        for idx, row in merged_df.iterrows():
            status_ivm = str(row.get('Status (IVM)', '')).strip()
            
            # Check if Status (IVM) is blank, empty, or NaN
            if not status_ivm or status_ivm == '' or status_ivm.lower() in ['nan', 'none']:
                merged_df.at[idx, 'Status (IVM)'] = 'Open'
                merged_df.at[idx, 'IVM Remarks'] = 'Open Vuln'
                updated_count += 1
        
        logging.info(f"Status (IVM) updates completed:")
        logging.info(f"  - Updated blank Status (IVM) records: {updated_count}")
        logging.info(f"  - Set Status (IVM) to: 'Open'")
        logging.info(f"  - Set IVM Remarks to: 'Open Vuln'")
        
        return merged_df, updated_count
        
    except Exception as e:
        logging.error(f"Error in update_blank_status_ivm: {str(e)}")
        raise


def apply_vulnerability_category_rules(merged_df):
    """
    Apply additional business rules based on Vulnerability Category values.
    """
    try:
        logging.info("Applying additional rules based on Vulnerability Category")
        
        # Ensure required columns exist
        required_columns = ['Scope Identification', 'Sub Value Stream', 'Vulnerability Ownership', 'Attributes']
        for col in required_columns:
            if col not in merged_df.columns:
                merged_df[col] = ''
                logging.info(f"Created '{col}' column")
        
        # Handle both Value Stream column variations
        value_stream_col = None
        if 'Value Stream' in merged_df.columns:
            value_stream_col = 'Value Stream'
        elif 'Value stream' in merged_df.columns:
            value_stream_col = 'Value stream'
        else:
            merged_df['Value Stream'] = ''  # Create if neither exists
            value_stream_col = 'Value Stream'
            logging.info("Created 'Value Stream' column")
        
        not_set_updates = 0
        os_level_updates = 0
        azure_ownership_updates = 0
        on_premises_ownership_updates = 0
        
        # Apply rules based on Vulnerability Category
        for idx, row in merged_df.iterrows():
            vulnerability_category = str(row.get('Vulnerability Category', '')).strip()
            attributes = str(row.get('Attributes', '')).strip()
            
            # Rule 1: If Vulnerability Category is "-Not Set-"
            if vulnerability_category == "-Not Set-":
                merged_df.at[idx, 'Scope Identification'] = 'Scope - Others'
                merged_df.at[idx, value_stream_col] = 'Mey Diageo'
                merged_df.at[idx, 'Sub Value Stream'] = 'Mey Diageo'
                merged_df.at[idx, 'Vulnerability Ownership'] = 'Mey Icki'
                not_set_updates += 1
            
            # Rule 2: If Vulnerability Category is "OS Level"
            elif vulnerability_category == "OS Level":
                merged_df.at[idx, value_stream_col] = 'Enterprise Services'
                merged_df.at[idx, 'Sub Value Stream'] = 'Azure, Compute & EUC'
                os_level_updates += 1
                
                # Sub-rule: Check Attributes for Vulnerability Ownership
                if attributes in ["Azure-Non-Datalake/Analytics", "Azure", "Azure-Datalake/Analytics"]:
                    merged_df.at[idx, 'Vulnerability Ownership'] = 'RUN Compute Azure'
                    azure_ownership_updates += 1
                else:
                    merged_df.at[idx, 'Vulnerability Ownership'] = 'RUN Compute On-premises'
                    on_premises_ownership_updates += 1
        
        logging.info(f"Vulnerability Category rules completed:")
        logging.info(f"  - Updated '-Not Set-' records: {not_set_updates}")
        logging.info(f"  - Updated 'OS Level' records: {os_level_updates}")
        logging.info(f"  - Set 'RUN Compute Azure' ownership: {azure_ownership_updates}")
        logging.info(f"  - Set 'RUN Compute On-premises' ownership: {on_premises_ownership_updates}")
        
        return merged_df, not_set_updates, os_level_updates, azure_ownership_updates, on_premises_ownership_updates
        
    except Exception as e:
        logging.error(f"Error in apply_vulnerability_category_rules: {str(e)}")
        raise


def update_non_os_level_ownership(merged_df):
    """
    Update Vulnerability Ownership for NON-OS Level categories based on 
    specific Value Stream and Sub Value Stream combinations.
    FIXED: Handles both 'Value Stream' and 'Value stream' column variations.
    """
    try:
        logging.info("Updating Vulnerability Ownership for NON-OS Level categories")
        
        # Ensure required columns exist
        required_columns = ['Vulnerability Category', 'Sub Value Stream', 'Vulnerability Ownership']
        for col in required_columns:
            if col not in merged_df.columns:
                merged_df[col] = ''
                logging.info(f"Created '{col}' column")
        
        # Handle both Value Stream column variations - CRITICAL FIX
        value_stream_col = None
        if 'Value stream' in merged_df.columns:  # Check lowercase first (this has the data)
            value_stream_col = 'Value stream'
        elif 'Value Stream' in merged_df.columns:  # Check uppercase second
            value_stream_col = 'Value Stream'
        else:
            logging.warning("Neither 'Value stream' nor 'Value Stream' column found")
            return merged_df, {}, 0
        
        logging.info(f"Using '{value_stream_col}' column for Value Stream data")
        
        # Initialize counters for each ownership type
        ownership_counts = {
            'RUN Consumer': 0, 'Others': 0, 'RUN E2E Planning': 0, 'RUN Corporate Functions': 0,
            'Technology Experience': 0, 'RUN People': 0, 'RUN Customer': 0, 'A and I': 0,
            'Technology Foundations': 0, 'IM&S': 0, 'RUN Employee Workplace': 0, 'RUN IDAM': 0,
            'RUN Network and DataCentre': 0, 'RUN OpEx': 0, 'Transform': 0, 'RUN SAP Ops': 0,
            'RUN Supply': 0, 'Ignore-Legacy': 0, 'Ignore-Old': 0  # Added for tracking
        }
        
        # Clean and normalize data first
        merged_df['Vulnerability Category'] = merged_df['Vulnerability Category'].astype(str).str.strip()
        merged_df[value_stream_col] = merged_df[value_stream_col].astype(str).str.strip()
        merged_df['Sub Value Stream'] = merged_df['Sub Value Stream'].astype(str).str.strip()
        
        # Apply ownership rules using iterrows for better debugging
        for idx, row in merged_df.iterrows():
            vuln_category = str(row.get('Vulnerability Category', '')).strip()
            value_stream = str(row.get(value_stream_col, '')).strip()
            sub_value_stream = str(row.get('Sub Value Stream', '')).strip()
            
            # Only process NON-OS Level records (handle both variants)
            if vuln_category in ['NON-OS Level', 'Non-OS Level']:
                ownership = None
                
                # MarTech rules
                if value_stream == 'MarTech':
                    if sub_value_stream == 'MarTech':
                        ownership = 'RUN Consumer'
                    elif sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # Corporate Functions rules
                elif value_stream == 'Corporate Functions':
                    if sub_value_stream == 'E2E Planning':
                        ownership = 'RUN E2E Planning'
                    elif sub_value_stream == 'Finance':
                        ownership = 'RUN Corporate Functions'
                    elif sub_value_stream == 'Legal & CR':
                        ownership = 'Technology Experience'
                    elif sub_value_stream == 'People':
                        ownership = 'RUN People'
                    elif sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # Customer rules
                elif value_stream == 'Customer':
                    if sub_value_stream == 'Customer':
                        ownership = 'RUN Customer'
                    elif sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # Data Analytics & Insights rules - CRITICAL FIX
                elif value_stream == 'Data Analytics & Insights':
                    if sub_value_stream in [
                        'Global Data Platforms, Engineering and Operations',
                        'DA&I Product Management Team', 
                        'DA&I Data Management & DDH',
                        'Global Data Products & Analytics',
                        'DA&I Regional Team',
                        'DA&I Strategy, Innovation and Transformation',
                        'Finance'
                    ]:
                        ownership = 'A and I'
                    elif sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # Digital Foundations rules
                elif value_stream == 'Digital Foundations':
                    if sub_value_stream == 'SAS-TBD':
                        ownership = 'Others'
                    elif sub_value_stream == 'Digital Foundations':
                        ownership = 'Technology Foundations'
                
                # Enterprise Services-IM&S rules
                elif value_stream == 'Enterprise Services-IM&S':
                    if sub_value_stream == 'IM&S':
                        ownership = 'IM&S'
                    elif sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # Enterprise Services rules
                elif value_stream == 'Enterprise Services':
                    if sub_value_stream == 'Azure, Compute & EUC':
                        ownership = 'RUN Employee Workplace'
                    elif sub_value_stream == 'Finance':
                        ownership = 'RUN Corporate Functions'
                    elif sub_value_stream == 'IDAM':
                        ownership = 'RUN IDAM'
                    elif sub_value_stream == 'Networks, DC, CRES & UCC':
                        ownership = 'RUN Network and DataCentre'
                    elif sub_value_stream == 'OpEx':
                        ownership = 'RUN OpEx'
                    elif sub_value_stream == 'Technology Engagement':
                        ownership = 'Transform'
                    elif sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # SAP rules
                elif value_stream == 'SAP':
                    if sub_value_stream in ['SAP BAU', 'SAP Voyager']:
                        ownership = 'RUN SAP Ops'
                    elif sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # Supply rules
                elif value_stream == 'Supply':
                    if sub_value_stream == 'Supply':
                        ownership = 'RUN Supply'
                    elif sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # VS-TBD rules
                elif value_stream == 'VS-TBD':
                    if sub_value_stream == 'SVS-TBD':
                        ownership = 'Others'
                
                # SPACE FOR ADDITIONAL VALUE STREAM RULES - TO BE ADDED LATER
                # elif value_stream == '[NEW_VALUE_STREAM]':
                #     if sub_value_stream == '[CONDITION]':
                #         ownership = '[OWNERSHIP_VALUE]'
                #     elif sub_value_stream == 'SVS-TBD':
                #         ownership = 'Others'
                
                # Apply ownership if determined
                if ownership:
                    merged_df.at[idx, 'Vulnerability Ownership'] = ownership
                    ownership_counts[ownership] += 1
                    logging.debug(f"Row {idx}: {value_stream} + {sub_value_stream} → {ownership}")
        
        total_updates = sum(ownership_counts.values())
        
        logging.info(f"NON-OS Level ownership updates completed:")
        logging.info(f"  - Total records updated: {total_updates}")
        for ownership, count in ownership_counts.items():
            if count > 0:
                logging.info(f"  - {ownership}: {count} records")
        
        return merged_df, ownership_counts, total_updates
        
    except Exception as e:
        logging.error(f"Error in update_non_os_level_ownership: {str(e)}")
        raise


def standardize_column_values(merged_df):
    """
    Standardize and clean up values in multiple columns according to business rules.
    
    Rules:
    Classification:
    - "Pre Production" → "Pre-Production"
    - "Pre-Production" → "Pre-Production" (already correct)
    - "Pre - Production" → "Pre-Production"
    - "Staging" → "TBD"
    - Blank/Empty → "-Not Set-"
    
    Exploitation Criteria:
    - Blank/Empty → "-Not Set-"
    
    Class:
    - Blank/Empty → "-Not Set-"
    
    Server Tier:
    - "Production" → "-Not Set-"
    - Blank/Empty → "-Not Set-"
    
    Status (Server Owner):
    - Blank/Empty → "-Not Set-"
    """
    try:
        logging.info("Standardizing column values according to business rules")
        
        # Define columns to process
        columns_to_process = [
            'Classification', 'Exploitation Criteria', 'Class', 
            'Server Tier', 'Status (Server Owner)'
        ]
        
        # Ensure all required columns exist
        for col in columns_to_process:
            if col not in merged_df.columns:
                merged_df[col] = ''
                logging.info(f"Created '{col}' column")
        
        # Initialize counters for each column
        counters = {
            'Classification': {'pre_production_fixed': 0, 'staging_to_tbd': 0, 'blank_to_not_set': 0},
            'Exploitation Criteria': {'blank_to_not_set': 0},
            'Class': {'blank_to_not_set': 0},
            'Server Tier': {'production_to_not_set': 0, 'blank_to_not_set': 0},
            'Status (Server Owner)': {'blank_to_not_set': 0}
        }
        
        # Process each row
        for idx, row in merged_df.iterrows():
            
            # 1. Classification column processing
            classification = str(row.get('Classification', '')).strip()
            if classification in ['Pre Production', 'Pre - Production']:
                merged_df.at[idx, 'Classification'] = 'Pre-Production'
                counters['Classification']['pre_production_fixed'] += 1
            elif classification == 'Staging':
                merged_df.at[idx, 'Classification'] = 'TBD'
                counters['Classification']['staging_to_tbd'] += 1
            elif not classification or classification == '' or classification.lower() in ['nan', 'none', 'null']:
                merged_df.at[idx, 'Classification'] = '-Not Set-'
                counters['Classification']['blank_to_not_set'] += 1
            
            # 2. Exploitation Criteria column processing
            exploitation_criteria = str(row.get('Exploitation Criteria', '')).strip()
            if not exploitation_criteria or exploitation_criteria == '' or exploitation_criteria.lower() in ['nan', 'none', 'null']:
                merged_df.at[idx, 'Exploitation Criteria'] = '-Not Set-'
                counters['Exploitation Criteria']['blank_to_not_set'] += 1
            
            # 3. Class column processing
            class_value = str(row.get('Class', '')).strip()
            if not class_value or class_value == '' or class_value.lower() in ['nan', 'none', 'null']:
                merged_df.at[idx, 'Class'] = '-Not Set-'
                counters['Class']['blank_to_not_set'] += 1
            
            # 4. Server Tier column processing
            server_tier = str(row.get('Server Tier', '')).strip()
            if server_tier == 'Production':
                merged_df.at[idx, 'Server Tier'] = '-Not Set-'
                counters['Server Tier']['production_to_not_set'] += 1
            elif not server_tier or server_tier == '' or server_tier.lower() in ['nan', 'none', 'null']:
                merged_df.at[idx, 'Server Tier'] = '-Not Set-'
                counters['Server Tier']['blank_to_not_set'] += 1
            
            # 5. Status (Server Owner) column processing
            status_server_owner = str(row.get('Status (Server Owner)', '')).strip()
            if not status_server_owner or status_server_owner == '' or status_server_owner.lower() in ['nan', 'none', 'null']:
                merged_df.at[idx, 'Status (Server Owner)'] = '-Not Set-'
                counters['Status (Server Owner)']['blank_to_not_set'] += 1
        
        # Log results
        logging.info(f"Column standardization completed:")
        logging.info(f"Classification updates:")
        logging.info(f"  - Pre-Production variants fixed: {counters['Classification']['pre_production_fixed']} records")
        logging.info(f"  - Staging → TBD: {counters['Classification']['staging_to_tbd']} records")
        logging.info(f"  - Blank → -Not Set-: {counters['Classification']['blank_to_not_set']} records")
        
        logging.info(f"Exploitation Criteria updates:")
        logging.info(f"  - Blank → -Not Set-: {counters['Exploitation Criteria']['blank_to_not_set']} records")
        
        logging.info(f"Class updates:")
        logging.info(f"  - Blank → -Not Set-: {counters['Class']['blank_to_not_set']} records")
        
        logging.info(f"Server Tier updates:")
        logging.info(f"  - Production → -Not Set-: {counters['Server Tier']['production_to_not_set']} records")
        logging.info(f"  - Blank → -Not Set-: {counters['Server Tier']['blank_to_not_set']} records")
        
        logging.info(f"Status (Server Owner) updates:")
        logging.info(f"  - Blank → -Not Set-: {counters['Status (Server Owner)']['blank_to_not_set']} records")
        
        return merged_df, counters
        
    except Exception as e:
        logging.error(f"Error in standardize_column_values: {str(e)}")
        raise


def update_vm_status_based_on_vuln_status(merged_df):
    """
    Update VM Status based on ID and Vuln Status combinations.
    
    Rules:
    - If ID is blank/empty and Vuln Status is "Active" → VM Status = "Active"
    - If ID is blank/empty and Vuln Status is "New" → VM Status = "Re-Opened"
    - If ID is blank/empty and Vuln Status is "Re-Opened" → VM Status = "Re-Opened"
    """
    try:
        logging.info("Updating VM Status based on ID and Vuln Status conditions")
        
        # Ensure required columns exist
        required_columns = ['ID', 'Vuln Status', 'VM Status']
        for col in required_columns:
            if col not in merged_df.columns:
                merged_df[col] = ''
                logging.info(f"Created '{col}' column")
        
        # Initialize counters
        active_count = 0
        reopened_count = 0
        
        # Process each row
        for idx, row in merged_df.iterrows():
            id_value = str(row.get('ID', '')).strip()
            vuln_status = str(row.get('Vuln Status', '')).strip()
            
            # Check if ID is blank/empty
            if not id_value or id_value == '' or id_value.lower() in ['nan', 'none', 'null']:
                
                # Rule 1: If Vuln Status is "Active" → VM Status = "Active"
                if vuln_status == "Active":
                    merged_df.at[idx, 'VM Status'] = 'Active'
                    active_count += 1
                    logging.debug(f"Row {idx}: Set VM Status to 'Active' (ID blank + Vuln Status 'Active')")
                
                # Rule 2: If Vuln Status is "New" → VM Status = "Re-Opened"
                elif vuln_status == "New":
                    merged_df.at[idx, 'VM Status'] = 'Re-Opened'
                    reopened_count += 1
                    logging.debug(f"Row {idx}: Set VM Status to 'Re-Opened' (ID blank + Vuln Status 'New')")
                
                # Rule 3: If Vuln Status is "Re-Opened" → VM Status = "Re-Opened"
                elif vuln_status == "Re-Opened":
                    merged_df.at[idx, 'VM Status'] = 'Re-Opened'
                    reopened_count += 1
                    logging.debug(f"Row {idx}: Set VM Status to 'Re-Opened' (ID blank + Vuln Status 'Re-Opened')")
        
        logging.info(f"VM Status updates based on ID and Vuln Status completed:")
        logging.info(f"  - Set VM Status to 'Active': {active_count} records")
        logging.info(f"  - Set VM Status to 'Re-Opened': {reopened_count} records")
        logging.info(f"  - Rule 1: ID blank + Vuln Status 'Active' → VM Status 'Active'")
        logging.info(f"  - Rule 2: ID blank + Vuln Status 'New' → VM Status 'Re-Opened'")
        logging.info(f"  - Rule 3: ID blank + Vuln Status 'Re-Opened' → VM Status 'Re-Opened'")
        
        return merged_df, active_count, reopened_count
        
    except Exception as e:
        logging.error(f"Error in update_vm_status_based_on_vuln_status: {str(e)}")
        raise


def update_vuln_status_and_install_status_rules(merged_df):
    """
    Update records based on Vuln Status and Install Status:
    1. If Vuln Status is "Fixed" → Update Status (IVM), RAG, IVM Remarks, Actual Mitigation Date
    2. If Install Status is "decommissioned"/"decomissioned" → Update Status (IVM), RAG, IVM Remarks, VM Status, Actual Mitigation Date
    """
    try:
        logging.info("Updating records based on Vuln Status and Install Status rules")
        
        # Ensure required columns exist
        required_columns = ['Vuln Status', 'Install Status', 'Status (IVM)', 'RAG', 'IVM Remarks', 'VM Status', 'Actual Mitigation Date']
        for col in required_columns:
            if col not in merged_df.columns:
                merged_df[col] = ''
                logging.info(f"Created '{col}' column")
        
        # Get today's date in dd/mm/yyyy format
        today_str = datetime.datetime.now().strftime("%d/%m/%Y")
        
        fixed_count = 0
        decommissioned_count = 0
        
        # Process each row
        for idx, row in merged_df.iterrows():
            vuln_status = str(row.get('Vuln Status', '')).strip()
            install_status = str(row.get('Install Status', '')).strip()
            existing_remarks = str(row.get('IVM Remarks', '')).strip()
            
            # Rule 1: If Vuln Status is "Fixed"
            if vuln_status.lower() == 'fixed':
                merged_df.at[idx, 'Status (IVM)'] = 'Closed'
                merged_df.at[idx, 'RAG'] = '-Not Set-'
                merged_df.at[idx, 'Actual Mitigation Date'] = today_str
                
                # Append to IVM Remarks
                append_text = 'Closed due to vulnerability fix'
                if existing_remarks and existing_remarks.lower() not in ['', 'nan', 'none']:
                    if append_text not in existing_remarks:
                        new_remarks = existing_remarks + ', ' + append_text
                        merged_df.at[idx, 'IVM Remarks'] = new_remarks
                else:
                    merged_df.at[idx, 'IVM Remarks'] = append_text
                
                fixed_count += 1
                logging.debug(f"Row {idx}: Updated for Fixed Vuln Status")
            
            # Rule 2: If Install Status is decommissioned (handle variants)
            elif install_status.lower() in ['decommissioned', 'decomissioned']:
                merged_df.at[idx, 'Status (IVM)'] = 'Closed'
                merged_df.at[idx, 'RAG'] = '-Not Set-'
                merged_df.at[idx, 'VM Status'] = 'Decommissioned'
                merged_df.at[idx, 'Actual Mitigation Date'] = today_str
                
                # Append to IVM Remarks
                append_text = 'Closed due to decommissioned'
                if existing_remarks and existing_remarks.lower() not in ['', 'nan', 'none']:
                    if append_text not in existing_remarks:
                        new_remarks = existing_remarks + ', ' + append_text
                        merged_df.at[idx, 'IVM Remarks'] = new_remarks
                else:
                    merged_df.at[idx, 'IVM Remarks'] = append_text
                
                decommissioned_count += 1
                logging.debug(f"Row {idx}: Updated for Decommissioned Install Status")
        
        logging.info(f"Vuln Status and Install Status updates completed:")
        logging.info(f"  - Fixed vulnerabilities updated: {fixed_count} records")
        logging.info(f"  - Decommissioned install status updated: {decommissioned_count} records")
        logging.info(f"  - Rule 1: Vuln Status = 'Fixed' → Status(IVM)='Closed', RAG='-Not Set-', append IVM Remarks, set Actual Mitigation Date")
        logging.info(f"  - Rule 2: Install Status = 'decommissioned'/'decomissioned' → Status(IVM)='Closed', RAG='-Not Set-', VM Status='Decommissioned', append IVM Remarks, set Actual Mitigation Date")
        
        return merged_df, fixed_count, decommissioned_count
        
    except Exception as e:
        logging.error(f"Error in update_vuln_status_and_install_status_rules: {str(e)}")
        raise


def update_legacy_non_exploitable_ownership(merged_df):
    """
    Update Vulnerability Ownership for Legacy vulnerabilities where QID CTI is "Vulnerability Normal" or blank.
    Rule: If Vulnerability Class is "Legacy" and QID CTI is "Vulnerability Normal" or blank/empty
    → Set Vulnerability Ownership to "Ignore-Legacy"
    """
    try:
        logging.info("Updating ownership for Legacy vulnerabilities with Vulnerability Normal or blank QID CTI")
        
        # Ensure required columns exist
        if 'Vulnerability Class' not in merged_df.columns:
            merged_df['Vulnerability Class'] = ''
            logging.info("Created 'Vulnerability Class' column")
        
        if 'QID CTI' not in merged_df.columns:
            merged_df['QID CTI'] = ''
            logging.info("Created 'QID CTI' column")
        
        if 'Vulnerability Ownership' not in merged_df.columns:
            merged_df['Vulnerability Ownership'] = ''
            logging.info("Created 'Vulnerability Ownership' column")
        
        updated_count = 0
        
        # Process each row
        for idx, row in merged_df.iterrows():
            vuln_class = str(row.get('Vulnerability Class', '')).strip()
            qid_cti = str(row.get('QID CTI', '')).strip()
            
            # Check if Legacy and QID CTI is "Vulnerability Normal" or blank/empty
            if vuln_class == 'Legacy' and (qid_cti == 'Normal Vulnerability' or qid_cti == '' or qid_cti.lower() in ['nan', 'none', 'null']):
                merged_df.at[idx, 'Vulnerability Ownership'] = 'Ignore-Legacy'
                updated_count += 1
        
        logging.info(f"Legacy non-exploitable ownership updates completed:")
        logging.info(f"  - Updated to 'Ignore-Legacy': {updated_count} records")
        logging.info(f"  - Rule: Legacy + (QID CTI = 'Vulnerability Normal' OR blank/empty) → 'Ignore-Legacy'")
        
        return merged_df, updated_count
        
    except Exception as e:
        logging.error(f"Error in update_legacy_non_exploitable_ownership: {str(e)}")
        raise


def update_ownership_for_decommissioned_and_closed(merged_df):
    """
    Update Vulnerability Ownership to 'Ignore-Old' and append VM Status to IVM Remarks.
    FIXED: Handles spelling variations, comprehensive substring matching, and proper appending.
    """
    try:
        logging.info("Updating ownership for Decommissioned VMs and Closed vulnerabilities")
        
        # Ensure required columns exist
        if 'VM Status' not in merged_df.columns:
            merged_df['VM Status'] = ''
            logging.info("Created 'VM Status' column")
        
        if 'IVM Remarks' not in merged_df.columns:
            merged_df['IVM Remarks'] = ''
            logging.info("Created 'IVM Remarks' column")
        
        if 'Vulnerability Ownership' not in merged_df.columns:
            merged_df['Vulnerability Ownership'] = ''
            logging.info("Created 'Vulnerability Ownership' column")
        
        updated_ownership_count = 0
        updated_remarks_count = 0
        
        # Process each row
        for idx, row in merged_df.iterrows():
            vm_status = str(row.get('VM Status', '')).strip()
            ivm_remarks = str(row.get('IVM Remarks', '')).strip()
            
            # Append VM Status to IVM Remarks (without losing existing values)
            if vm_status and vm_status.lower() not in ['', 'nan', 'none']:
                if ivm_remarks and ivm_remarks.lower() not in ['', 'nan', 'none']:
                    # Check if VM Status is not already in IVM Remarks to avoid duplicates
                    if vm_status not in ivm_remarks:
                        new_remarks = ivm_remarks + ', ' + vm_status
                        merged_df.at[idx, 'IVM Remarks'] = new_remarks
                        updated_remarks_count += 1
                else:
                    # IVM Remarks is empty, just set VM Status
                    merged_df.at[idx, 'IVM Remarks'] = vm_status
                    updated_remarks_count += 1
            
            # Update Vulnerability Ownership - COMPREHENSIVE CONDITIONS
            current_ivm_remarks = str(merged_df.at[idx, 'IVM Remarks']).strip().lower()
            vm_status_lower = vm_status.lower()
            
            # Check for VM Status conditions (handle both spellings)
            vm_decommissioned = (vm_status_lower == 'decommissioned' or 
                               vm_status_lower == 'decomissioned' or
                               'decomissioned' in vm_status_lower or
                               'decommissioned' in vm_status_lower)
            
            # Check for IVM Remarks conditions (comprehensive substring matching)
            ivm_closed = ('closed due to vulnerability fixed' in current_ivm_remarks or
                         'closed due to vulnerability got fixed' in current_ivm_remarks or
                         'closed due to decommission' in current_ivm_remarks or
                         'closed due to vulnerability' in current_ivm_remarks)
            
            if vm_decommissioned or ivm_closed:
                merged_df.at[idx, 'Vulnerability Ownership'] = 'Ignore-Old'
                updated_ownership_count += 1
                logging.debug(f"Row {idx}: Set Ignore-Old due to VM={vm_status_lower}, IVM={current_ivm_remarks[:50]}...")
        
        logging.info(f"Decommissioned/Closed updates completed:")
        logging.info(f"  - Updated Vulnerability Ownership to 'Ignore-Old': {updated_ownership_count} records")
        logging.info(f"  - Appended VM Status to IVM Remarks: {updated_remarks_count} records")
        logging.info(f"  - Rule 1: VM Status contains 'decomissioned'/'decommissioned' → 'Ignore-Old'")
        logging.info(f"  - Rule 2: IVM Remarks contains 'closed due to vulnerability fixed' → 'Ignore-Old'")
        logging.info(f"  - Rule 3: IVM Remarks contains 'closed due to vulnerability got fixed' → 'Ignore-Old'")
        logging.info(f"  - Rule 4: IVM Remarks contains 'closed due to decommission' → 'Ignore-Old'")
        
        return merged_df, updated_ownership_count, updated_remarks_count
        
    except Exception as e:
        logging.error(f"Error in update_ownership_for_decommissioned_and_closed: {str(e)}")
        raise


def update_column_names_server_to_cmdb(merged_df):
    """
    Update column names to maintain consistency:
    - 'Server' → 'Server Name not matching'
    - 'CMDB Host Name' → 'Server'
    """
    try:
        logging.info("Updating column names: Server → Server Name not matching, CMDB Host Name → Server")
        
        # Create a mapping of old column names to new column names
        column_rename_mapping = {}
        
        # Check if columns exist and prepare renaming
        if 'Server' in merged_df.columns:
            column_rename_mapping['Server'] = 'Server Name not matching'
            logging.info("Found 'Server' column - will rename to 'Server Name not matching'")
        
        if 'CMDB Host Name' in merged_df.columns:
            column_rename_mapping['CMDB Host Name'] = 'Server'
            logging.info("Found 'CMDB Host Name' column - will rename to 'Server'")
        
        # Apply the column renaming
        if column_rename_mapping:
            merged_df = merged_df.rename(columns=column_rename_mapping)
            logging.info(f"Successfully renamed {len(column_rename_mapping)} columns")
        else:
            logging.info("No matching columns found for renaming")
        
        # Log the changes made
        for old_name, new_name in column_rename_mapping.items():
            logging.info(f"  - '{old_name}' → '{new_name}'")
        
        return merged_df, len(column_rename_mapping)
        
    except Exception as e:
        logging.error(f"Error in update_column_names_server_to_cmdb: {str(e)}")
        raise


def update_rescan_date_column(merged_df):
    """
    Update Rescan Date column with today's date in dd/mm/yyyy format.
    Overrides any existing values in the column.
    """
    try:
        logging.info("Updating Rescan Date column with today's date")
        
        # Get today's date in dd/mm/yyyy format
        today_str = datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Ensure Rescan Date column exists
        if 'Rescan Date' not in merged_df.columns:
            merged_df['Rescan Date'] = ''
            logging.info("Created 'Rescan Date' column")
        
        # Update all rows with today's date (override existing values)
        merged_df['Rescan Date'] = today_str
        
        logging.info(f"Updated Rescan Date column:")
        logging.info(f"  - Set all {len(merged_df)} records to: {today_str}")
        
        return merged_df, today_str
        
    except Exception as e:
        logging.error(f"Error in update_rescan_date_column: {str(e)}")
        raise


def update_actual_mitigation_date_based_on_status_ivm(df):
    """
    Update Actual Mitigation Date based on Status (IVM) values:
    - If Status (IVM) is 'Closed': Update today's date only for records with '01/01/2000' value
    - If Status (IVM) is 'Open' or 'Exception': Update to '01/01/2000'
    """
    try:
        logging.info("Updating Actual Mitigation Date based on Status (IVM)")
        
        # Get today's date in dd/mm/yyyy format
        today_str = datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Ensure the required columns exist
        if 'Status (IVM)' not in df.columns:
            logging.warning("'Status (IVM)' column not found - creating empty column")
            df['Status (IVM)'] = ''
            
        if 'Actual Mitigation Date' not in df.columns:
            logging.info("Creating 'Actual Mitigation Date' column")
            df['Actual Mitigation Date'] = ''
        
        # Convert to string and clean up values
        df['Status (IVM)'] = df['Status (IVM)'].astype(str).str.strip()
        df['Actual Mitigation Date'] = df['Actual Mitigation Date'].astype(str).str.strip()
        
        # Track updates
        closed_updated_count = 0
        open_exception_updated_count = 0
        
        # Rule 1: If Status (IVM) is 'Closed', update today's date ONLY for '01/01/2000' values
        closed_mask = (df['Status (IVM)'].str.lower() == 'closed') & \
                     (df['Actual Mitigation Date'] == '01/01/2000')
        
        if closed_mask.any():
            df.loc[closed_mask, 'Actual Mitigation Date'] = today_str
            closed_updated_count = closed_mask.sum()
            logging.info(f"Updated {closed_updated_count} 'Closed' records with today's date ({today_str})")
        
        # Rule 2: If Status (IVM) is 'Open' or 'Exception', update to '01/01/2000'
        open_exception_mask = (df['Status (IVM)'].str.lower().isin(['open', 'exception']))
        
        if open_exception_mask.any():
            df.loc[open_exception_mask, 'Actual Mitigation Date'] = '01/01/2000'
            open_exception_updated_count = open_exception_mask.sum()
            logging.info(f"Updated {open_exception_updated_count} 'Open/Exception' records with '01/01/2000'")
        
        total_updated = closed_updated_count + open_exception_updated_count
        
        logging.info(f"Actual Mitigation Date update completed:")
        logging.info(f"  - Closed records (01/01/2000 -> today): {closed_updated_count}")
        logging.info(f"  - Open/Exception records (-> 01/01/2000): {open_exception_updated_count}")
        logging.info(f"  - Total records updated: {total_updated}")
        
        return df, closed_updated_count, open_exception_updated_count
        
    except Exception as e:
        logging.error(f"Error in update_actual_mitigation_date_based_on_status_ivm: {str(e)}")
        raise


def apply_final_os_level_updates(merged_df):
    """
    FINAL UPDATE STEP: Apply OS Level specific updates with highest priority.
    This should be called as the last step before Excel generation.
    
    Rules:
    1. If Vulnerability Category is "OS Level" → Set Sub Value Stream = "Azure, Compute & EUC"
    2. If Vulnerability Category is "OS Level" → Set Value stream = "Enterprise Services" 
    3. If Vulnerability Category is "OS Level" AND Attributes = "Azure" → Set Vulnerability Ownership = "RUN Compute Azure"
    4. If Vulnerability Category is "OS Level" AND Attributes = "On-Prem" → Set Vulnerability Ownership = "RUN Compute On-premises"
    """
    try:
        logging.info("Applying final OS Level updates (HIGHEST PRIORITY)")
        
        # Ensure required columns exist
        required_columns = ['Vulnerability Category', 'Attributes', 'Sub Value Stream', 'Vulnerability Ownership']
        for col in required_columns:
            if col not in merged_df.columns:
                merged_df[col] = ''
                logging.info(f"Created '{col}' column")
        
        # Handle both Value Stream column variations
        value_stream_col = None
        if 'Value stream' in merged_df.columns:
            value_stream_col = 'Value stream'
        elif 'Value Stream' in merged_df.columns:
            value_stream_col = 'Value Stream'
        else:
            merged_df['Value stream'] = ''
            value_stream_col = 'Value stream'
            logging.info("Created 'Value stream' column")
        
        # Initialize counters
        updated_sub_value_stream = 0
        updated_value_stream = 0
        updated_azure_ownership = 0
        updated_onprem_ownership = 0
        
        # Define attribute mappings
        azure_attributes = {'azure', 'azure-non-datalake', 'azure-non-datalake analytics', 
                          'azure-non-datalake/analytics', 'azure-datalake/analytics'}
        onprem_attributes = {'on prem', 'on-prem', 'onprem', 'on premises', 'on-premises'}
        
        # Process each row
        for idx, row in merged_df.iterrows():
            vulnerability_category = str(row.get('Vulnerability Category', '')).strip()
            
            # Only process OS Level vulnerabilities
            if vulnerability_category == 'OS Level':
                # Force update Sub Value Stream (always override)
                merged_df.at[idx, 'Sub Value Stream'] = 'Azure, Compute & EUC'
                updated_sub_value_stream += 1
                
                # Force update Value stream (always override)  
                merged_df.at[idx, value_stream_col] = 'Enterprise Services'
                updated_value_stream += 1
                
                # Update Vulnerability Ownership based on Attributes (always override)
                attributes = str(row.get('Attributes', '')).strip().lower()
                
                if attributes in azure_attributes:
                    merged_df.at[idx, 'Vulnerability Ownership'] = 'RUN Compute Azure'
                    updated_azure_ownership += 1
                elif attributes in onprem_attributes:
                    merged_df.at[idx, 'Vulnerability Ownership'] = 'RUN Compute On-premises'
                    updated_onprem_ownership += 1
                # Note: If attributes don't match known values, ownership remains as previously set
        
        logging.info(f"Final OS Level updates completed:")
        logging.info(f"  - Updated Sub Value Stream: {updated_sub_value_stream} records")
        logging.info(f"  - Updated Value stream: {updated_value_stream} records")
        logging.info(f"  - Set Azure ownership: {updated_azure_ownership} records")
        logging.info(f"  - Set On-premises ownership: {updated_onprem_ownership} records")
        logging.info(f"  - FINAL OVERRIDE: These updates take precedence over all previous rules")
        
        return merged_df, updated_sub_value_stream, updated_value_stream, updated_azure_ownership, updated_onprem_ownership
        
    except Exception as e:
        logging.error(f"Error in apply_final_os_level_updates: {str(e)}")
        raise
