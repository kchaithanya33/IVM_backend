function FunctionDeployment({
  deploymentInfo,
  onDeploy,
  isDeploying,
  result,
  error,
}) {

  return (
    <div className="wizard-page">

      {/* ====================================================
          HEADER
          ==================================================== */}

      <div className="wizard-page-header">

        <h1>
          Function App Deployment
        </h1>

        <p>
          Deploy the Function App using the infrastructure
          created in the previous steps.
        </p>

      </div>


      {/* ====================================================
          DEPLOYMENT INFORMATION
          ==================================================== */}

      <div className="configuration-card">

        <h2>
          Infrastructure Details
        </h2>


        <div className="configuration-grid">

          <div className="configuration-item">

            <span className="configuration-label">
              Subscription ID
            </span>

            <span className="configuration-value">
              {deploymentInfo?.subscription_id || "-"}
            </span>

          </div>


          <div className="configuration-item">

            <span className="configuration-label">
              Resource Group
            </span>

            <span className="configuration-value">
              {deploymentInfo?.resource_group_name || "-"}
            </span>

          </div>


          <div className="configuration-item">

            <span className="configuration-label">
              Location
            </span>

            <span className="configuration-value">
              {deploymentInfo?.location || "-"}
            </span>

          </div>


          <div className="configuration-item">

            <span className="configuration-label">
              Storage Account
            </span>

            <span className="configuration-value">
              {deploymentInfo?.storage_account_name || "-"}
            </span>

          </div>


          <div className="configuration-item">

            <span className="configuration-label">
              Function App
            </span>

            <span className="configuration-value">
              {deploymentInfo?.function_app_name || "-"}
            </span>

          </div>


          <div className="configuration-item">

            <span className="configuration-label">
              Table Name
            </span>

            <span className="configuration-value">
              AppConfiguration
            </span>

          </div>


          <div className="configuration-item">

            <span className="configuration-label">
              Cache Expiration
            </span>

            <span className="configuration-value">
              10 minutes
            </span>

          </div>

        </div>

      </div>


      {/* ====================================================
          ERROR
          ==================================================== */}

      {error && (

        <div className="error-message">
          {error}
        </div>

      )}


      {/* ====================================================
          SUCCESS
          ==================================================== */}

      {result && (

        <div className="success-message">

          <h3>
            Function App Deployment Successful
          </h3>

          <pre>
            {JSON.stringify(
              result,
              null,
              2
            )}
          </pre>

        </div>

      )}

    </div>
  );
}


export default FunctionDeployment;