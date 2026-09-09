import logging
import json
import time
import datetime
import traceback

import azure.functions as func

from shared_code.process_merged_helpers import (
    convert_numpy_types,
    safe_value_conversion,
    find_best_excel_sheet,
    process_file_content,
    update_new_vulnerabilities_before_merge,
    preprocess_old_columns_before_merge,
    merge_vulnerability_data,
    clean_vulnerability_category_typos,
    normalize_value_streams,
    apply_legacy_classification,
    apply_qid_cti_classification,
    apply_tags_logic,
    rename_scope_identification_values,
    update_exception_records,
    update_vulnerability_category,
    update_blank_status_ivm,
    apply_vulnerability_category_rules,
    update_non_os_level_ownership,
    standardize_column_values,
    update_vm_status_based_on_vuln_status,
    update_vuln_status_and_install_status_rules,
    update_legacy_non_exploitable_ownership,
    update_ownership_for_decommissioned_and_closed,
    update_column_names_server_to_cmdb,
    update_rescan_date_column,
    update_actual_mitigation_date_based_on_status_ivm,
    apply_final_os_level_updates,

)


def main(req: func.HttpRequest) -> func.HttpResponse:
    function_start_time = time.time()
    logging.info('Processing vulnerability data with merge and complete business logic.')

    try:
        # Get request body
        req_body = req.get_json()
        cycle_id = req_body.get('cycleId')

        # Required parameters
        all_vuln_content = req_body.get('allVulnDataContent')
        new_vuln_content = req_body.get('newVulnDataContent')
        qid_content = req_body.get('qidDataContent')
        legacy_content = req_body.get('legacyDataContent')

        # Get optional file type hints
        all_vuln_file_type = req_body.get('allVulnFileType', 'xlsx')
        new_vuln_file_type = req_body.get('newVulnFileType', 'xlsx')
        qid_file_type = req_body.get('qidFileType', 'xlsx')
        legacy_file_type = req_body.get('legacyFileType', 'xlsx')

        # Validate required inputs
        missing_params = []
        if not cycle_id:
            missing_params.append("cycleId")
        if not all_vuln_content:
            missing_params.append("allVulnDataContent")
        if not new_vuln_content:
            missing_params.append("newVulnDataContent")
        if not qid_content:
            missing_params.append("qidDataContent")
        if not legacy_content:
            missing_params.append("legacyDataContent")

        if missing_params:
            return func.HttpResponse(
                f"Missing required parameters: {', '.join(missing_params)}",
                status_code=400
            )

        logging.info(f"Processing vulnerability data for cycle ID: {cycle_id}")

        # Step 1: Process all input files
        logging.info("Step 1: Processing input files...")
        all_vuln_df = process_file_content(all_vuln_content, all_vuln_file_type, "allvuln")
        new_vuln_df = process_file_content(new_vuln_content, new_vuln_file_type, "newvuln")
        qid_df = process_file_content(qid_content, qid_file_type, "qid")
        legacy_df = process_file_content(legacy_content, legacy_file_type, "legacy")

        logging.info(f"Processed all vulnerabilities data: {len(all_vuln_df)} rows")
        logging.info(f"Processed new vulnerabilities data: {len(new_vuln_df)} rows")
        logging.info(f"Processed QID data: {len(qid_df)} rows")
        logging.info(f"Processed Legacy data: {len(legacy_df)} rows")

        # Step 2a: Update new vulnerabilities with current date and RAG
        logging.info("Step 2a: Updating new vulnerabilities with Reported Date and RAG...")
        updated_new_vuln_df = update_new_vulnerabilities_before_merge(new_vuln_df)

        # Step 2b: Preprocess OLD columns BEFORE merge (CORRECTED)
        logging.info("Step 2b: Preprocessing OLD columns before merge...")
        all_vuln_processed, all_old_counts = preprocess_old_columns_before_merge(all_vuln_df)
        new_vuln_processed, new_old_counts = preprocess_old_columns_before_merge(updated_new_vuln_df)

        # Step 2c: Merge preprocessed vulnerability data (CORRECTED)
        logging.info("Step 2c: Merging preprocessed vulnerability data...")
        merged_df, overridden_count, new_count = merge_vulnerability_data(all_vuln_processed, new_vuln_processed)

        # Step 2d: Rename Scope Identification values (NEW STEP)
        logging.info("Step 2d: Renaming Scope Identification values...")
        processed_df, scope_renamed_count = rename_scope_identification_values(merged_df)

        # After Step 3: Clean Vulnerability Category typos
        logging.info("Step 3: Cleaning Vulnerability Category typos...")
        processed_df, typo_fixes_count = clean_vulnerability_category_typos(merged_df)

        # NEW Step 4: Standardize column values
        logging.info("Step 4: Standardizing column values...")
        processed_df, standardization_counters = standardize_column_values(processed_df)

        # Step 5: Normalize Value Stream and Sub Value Stream columns
        logging.info("Step 5: Normalizing Value Stream and Sub Value Stream...")
        processed_df, vs_normalized_count, svs_normalized_count = normalize_value_streams(processed_df)

        # Step 5: Apply Legacy/Non-Legacy classification (only for blank values)
        logging.info("Step 5: Applying Legacy/Non-Legacy classification (only for blank values)...")
        processed_df, legacy_count, non_legacy_count, skipped_legacy_count = apply_legacy_classification(processed_df, legacy_df)

        # Step 6: Apply QID CTI classification
        logging.info("Step 6: Applying QID CTI classification...")
        processed_df, highly_exploitable_count, empty_cti_count = apply_qid_cti_classification(processed_df, qid_df)

        # Step 7: Apply Tags logic based on Vulnerability Class and QID CTI
        logging.info("Step 7: Applying Tags logic...")
        processed_df, exploitable_tags_count, fy_quarter_added_count, fy_quarter_already_present_count = apply_tags_logic(processed_df)

        # Step 8: Update Vulnerability Category based on Scope Identification and Value Stream
        logging.info("Step 8: Updating Vulnerability Category...")
        processed_df, os_level_count, non_os_level_count, not_set_count = update_vulnerability_category(processed_df)

        # Step 8.5: Update Vuln Status and Install Status rules
        logging.info("Step 8.5: Updating Vuln Status and Install Status rules...")
        processed_df, fixed_vuln_count, decommissioned_install_count = update_vuln_status_and_install_status_rules(processed_df)

        # Step 8.6: Update Exception records
        logging.info("Step 8.6: Updating Exception records...")
        processed_df, exception_records_count = update_exception_records(processed_df)

        # Step 9: Update blank Status (IVM) records  
        logging.info("Step 9: Updating blank Status (IVM) records...")
        processed_df, blank_status_updated_count = update_blank_status_ivm(processed_df)

        # Step 10: Apply additional rules based on Vulnerability Category
        logging.info("Step 10: Applying Vulnerability Category-based rules...")
        processed_df, not_set_rule_updates, os_level_rule_updates, azure_ownership_updates, on_premises_ownership_updates = apply_vulnerability_category_rules(processed_df)

        # Step 11: Update NON-OS Level ownership rules
        logging.info("Step 11: Updating NON-OS Level ownership rules...")
        processed_df, non_os_ownership_counts, non_os_total_updates = update_non_os_level_ownership(processed_df)

        # Step 11.1: Update Legacy non-exploitable ownership
        logging.info("Step 11.1: Updating Legacy non-exploitable ownership...")
        processed_df, legacy_ignore_count = update_legacy_non_exploitable_ownership(processed_df)

        # Step 11.2: Update ownership for Decommissioned/Closed vulnerabilities
        logging.info("Step 11.2: Updating ownership for Decommissioned/Closed vulnerabilities...")
        processed_df, ignore_old_count, remarks_updated_count = update_ownership_for_decommissioned_and_closed(processed_df)

        # Step 12: Update Rescan Date column with today's date
        logging.info("Step 12: Updating Rescan Date column...")
        processed_df, rescan_date_value = update_rescan_date_column(processed_df)

        # Step 13: Apply final OS Level updates (FINAL OVERRIDE - HIGHEST PRIORITY)
        #logging.info("Step 13: Applying final OS Level updates (HIGHEST PRIORITY)...")
        #processed_df, final_sub_vs_updates, final_vs_updates, final_azure_updates, final_onprem_updates = apply_final_os_level_updates(processed_df)

        # NEW Step 13: Update VM Status based on ID and Vuln Status
        logging.info("Step 13: Updating VM Status based on ID and Vuln Status...")
        processed_df, vm_active_count, vm_reopened_count = update_vm_status_based_on_vuln_status(processed_df)
        # NEW Step 14: Update Actual Mitigation Date based on Status (IVM)
        logging.info("Step 14: Updating Actual Mitigation Date based on Status (IVM)...")
        processed_df, closed_mitigation_count, open_exception_mitigation_count = update_actual_mitigation_date_based_on_status_ivm(processed_df)

        # NEW Step 14.1: Update column names
        logging.info("Step 14.1 : Updating column names...")
        processed_df, column_rename_count = update_column_names_server_to_cmdb(processed_df)

        # Step 15: Create Excel workbook with OPTIMIZED xlsxwriter
        logging.info("Step 15: Creating Excel workbook with optimized xlsxwriter...")

        async def create_excel():
            return await create_excel_workbook_fast(processed_df, "Processed Vulnerabilities")

        # Run the async Excel creation
        excel_bytes = asyncio.run(create_excel())

        # Calculate statistics
        total_processed = len(processed_df)

        # Calculate severity counts from processed data
        severity_counts = {}
        if 'Severity' in processed_df.columns:
            severity_counts = processed_df['Severity'].value_counts().to_dict()

        # Calculate function duration
        function_duration = time.time() - function_start_time
        logging.info(f"Data processing completed in {function_duration:.2f} seconds")
        logging.info(f"Output Excel file maintains original structure with {len(processed_df.columns)} columns")

        # Generate filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"processed_vulnerabilities_{cycle_id}_{timestamp}.xlsx"

        # Return the Excel file with comprehensive JSON serialization
        return func.HttpResponse(
            excel_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "Cache-Control": "no-cache",
                "X-Cycle-ID": cycle_id,
                "X-Total-Processed": str(total_processed),
                "X-Processing-Time": f"{function_duration:.2f}s",
                "X-Severity-Counts": json.dumps(severity_counts, default=convert_numpy_types),
                "X-Merge-Summary": json.dumps({
                    "overridden_records": overridden_count,
                    "new_records": new_count,
                    "original_all_vulns": len(all_vuln_df),
                    "new_vulns_input": len(updated_new_vuln_df),
                    "final_processed": total_processed
                }, default=convert_numpy_types),
                "X-Pre-Merge-Updates": json.dumps({
                    "reported_date_updated": datetime.datetime.now().strftime("%d/%m/%Y"),
                    "rag_updated": "Green",
                    "records_updated": len(updated_new_vuln_df)
                }, default=convert_numpy_types),
                "X-Typo-Fixes-Summary": json.dumps({
                    "vulnerability_category_typos_fixed": typo_fixes_count
                }, default=convert_numpy_types),
                "X-Scope-Renaming-Summary": json.dumps({
                    "scope_identification_renamed": scope_renamed_count,
                    "rules": {
                        "Application Dependent": "App Dependency",
                        "out-of-scope": "Scope - Others"
                    }
                }, default=convert_numpy_types),
                "X-Column-Standardization-Summary": json.dumps({
                    "classification_pre_production_fixed": standardization_counters['Classification']['pre_production_fixed'],
                    "classification_staging_to_tbd": standardization_counters['Classification']['staging_to_tbd'],
                    "classification_blank_to_not_set": standardization_counters['Classification']['blank_to_not_set'],
                    "exploitation_criteria_blank_to_not_set": standardization_counters['Exploitation Criteria']['blank_to_not_set'],
                    "class_blank_to_not_set": standardization_counters['Class']['blank_to_not_set'],
                    "server_tier_production_to_not_set": standardization_counters['Server Tier']['production_to_not_set'],
                    "server_tier_blank_to_not_set": standardization_counters['Server Tier']['blank_to_not_set'],
                    "status_server_owner_blank_to_not_set": standardization_counters['Status (Server Owner)']['blank_to_not_set']
                }, default=convert_numpy_types),
                "X-Normalization-Summary": json.dumps({
                    "value_stream_normalized": vs_normalized_count,
                    "sub_value_stream_normalized": svs_normalized_count
                }, default=convert_numpy_types),
                "X-Legacy-Summary": json.dumps({
                    "legacy_count": legacy_count,
                    "non_legacy_count": non_legacy_count,
                    "skipped_count": skipped_legacy_count
                }, default=convert_numpy_types),
                "X-QID-CTI-Summary": json.dumps({
                    "highly_exploitable_count": highly_exploitable_count,
                    "empty_cti_count": empty_cti_count
                }, default=convert_numpy_types),
                "X-Tags-Summary": json.dumps({
                    "exploitable_tags_count": exploitable_tags_count,
                    "fy_quarter_added_count": fy_quarter_added_count,
                    "fy_quarter_already_present_count": fy_quarter_already_present_count,
                    "current_fy_quarter": f"FY{str(datetime.datetime.now().year)[-2:]}-Q{((datetime.datetime.now().month-1)//3)+1}"
                }, default=convert_numpy_types),
                "X-Vulnerability-Category-Summary": json.dumps({
                    "os_level_count": os_level_count,
                    "non_os_level_count": non_os_level_count,
                    "not_set_count": not_set_count
                }, default=convert_numpy_types),
                "X-Status-IVM-Summary": json.dumps({
                    "blank_status_ivm_updated": blank_status_updated_count,
                    "status_set_to": "Open",
                    "remarks_set_to": "Open Vuln"
                }, default=convert_numpy_types),
                "X-Category-Rules-Summary": json.dumps({
                    "not_set_rule_updates": not_set_rule_updates,
                    "os_level_rule_updates": os_level_rule_updates,
                    "azure_ownership_updates": azure_ownership_updates,
                    "on_premises_ownership_updates": on_premises_ownership_updates
                }, default=convert_numpy_types),
                "X-Non-OS-Ownership-Summary": json.dumps({
                    "total_updates": non_os_total_updates,
                    "ownership_counts": non_os_ownership_counts
                }, default=convert_numpy_types),
                "X-Legacy-Ignore-Summary": json.dumps({
                    "legacy_ignore_ownership_updated": legacy_ignore_count,
                    "rule": "Legacy + blank/empty QID CTI → Ignore-Legacy"
                }, default=convert_numpy_types),
                "X-Ignore-Old-Summary": json.dumps({
                    "ignore_old_ownership_updated": ignore_old_count,
                    "ivm_remarks_updated": remarks_updated_count,
                    "rule1": "VM Status contains 'decomissioned'/'decommissioned' → Ignore-Old + append to IVM Remarks",
                    "rule2": "IVM Remarks contains 'closed due to vulnerability fixed' → Ignore-Old",
                    "rule3": "IVM Remarks contains 'closed due to vulnerability got fixed' → Ignore-Old",
                    "rule4": "IVM Remarks contains 'closed due to decommission' → Ignore-Old"
                }, default=convert_numpy_types),
                "X-Exception-Records-Summary": json.dumps({
                    "exception_records_updated": exception_records_count,
                    "rule": "Exception Number present AND Exception Expiry Date > today AND Status (IVM) ≠ 'Closed' → Status (IVM) = 'Exception', append 'Under Exception' to IVM Remarks"
                }, default=convert_numpy_types),
                "X-Vuln-Install-Status-Summary": json.dumps({
                    "fixed_vulnerabilities_updated": fixed_vuln_count,
                    "decommissioned_install_updated": decommissioned_install_count,
                    "rule1": "Vuln Status = 'Fixed' → Status(IVM)='Closed', RAG='-Not Set-', append 'Closed due to vulnerability fix', set Actual Mitigation Date",
                    "rule2": "Install Status = 'decommissioned'/'decomissioned' → Status(IVM)='Closed', RAG='-Not Set-', VM Status='Decommissioned', append 'Closed due to decommissioned', set Actual Mitigation Date"
                }, default=convert_numpy_types),
                "X-Rescan-Date-Summary": json.dumps({
                    "rescan_date_updated": rescan_date_value,
                    "records_updated": total_processed
                }, default=convert_numpy_types),
                #"X-Final-OS-Level-Summary": json.dumps({
                   # "sub_value_stream_final_updates": final_sub_vs_updates,
                    #"value_stream_final_updates": final_vs_updates,
                    #"azure_ownership_final_updates": final_azure_updates,
                    #"onprem_ownership_final_updates": final_onprem_updates,
                    #"note": "These updates override all previous assignments for OS Level vulnerabilities"
               #}, default=convert_numpy_types),
                "X-Column-Count": str(len(processed_df.columns)),
                "X-Original-Structure-Preserved": "true",
                "X-Excel-Engine": "xlsxwriter"
            },
            status_code=200
        )

    except Exception as e:
        function_duration = time.time() - function_start_time
        error_message = str(e)
        error_details = traceback.format_exc()

        logging.error(f"Error in process_merged_data: {error_message}\n{error_details}")

        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "message": error_message,
                "processingTime": f"{function_duration:.2f} seconds"
            }),
            mimetype="application/json",
            headers={
                "X-Error-Type": type(e).__name__,
                "X-Processing-Time": f"{function_duration:.2f}s"
            },
            status_code=500
        )
