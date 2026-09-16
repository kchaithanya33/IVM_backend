import React from "react";

// ============================================================
// NOTIFICATION / COMMON SERVICES CONFIGURATION
// ============================================================
//
// This page displays infrastructure information returned by
// the infrastructure deployment.
//
// All values are read-only.
//
// The Notification Service deployment itself is handled by the
// next Notification Service page.
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

  const qualysFunctionAppName =
    deploymentInfo?.qualys_function_app_name ||
    deploymentInfo?.function_app_name ||
    "";

  const storageAccountName =
    deploymentInfo?.storage_account_name || "";


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
            Review the Common Services infrastructure
            configuration.
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


          {/* STORAGE ACCOUNT */}

          <div className="configuration-field">

            <label>
              Storage Account Name
            </label>

            <input
              type="text"
              value={storageAccountName}
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
            The Common Services infrastructure was
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