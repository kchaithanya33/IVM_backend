// ============================================================
// KEY VAULT + QUALYS CONFIGURATION
// ============================================================

function KeyVaultConfiguration({
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
  //
  // IMPORTANT:
  // Form state is maintained by NewDeployment.jsx.
  // This component only sends changes to the parent.
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
  // DEPLOY / SETUP
  //
  // IMPORTANT:
  // The actual API call is handled by NewDeployment.jsx.
  // ==========================================================

  const handleDeploy = () => {

    if (onDeploy) {

      onDeploy();

    }

  };


  return (

    <div className="wizard-section">

      {/* ====================================================
          HEADER
          ==================================================== */}

      <div className="wizard-section-header">

        <div>

          <h2>
            Key Vault & Qualys Configuration
          </h2>

          <p>
            Configure the Key Vault and Qualys credentials
            required for the workflow.
          </p>

        </div>

      </div>


      {/* ====================================================
          INFRASTRUCTURE INFORMATION
          ====================================================

          These values come from the FIRST API.

          POST /api/workflow/deploy

          User does NOT enter these values again.
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
              FUNCTION APP
              ================================================== */}

          <div className="configuration-field">

            <label>
              Function App Name
            </label>

            <input
              type="text"
              value={
                deploymentInfo?.function_app_name || ""
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
          KEY VAULT CONFIGURATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Key Vault Configuration
          </h3>

          <p>
            Enter the Key Vault information.
          </p>

        </div>


        <div className="configuration-grid">


          {/* ==================================================
              KEY VAULT NAME
              ================================================== */}

          <div className="configuration-field">

            <label htmlFor="key-vault-name">

              Key Vault Name

              <span className="required-mark">
                *
              </span>

            </label>

            <input
              id="key-vault-name"
              type="text"
              placeholder="Enter Key Vault name"
              value={
                formData?.key_vault_name || ""
              }
              onChange={(event) =>
                handleChange(
                  "key_vault_name",
                  event.target.value
                )
              }
            />

          </div>

        </div>

      </div>


      {/* ====================================================
          QUALYS CONFIGURATION
          ==================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Qualys Configuration
          </h3>

          <p>
            Enter the Qualys authentication details.
          </p>

        </div>


        <div className="configuration-grid">


          {/* ==================================================
              QUALYS USERNAME
              ================================================== */}

          <div className="configuration-field">

            <label htmlFor="qualys-username">

              Qualys Username

              <span className="required-mark">
                *
              </span>

            </label>

            <input
              id="qualys-username"
              type="text"
              placeholder="Enter Qualys username"
              value={
                formData?.qualys_username || ""
              }
              onChange={(event) =>
                handleChange(
                  "qualys_username",
                  event.target.value
                )
              }
            />

          </div>


          {/* ==================================================
              QUALYS PASSWORD
              ================================================== */}

          <div className="configuration-field">

            <label htmlFor="qualys-password">

              Qualys Password

              <span className="required-mark">
                *
              </span>

            </label>

            <input
              id="qualys-password"
              type="password"
              placeholder="Enter Qualys password"
              value={
                formData?.qualys_password || ""
              }
              onChange={(event) =>
                handleChange(
                  "qualys_password",
                  event.target.value
                )
              }
            />

          </div>


          {/* ==================================================
              QUALYS BASE URL
              ================================================== */}

          <div className="configuration-field">

            <label htmlFor="qualys-base-url">

              Qualys Base URL

              <span className="required-mark">
                *
              </span>

            </label>

            <input
              id="qualys-base-url"
              type="url"
              placeholder="https://qualysguard.qualys.com"
              value={
                formData?.qualys_base_url || ""
              }
              onChange={(event) =>
                handleChange(
                  "qualys_base_url",
                  event.target.value
                )
              }
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
            Key Vault configuration completed.
          </strong>

          <p>
            The Key Vault and Qualys configuration
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
          SETUP KEY VAULT BUTTON
          ==================================================== */}

      <div className="configuration-actions">

        <button
          type="button"
          className="primary-button"
          onClick={handleDeploy}
          disabled={isDeploying}
        >

          {isDeploying
            ? "Setting Up..."
            : "Setup Key Vault"}

        </button>

      </div>

    </div>

  );

}


export default KeyVaultConfiguration;