
function WizardHeader({ currentStep }) {

  const headers = {

    // ==========================================================
    // STEP 1
    // ==========================================================

    1: {
      title: "Infrastructure Details",
      description:
        "Provide the infrastructure details required for deployment.",
    },


    // ==========================================================
    // STEP 2
    // ==========================================================

    2: {
      title: "Application Configuration",
    },


    // ==========================================================
    // STEP 3
    // ==========================================================

    3: {
      title: "Deployment Status",
      description:
        "Review the status of the infrastructure deployment.",
    },


    // ==========================================================
    // STEP 4
    // ==========================================================

    4: {
      title: "Application Configuration",
      description:
        "Provide values for all application configuration settings.",
    },


    // ==========================================================
    // STEP 5
    // ==========================================================

    5: {
      title: "API Connection Check",
      description:
        "Verify the required API connections before continuing.",
    },


    // ==========================================================
    // STEP 6
    // KEY VAULT + QUALYS
    // ==========================================================

    6: {
      title: "Key Vault & Qualys Configuration",
      description:
        "Configure the Key Vault and Qualys settings required for deployment.",
    },


    // ==========================================================
    // STEP 7
    // FUNCTION DEPLOYMENT
    // ==========================================================

    7: {
      title: "Function Deployment",
      description:
        "Proceed to the Common Services deployment configuration.",
    },


    // ==========================================================
    // STEP 8
    // COMMON SERVICES
    // ==========================================================

    8: {
      title: "Common Services Configuration",
      description:
        "Review the Common Services configuration before deployment.",
    },


    // ==========================================================
    // STEP 9
    // SCOPING SERVICE
    // ==========================================================

    9: {
      title: "Scoping Service Configuration",
      description:
        "Review the Scoping Service configuration before deployment.",
    },

  };


  const currentHeader =
    headers[currentStep] || headers[1];


  return (

    <div className="wizard-header">

      <h1>
        {currentHeader.title}
      </h1>

      <p>
        {currentHeader.description}
      </p>

    </div>

  );

}


export default WizardHeader;
