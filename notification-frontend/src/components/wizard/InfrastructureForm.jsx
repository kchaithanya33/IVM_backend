// ============================================================
// ICONS
// ============================================================

function CheckIcon() {
  return (
    <svg
      className="field-check"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="1.6"
      />

      <path
        d="M8 12.2L10.6 14.7L16 9.5"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}


function ChevronDown() {
  return (
    <svg
      className="chevron-icon"
      viewBox="0 0 24 24"
      fill="none"
    >
      <path
        d="M6 9L12 15L18 9"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}


// ============================================================
// INFRASTRUCTURE FORM
// ============================================================

function InfrastructureForm({
  formData,
  onChange,
}) {

  return (

    <section className="infrastructure-form">

      {/* ====================================================
          DIVIDER
          ==================================================== */}

      <div className="section-divider" />


      <div className="form-grid">


        {/* ==================================================
            1. SUBSCRIPTION ID
            ================================================== */}

        <div className="form-field">

          <label>

            Subscription ID

            <span className="required">
              *
            </span>

          </label>


          <div className="input-wrapper">

            <input
              type="text"
              placeholder="string"
              value={
                formData.subscriptionId
              }
              onChange={(event) =>
                onChange(
                  "subscriptionId",
                  event.target.value
                )
              }
              required
            />

          </div>

        </div>


        {/* ==================================================
            2. RESOURCE GROUP NAME
            ================================================== */}

        <div className="form-field">

          <label>

            Resource Group Name

            <span className="required">
              *
            </span>

          </label>


          <div className="input-wrapper">

            <input
              type="text"
              placeholder="string"
              value={
                formData.resourceGroupName
              }
              onChange={(event) =>
                onChange(
                  "resourceGroupName",
                  event.target.value
                )
              }
              required
            />


            <CheckIcon />

          </div>

        </div>


        {/* ==================================================
            3. RESOURCE GROUP LOCATION
            ================================================== */}

        <div className="form-field">

          <label>

            Resource Group Location

            <span className="required">
              *
            </span>

          </label>


          <div className="input-wrapper">

            <input
              type="text"
              placeholder="string"
              value={
                formData.resourceGroupLocation
              }
              onChange={(event) =>
                onChange(
                  "resourceGroupLocation",
                  event.target.value
                )
              }
              required
            />

          </div>

        </div>


        {/* ==================================================
            4. STORAGE ACCOUNT NAME
            ================================================== */}

        <div className="form-field">

          <label>

            Storage Account Name

            <span className="required">
              *
            </span>

          </label>


          <div className="input-wrapper">

            <input
              type="text"
              placeholder="string"
              value={
                formData.storageAccountName
              }
              onChange={(event) =>
                onChange(
                  "storageAccountName",
                  event.target.value
                )
              }
              required
            />


            <CheckIcon />

          </div>

        </div>


        {/* ==================================================
            5. STORAGE ACCOUNT LOCATION
            ================================================== */}

        <div className="form-field">

          <label>

            Storage Account Location

            <span className="required">
              *
            </span>

          </label>


          <div className="select-wrapper">

            <select
              value={
                formData.storageAccountLocation
              }
              onChange={(event) =>
                onChange(
                  "storageAccountLocation",
                  event.target.value
                )
              }
              required
            >

              <option value="">
                string
              </option>

              <option value="eastus">
                East US
              </option>

              <option value="eastus2">
                East US 2
              </option>

              <option value="centralindia">
                Central India
              </option>

              <option value="canadacentral">
                Canada Central
              </option>

              <option value="westeurope">
                West Europe
              </option>

            </select>


            <ChevronDown />

          </div>

        </div>


        {/* ==================================================
            6. FUNCTION APP NAME
            ================================================== */}

        <div className="form-field">

          <label>

            Function App Name

            <span className="required">
              *
            </span>

          </label>


          <div className="input-wrapper">

            <input
              type="text"
              placeholder="string"
              value={
                formData.functionAppName
              }
              onChange={(event) =>
                onChange(
                  "functionAppName",
                  event.target.value
                )
              }
              required
            />


            <CheckIcon />

          </div>

        </div>


      </div>

    </section>

  );

}


export default InfrastructureForm;