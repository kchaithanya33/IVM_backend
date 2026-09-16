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
            USER CAN EDIT
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
              placeholder="Enter Subscription ID"
              value={
                formData.subscriptionId || ""
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
            USER CAN EDIT
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
              placeholder="Enter Resource Group Name"
              value={
                formData.resourceGroupName || ""
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
            FIXED VALUE - USER CANNOT EDIT
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
              value="canadacentral"
              readOnly
              disabled
            />

            <CheckIcon />

          </div>

        </div>


        {/* ==================================================
            4. STORAGE ACCOUNT NAME
            FIXED VALUE - USER CANNOT EDIT
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
              value="ivmstorageaccount"
              readOnly
              disabled
            />

            <CheckIcon />

          </div>

        </div>


        {/* ==================================================
            5. STORAGE ACCOUNT LOCATION
            FIXED VALUE - USER CANNOT EDIT
            ================================================== */}

        <div className="form-field">

          <label>
            Storage Account Location

            <span className="required">
              *
            </span>
          </label>


          <div className="input-wrapper">

            <input
              type="text"
              value="canadacentral"
              readOnly
              disabled
            />

            <CheckIcon />

          </div>

        </div>


        {/* ==================================================
            6. FUNCTION APP NAME
            FIXED VALUE - USER CANNOT EDIT
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
              value="ivmfunctionapp"
              readOnly
              disabled
            />

            <CheckIcon />

          </div>

        </div>

      </div>

    </section>
  );
}


export default InfrastructureForm;