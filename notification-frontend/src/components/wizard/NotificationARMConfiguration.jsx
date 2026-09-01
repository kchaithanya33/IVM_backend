import React from "react";

// ============================================================
// NOTIFICATION / COMMON SERVICES CONFIGURATION
// ============================================================
//
// Same visual/design structure as KeyVaultConfiguration.
//
// All configuration values are read-only.
//
// Resource information comes from infrastructure deployment.
//
// DEPLOY:
//   The "Deploy Common Services" button performs the actual
//   deployment through the onDeploy callback.
//
// NEXT:
//   Navigation is handled by WizardFooter.
//
// SUCCESS:
//   Success message is displayed inside this component.
// ============================================================

function NotificationARMConfiguration({
  deploymentInfo,
  configuration,
  result,
  error,
  onDeploy,
  isDeploying,
}) {

  // ==========================================================
  // DEPLOY / SETUP
  // ==========================================================

  const handleDeploy = () => {

    if (onDeploy) {

      onDeploy();

    }

  };


  // ==========================================================
  // RESOURCE INFORMATION
  // ==========================================================

  const subscriptionId =
    deploymentInfo?.subscription_id || "";

  const resourceGroupName =
    deploymentInfo?.resource_group_name || "";

  const location =
    deploymentInfo?.location || "";

  const functionAppName =
    deploymentInfo?.function_app_name || "";

  const storageAccountName =
    deploymentInfo?.storage_account_name || "";


  // ==========================================================
  // LOGIC APP CONFIGURATION
  // ==========================================================

  const logicAppName =
    configuration?.logic_app_name ||
    "notification-service";

  const completionLogicAppName =
    configuration?.completion_logic_app_name ||
    "notification-completion";

  const notificationFollowupLogicAppName =
    configuration?.notification_followup_logic_app_name ||
    "notification-followup";


  // ==========================================================
  // STORAGE CONFIGURATION
  // ==========================================================

  const followupQueueName =
    configuration?.followup_queue_name ||
    "taskreminder";

  const notificationLogTableName =
    configuration?.notification_log_table_name ||
    "NotificationLogs";

  const notificationStatusTableName =
    configuration?.notification_status_table_name ||
    "NotificationStatus";


  // ==========================================================
  // CONNECTION CONFIGURATION
  // ==========================================================

  const azureTablesConnectionName =
    configuration?.azure_tables_connection_name ||
    "azuretables-1";

  const azureQueuesConnectionName =
    configuration?.azure_queues_connection_name ||
    "azurequeues-1";

  const office365ConnectionName =
    configuration?.office365_connection_name ||
    "office365-1";

  const teamsConnectionName =
    configuration?.teams_connection_name ||
    "teams-1";


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
            Common Services Configuration
          </h2>

          <p>
            Review the Common Services configuration
            required for the notification workflow.
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
                subscriptionId
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
                resourceGroupName
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
                location
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              FUNCTION APP
              ================================================== */}

          <div className="configuration-field">

            <label>
              Function App Name
            </label>

            <input
              type="text"
              value={
                functionAppName
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
                storageAccountName
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
            Review the Logic Apps used by the
            notification workflow.
          </p>

        </div>


        <div className="configuration-grid">


          {/* ==================================================
              LOGIC APP
              ================================================== */}

          <div className="configuration-field">

            <label>
              Logic App Name
            </label>

            <input
              type="text"
              value={
                logicAppName
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
              Completion Logic App Name
            </label>

            <input
              type="text"
              value={
                completionLogicAppName
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              NOTIFICATION FOLLOW-UP LOGIC APP
              ================================================== */}

          <div className="configuration-field">

            <label>
              Notification Follow-up Logic App Name
            </label>

            <input
              type="text"
              value={
                notificationFollowupLogicAppName
              }
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
            Review the queues and tables used by the
            Notification Service.
          </p>

        </div>


        <div className="configuration-grid">


          {/* ==================================================
              FOLLOW-UP QUEUE
              ================================================== */}

          <div className="configuration-field">

            <label>
              Follow-up Queue Name
            </label>

            <input
              type="text"
              value={
                followupQueueName
              }
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
              value={
                notificationLogTableName
              }
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
              value={
                notificationStatusTableName
              }
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
            Review the API connections used by the
            Logic Apps.
          </p>

        </div>


        <div className="configuration-grid">


          {/* ==================================================
              AZURE TABLES CONNECTION
              ================================================== */}

          <div className="configuration-field">

            <label>
              Azure Tables Connection
            </label>

            <input
              type="text"
              value={
                azureTablesConnectionName
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              AZURE QUEUES CONNECTION
              ================================================== */}

          <div className="configuration-field">

            <label>
              Azure Queues Connection
            </label>

            <input
              type="text"
              value={
                azureQueuesConnectionName
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              OFFICE 365 CONNECTION
              ================================================== */}

          <div className="configuration-field">

            <label>
              Office 365 Connection
            </label>

            <input
              type="text"
              value={
                office365ConnectionName
              }
              readOnly
              disabled
            />

          </div>


          {/* ==================================================
              TEAMS CONNECTION
              ================================================== */}

          <div className="configuration-field">

            <label>
              Teams Connection
            </label>

            <input
              type="text"
              value={
                teamsConnectionName
              }
              readOnly
              disabled
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
            Common Services deployment completed.
          </strong>

          <p>
            The Notification Service Logic Apps,
            storage configuration, and connections
            were processed successfully.
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
          DEPLOY COMMON SERVICES BUTTON
          ==================================================== */}

      <div className="configuration-actions">

        <button
          type="button"
          className="primary-button"
          onClick={handleDeploy}
         
        >

          {isDeploying
            ? "Deploying..."
            : result
              ? "Deployed"
              : "Deploy Common Services"}

        </button>

      </div>

    </div>

  );

}


export default NotificationARMConfiguration;