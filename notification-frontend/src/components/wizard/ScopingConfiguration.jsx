import React from "react";

// ============================================================
// SCOPING CONFIGURATION
// ============================================================
//
// Infrastructure values come from the infrastructure deployment.
//
// Fixed values are displayed as read-only.
//
// User-entered values:
//
// - SharePoint URL
// - Callback Secret Key
// - Completion Logic App URL
//
// Deployment is handled by the parent / WizardFooter.
// ============================================================

function ScopingConfiguration({
  deploymentInfo,
  formData,
  onChange,
  onDeploy,
  isDeploying,
  result,
  error,
}) {

  // ==========================================================
  // HANDLE CHANGE
  // ==========================================================

  const handleChange = (field, value) => {

    if (onChange) {

      onChange(
        field,
        value
      );

    }

  };


  // ==========================================================
  // DEPLOY
  // ==========================================================

  const handleDeploy = () => {

    if (onDeploy) {

      onDeploy();

    }

  };


  // ==========================================================
  // FIXED LOGIC APP CONFIGURATION
  // ==========================================================

  const logicAppName =
    "LA-Scoping-00";

  const scoping01LogicAppName =
    "LA-Scoping-01";

  const scoping02LogicAppName =
    "LA-Scoping-02";


  // ==========================================================
  // FIXED CONNECTION CONFIGURATION
  // ==========================================================

  const tableConnectionName =
    "azuretables-1";

  const queueConnectionName =
    "azurequeues-1";

  const sharepointConnectionName =
    "sharepointonline-1";


  // ==========================================================
  // FIXED STORAGE CONFIGURATION
  // ==========================================================

  const notificationLogTableName =
    "NotificationLogs";

  const notificationStatusTableName =
    "NotificationStatus";

  const queueName =
    "scopingschedulequeue";

  const authscanQueueName =
    "authscan00";


  return (

    <div className="wizard-section">

      {/* ====================================================
          HEADER
          ==================================================== */}

      <div className="wizard-section-header">

        <div>

          <h2>
            Scoping Service Configuration
          </h2>

          <p>
            Configure the Scoping Services required
            for the workflow.
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
            These values were returned by the infrastructure
            deployment.
          </p>

        </div>


        <div className="configuration-grid">

          {/* ==================================================
              SUBSCRIPTION ID
              ================================================== */}

          <div className="configuration-field">

            <label>
              Subscription ID
            </label>

            <input
              type="text"
              value={
                deploymentInfo?.subscription_id || ""
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              RESOURCE GROUP
              ================================================== */}

          <div className="configuration-field">

            <label>
              Resource Group
            </label>

            <input
              type="text"
              value={
                deploymentInfo?.resource_group_name || ""
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              LOCATION
              ================================================== */}

          <div className="configuration-field">

            <label>
              Location
            </label>

            <input
              type="text"
              value={
                deploymentInfo?.location || ""
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              STORAGE ACCOUNT
              ================================================== */}

          <div className="configuration-field">

            <label>
              Storage Account Name
            </label>

            <input
              type="text"
              value={
                deploymentInfo?.storage_account_name || ""
              }
              readOnly
              disabled
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          LOGIC APP CONFIGURATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Logic App Configuration
          </h3>

          <p>
            Scoping Logic Apps used by the workflow.
          </p>

        </div>


        <div className="configuration-grid">

          {/* ==================================================
              MAIN LOGIC APP
              ================================================== */}

          <div className="configuration-field">

            <label>
              Logic App Name
            </label>

            <input
              type="text"
              value={logicAppName}
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              SCOPING 01
              ================================================== */}

          <div className="configuration-field">

            <label>
              Scoping 01 Logic App Name
            </label>

            <input
              type="text"
              value={scoping01LogicAppName}
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              SCOPING 02
              ================================================== */}

          <div className="configuration-field">

            <label>
              Scoping 02 Logic App Name
            </label>

            <input
              type="text"
              value={scoping02LogicAppName}
              readOnly
              disabled
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          STORAGE CONFIGURATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Storage Configuration
          </h3>

          <p>
            Storage resources used by the Scoping Services.
          </p>

        </div>


        <div className="configuration-grid">

          {/* ==================================================
              QUEUE
              ================================================== */}

          <div className="configuration-field">

            <label>
              Scoping Schedule Queue Name
            </label>

            <input
              type="text"
              value={queueName}
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              AUTH SCAN QUEUE
              ================================================== */}

          <div className="configuration-field">

            <label>
              Auth Scan Queue Name
            </label>

            <input
              type="text"
              value={authscanQueueName}
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              NOTIFICATION LOG TABLE
              ================================================== */}

          <div className="configuration-field">

            <label>
              Notification Log Table Name
            </label>

            <input
              type="text"
              value={notificationLogTableName}
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              NOTIFICATION STATUS TABLE
              ================================================== */}

          <div className="configuration-field">

            <label>
              Notification Status Table Name
            </label>

            <input
              type="text"
              value={notificationStatusTableName}
              readOnly
              disabled
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          CONNECTION CONFIGURATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Connection Configuration
          </h3>

          <p>
            API connections used by the Scoping Logic Apps.
          </p>

        </div>


        <div className="configuration-grid">

          {/* ==================================================
              AZURE TABLES
              ================================================== */}

          <div className="configuration-field">

            <label>
              Azure Tables Connection
            </label>

            <input
              type="text"
              value={tableConnectionName}
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              AZURE QUEUES
              ================================================== */}

          <div className="configuration-field">

            <label>
              Azure Queues Connection
            </label>

            <input
              type="text"
              value={queueConnectionName}
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              SHAREPOINT
              ================================================== */}

          <div className="configuration-field">

            <label>
              SharePoint Connection
            </label>

            <input
              type="text"
              value={sharepointConnectionName}
              readOnly
              disabled
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          SCOPING CONFIGURATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Scoping Configuration
          </h3>

          <p>
            Enter the Scoping Service configuration details.
          </p>

        </div>


        <div className="configuration-grid">

          {/* ==================================================
              SHAREPOINT URL
              ================================================== */}

          <div className="configuration-field">

            <label htmlFor="sharepoint-url">

              SharePoint URL

              <span className="required-mark">
                *
              </span>

            </label>

            <input
              id="sharepoint-url"
              type="url"
              placeholder="https://company.sharepoint.com/sites/demo"
              value={
                formData?.sharepoint_url || ""
              }
              onChange={(event) =>
                handleChange(
                  "sharepoint_url",
                  event.target.value
                )
              }
              disabled={isDeploying}
            />

          </div>


          {/* ==================================================
              CALLBACK SECRET KEY
              ================================================== */}

          <div className="configuration-field">

            <label htmlFor="callback-secret-key">

              Callback Secret Key

              <span className="required-mark">
                *
              </span>

            </label>

            <input
              id="callback-secret-key"
              type="password"
              placeholder="Enter callback secret key"
              value={
                formData?.callback_secret_key || ""
              }
              onChange={(event) =>
                handleChange(
                  "callback_secret_key",
                  event.target.value
                )
              }
              disabled={isDeploying}
            />

          </div>


          {/* ==================================================
              COMPLETION LOGIC APP URL
              ================================================== */}

          <div className="configuration-field">

            <label htmlFor="completion-logic-app-url">

              Completion Logic App URL

              <span className="required-mark">
                *
              </span>

            </label>

            <input
              id="completion-logic-app-url"
              type="url"
              placeholder="Enter Completion Logic App URL"
              value={
                formData?.completion_logic_app_url || ""
              }
              onChange={(event) =>
                handleChange(
                  "completion_logic_app_url",
                  event.target.value
                )
              }
              disabled={isDeploying}
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          SUCCESS
          ====================================================

          IMPORTANT:
          Unlike the previous version, the success message
          does NOT replace the complete configuration screen.

          It appears below the configuration cards,
          exactly like the Key Vault screen.
          ==================================================== */}

      {result && (

        <div className="configuration-success">

          <strong>
            Scoping configuration completed.
          </strong>

          <p>
            The Scoping Service configuration
            was processed successfully.
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
          DEPLOYMENT BUTTON
          ====================================================

          If your WizardFooter already controls deployment,
          you can remove this entire section.

          Kept here to match the Key Vault component pattern.
          ==================================================== */}

      <div className="configuration-actions">

        <button
          type="button"
          className="primary-button"
          onClick={handleDeploy}
          disabled={isDeploying}
        >

          {isDeploying
            ? "Deploying..."
            : "Deploy Scoping Services"}

        </button>

      </div>

    </div>

  );

}


export default ScopingConfiguration;