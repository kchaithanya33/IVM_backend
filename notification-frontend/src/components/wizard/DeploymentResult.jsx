function DeploymentResult({
  formData,
  result,
  error,
}) {

  // ============================================================
  // ERROR
  // ============================================================

  if (error) {

    return (

      <section className="deployment-result">

        <div className="deployment-status error">

          <div className="deployment-status-icon">
            !
          </div>

          <div>

            <h2>
              Deployment Failed
            </h2>

            <p>
              {error}
            </p>

          </div>

        </div>

      </section>

    );

  }


  // ============================================================
  // REVIEW / SUCCESS
  // ============================================================

  return (

    <section className="deployment-result">

      {/* ======================================================
          REVIEW STATUS
          ====================================================== */}

      <div className="deployment-status success">

        <div className="deployment-status-icon">
          ✓
        </div>

        <div>

          <h2>
            Deployment Completed
          </h2>

          <p>
            Your notification infrastructure was
            deployed successfully.
          </p>

        </div>

      </div>


      {/* ======================================================
          DEPLOYMENT SUMMARY
          ====================================================== */}

      <div className="deployment-summary">

        <h3>
          Deployment Details
        </h3>

        <div className="deployment-grid">

          <div className="deployment-item">

            <span>
              Subscription ID
            </span>

            <strong>
              {formData.subscriptionId}
            </strong>

          </div>


          <div className="deployment-item">

            <span>
              Resource Group
            </span>

            <strong>
              {formData.resourceGroupName}
            </strong>

          </div>


          <div className="deployment-item">

            <span>
              Resource Group Location
            </span>

            <strong>
              {formData.resourceGroupLocation}
            </strong>

          </div>


          <div className="deployment-item">

            <span>
              Storage Account
            </span>

            <strong>
              {formData.storageAccountName}
            </strong>

          </div>


          <div className="deployment-item">

            <span>
              Storage Account Location
            </span>

            <strong>
              {formData.storageAccountLocation}
            </strong>

          </div>


          <div className="deployment-item">

            <span>
              Function App
            </span>

            <strong>
              {formData.functionAppName}
            </strong>

          </div>

        </div>

      </div>


      {/* ======================================================
          BACKEND RESPONSE
          ====================================================== */}

      {result && (

        <div className="backend-response">

          <div className="backend-response-header">

            <h3>
              Deployment Status
            </h3>

            <span className="success-badge">
              Succeeded
            </span>

          </div>

          <p>
            Azure resources have been processed
            successfully by the backend.
          </p>

        </div>

      )}

    </section>

  );

}


export default DeploymentResult;