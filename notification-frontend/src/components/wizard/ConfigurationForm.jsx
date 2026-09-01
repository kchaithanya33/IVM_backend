function ConfigurationForm({ formData }) {
  return (
    <div className="configuration-form">

      <div className="configuration-form-header">

        <h2>
          Deployment Configuration
        </h2>

        <p>
          Review the deployment configuration
          before starting the deployment.
        </p>

      </div>

      <div className="configuration-summary">

        {/* ==================================================
            SUBSCRIPTION
            ================================================== */}

        <div className="configuration-item">
          <label>
            Subscription ID
          </label>

          <div className="configuration-value">
            {formData?.subscriptionId ||
              "-"}
          </div>
        </div>

        {/* ==================================================
            RESOURCE GROUP
            ================================================== */}

        <div className="configuration-item">
          <label>
            Resource Group Name
          </label>

          <div className="configuration-value">
            {formData?.resourceGroupName ||
              "-"}
          </div>
        </div>

        <div className="configuration-item">
          <label>
            Resource Group Location
          </label>

          <div className="configuration-value">
            {formData?.resourceGroupLocation ||
              "-"}
          </div>
        </div>

        {/* ==================================================
            STORAGE
            ================================================== */}

        <div className="configuration-item">
          <label>
            Storage Account Name
          </label>

          <div className="configuration-value">
            {formData?.storageAccountName ||
              "-"}
          </div>
        </div>

        <div className="configuration-item">
          <label>
            Storage Account Location
          </label>

          <div className="configuration-value">
            {formData?.storageAccountLocation ||
              "-"}
          </div>
        </div>

        {/* ==================================================
            FUNCTION APP
            ================================================== */}

        <div className="configuration-item">
          <label>
            Function App Name
          </label>

          <div className="configuration-value">
            {formData?.functionAppName ||
              "-"}
          </div>
        </div>

      </div>

      <div className="configuration-info">

        <span className="configuration-info-icon">
          i
        </span>

        <span>
          Verify all infrastructure details
          before starting the deployment.
        </span>

      </div>

    </div>
  );
}

export default ConfigurationForm;