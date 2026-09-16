import React, { useState } from "react";

// ============================================================
// NOTIFICATION SERVICE
// ============================================================
//
// STEP 8
//
// Notification Service has its own ARM deployment API:
//
// POST /notification-arm/deploy
//
// Infrastructure values come from deploymentInfo.
//
// User-visible configuration is limited to the values that
// actually need to be reviewed/entered.
//
// Other configuration values remain as defaults and are sent
// to the backend without being displayed.
// ============================================================

function NotificationService({
  deploymentInfo,
  onDeploy,
  result,
  error,
  isDeploying,
}) {

  // ==========================================================
  // USER INPUT
  // ==========================================================

  const [chgApprovalRecipients, setChgApprovalRecipients] =
    useState("");


  // ==========================================================
  // INFRASTRUCTURE VALUES
  // These come from the first page / infrastructure deployment.
  // ==========================================================

  const subscriptionId =
    deploymentInfo?.subscription_id || "";

  const resourceGroupName =
    deploymentInfo?.resource_group_name || "";

  const location =
    deploymentInfo?.location || "";

  const qualysFunctionAppName =
    deploymentInfo?.qualys_function_app_name ||
    deploymentInfo?.function_app_name ||
    "";

  const storageAccountName =
    deploymentInfo?.storage_account_name || "";


  // ==========================================================
  // DEFAULT CONFIGURATION
  //
  // These values are sent to the backend.
  //
  // Only selected values are displayed in the UI.
  // ==========================================================

  const notificationConfiguration = {

    // --------------------------------------------------------
    // QUALYS
    // --------------------------------------------------------

    qualys_function_name:
      "QualysScanStatus",


    // --------------------------------------------------------
    // LOGIC APPS
    // --------------------------------------------------------

    logic_app_name:
      "Notification-service",

    completion_logic_app_name:
      "Completion-logic",

    notification_followup_logic_app_name:
      "Notification-Followup-01",

    vuln_scan_complete_logic_app_name:
      "LA-VulnScan-Complete",

    sts_change_approval_check_logic_app_name:
      "LA-STS-ChangeApprovalCheck",

    status_tracking_system_logic_app_name:
      "LA-StatusTrackingSystem",


    // --------------------------------------------------------
    // STORAGE
    //
    // Hidden from user.
    // --------------------------------------------------------

    followup_queue_name:
      "taskreminder",

    qualys_scan_status_queue_name:
      "qualysscanstatusqueue",

    notification_log_table_name:
      "NotificationLogs",

    notification_status_table_name:
      "NotificationStatus",

    scan_status_log_table_name:
      "ScanStatusLog",

    scan_completion_log_table_name:
      "ScanCompletionLog",


    // --------------------------------------------------------
    // CONNECTIONS
    //
    // Hidden from user.
    // --------------------------------------------------------

    azure_tables_connection_name:
      "azuretables-1",

    azure_queues_connection_name:
      "azurequeues-1",

    office365_connection_name:
      "office365-1",

    teams_connection_name:
      "teams-1",

  };


  // ==========================================================
  // DEPLOY
  // ==========================================================

  const handleDeploy = () => {

    if (!onDeploy) {
      return;
    }


    // --------------------------------------------------------
    // Complete backend payload
    //
    // Notice:
    //
    // UI displays:
    // "Notification Service"
    //
    // Backend receives:
    // logic_app_name
    //
    // --------------------------------------------------------

    const payload = {

      // ------------------------------------------------------
      // INFRASTRUCTURE
      // ------------------------------------------------------

      subscription_id:
        subscriptionId,

      resource_group_name:
        resourceGroupName,

      location:
        location,

      storage_account_name:
        storageAccountName,

      qualys_function_app_name:
        qualysFunctionAppName,


      // ------------------------------------------------------
      // CONFIGURATION
      // ------------------------------------------------------

      ...notificationConfiguration,


      // ------------------------------------------------------
      // USER PROVIDED VALUE
      // ------------------------------------------------------

      chg_approval_recipients:
        chgApprovalRecipients,

    };


    onDeploy(payload);
  };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="wizard-section">

      {/* ====================================================
          HEADER
          ==================================================== */}

      <div className="wizard-section-header">

        <div>

          <h2>
            Notification Service
          </h2>

          <p>
            Review the Notification Service configuration
            and provide the required approval recipient.
          </p>

        </div>

      </div>


      {/* ====================================================
          INFRASTRUCTURE INFORMATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Infrastructure Information
          </h3>

          <p>
            These values come from the infrastructure
            deployment.
          </p>

        </div>


        <div className="configuration-grid">

          {/* SUBSCRIPTION ID */}

          <div className="configuration-field">

            <label>
              Subscription ID
            </label>

            <input
              type="text"
              value={subscriptionId}
              readOnly
              disabled
            />

          </div>


          {/* RESOURCE GROUP */}

          <div className="configuration-field">

            <label>
              Resource Group
            </label>

            <input
              type="text"
              value={resourceGroupName}
              readOnly
              disabled
            />

          </div>


          {/* LOCATION */}

          <div className="configuration-field">

            <label>
              Location
            </label>

            <input
              type="text"
              value={location}
              readOnly
              disabled
            />

          </div>


          {/* QUALYS FUNCTION APP */}

          <div className="configuration-field">

            <label>
              Qualys Function App Name
            </label>

            <input
              type="text"
              value={qualysFunctionAppName}
              readOnly
              disabled
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          NOTIFICATION SERVICE CONFIGURATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Notification Service Configuration
          </h3>

          <p>
            Review the Logic Apps and Qualys function used
            by the Notification Service.
          </p>

        </div>


        <div className="configuration-grid">

          {/* ==================================================
              QUALYS FUNCTION
              ================================================== */}

          <div className="configuration-field">

            <label>
              Qualys Function Name
            </label>

            <input
              type="text"
              value={
                notificationConfiguration
                  .qualys_function_name
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              LOGIC APP
              Backend key: logic_app_name
              UI label: Notification Service
              ================================================== */}

          <div className="configuration-field">

            <label>
              Notification Service
            </label>

            <input
              type="text"
              value={
                notificationConfiguration
                  .logic_app_name
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              COMPLETION LOGIC APP
              ================================================== */}

          <div className="configuration-field">

            <label>
              Completion Logic App
            </label>

            <input
              type="text"
              value={
                notificationConfiguration
                  .completion_logic_app_name
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              NOTIFICATION FOLLOW-UP
              ================================================== */}

          <div className="configuration-field">

            <label>
              Notification Follow-up Logic App
            </label>

            <input
              type="text"
              value={
                notificationConfiguration
                  .notification_followup_logic_app_name
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              VULNERABILITY SCAN COMPLETE
              ================================================== */}

          <div className="configuration-field">

            <label>
              Vulnerability Scan Complete Logic App
            </label>

            <input
              type="text"
              value={
                notificationConfiguration
                  .vuln_scan_complete_logic_app_name
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              STS CHANGE APPROVAL CHECK
              ================================================== */}

          <div className="configuration-field">

            <label>
              STS Change Approval Check Logic App
            </label>

            <input
              type="text"
              value={
                notificationConfiguration
                  .sts_change_approval_check_logic_app_name
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              STATUS TRACKING SYSTEM
              ================================================== */}

          <div className="configuration-field">

            <label>
              Status Tracking System Logic App
            </label>

            <input
              type="text"
              value={
                notificationConfiguration
                  .status_tracking_system_logic_app_name
              }
              readOnly
              disabled
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          CHG APPROVAL CONFIGURATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            CHG Approval Configuration
          </h3>

          <p>
            Provide the recipient email address for CHG
            approval notifications.
          </p>

        </div>


        <div className="configuration-grid">

          <div className="configuration-field">

            <label>
              CHG Approval Recipients
            </label>

            <input
              type="email"
              value={chgApprovalRecipients}
              onChange={(event) =>
                setChgApprovalRecipients(
                  event.target.value
                )
              }
              placeholder="Enter recipient email"
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          SUCCESS
          ==================================================== */}

      {result && (

        <div className="configuration-success">

          <strong>
            Notification Service deployment completed.
          </strong>

          <p>
            The Notification Service Logic Apps,
            configuration, and connections were
            processed successfully.
          </p>

        </div>

      )}


      {/* ====================================================
          ERROR
          ==================================================== */}

      {error && (

        <div className="configuration-error">

          <strong>
            Configuration Failed
          </strong>

          <p>
            {error}
          </p>

        </div>

      )}


      {/* ====================================================
          DEPLOY BUTTON
          ==================================================== */}

      <div className="configuration-actions">

        <button
          type="button"
          className="primary-button"
          onClick={handleDeploy}
          disabled={
            isDeploying ||
            !chgApprovalRecipients.trim()
          }
        >

          {isDeploying
            ? "Deploying..."
            : result
              ? "Deployed"
              : "Deploy Notification Service"}

        </button>

      </div>

    </div>

  );
}


export default NotificationService;