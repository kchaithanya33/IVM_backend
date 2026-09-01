function WizardFooter({
  currentStep,

  onBack,

  onNext,

  onDeploy,

  onDeploymentNext,

  onApplicationConfigurationNext,

  onKeyVaultNext,

  onConnectionNext,

  onFunctionDeploymentNext,

  onNotificationARMDeploy,

  onNotificationARMNext,

  onScopingDeploy,

  onScopingNext,

  isDeploying,

  completedSteps = [],
}) {

  // ============================================================
  // STEP 1 - INFRASTRUCTURE DETAILS
  // ============================================================

  if (currentStep === 1) {

    return (
      <div className="wizard-footer">

        <div />

        <button
          type="button"
          className="next-button"
          onClick={onNext}
          disabled={isDeploying}
        >
          Next
          <span>›</span>
        </button>

      </div>
    );
  }


  // ============================================================
  // STEP 2 - CONFIGURATION REVIEW
  // ============================================================

  if (currentStep === 2) {

    return (
      <div className="wizard-footer">

        <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={isDeploying}
        >
          Back
        </button>

        <div className="wizard-footer-actions">

          <button
            type="button"
            className="next-button"
            onClick={onDeploy}
            disabled={isDeploying}
          >
            {isDeploying
              ? "Deploying..."
              : "Deploy"}
          </button>

        </div>

      </div>
    );
  }


  // ============================================================
  // STEP 3 - DEPLOYMENT STATUS
  // ============================================================

  if (currentStep === 3) {

    return (
      <div className="wizard-footer">

        <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={isDeploying}
        >
          Back
        </button>

        <button
          type="button"
          className="next-button"
          onClick={onDeploymentNext}
          disabled={isDeploying}
        >
          Next
          <span>›</span>
        </button>

      </div>
    );
  }


  // ============================================================
  // STEP 4 - APPLICATION CONFIGURATION
  // ============================================================

  if (currentStep === 4) {

    return (
      <div className="wizard-footer">

        <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={isDeploying}
        >
          Back
        </button>

        <button
          type="button"
          className="next-button"
          onClick={onApplicationConfigurationNext}
          disabled={isDeploying}
        >
          Next
          <span>›</span>
        </button>

      </div>
    );
  }


  // ============================================================
  // STEP 5 - API CONNECTION CHECK
  // ============================================================

  if (currentStep === 5) {

    return (
      <div className="wizard-footer">

        <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={isDeploying}
        >
          Back
        </button>

        <button
          type="button"
          className="next-button"
          onClick={onConnectionNext}
          disabled={isDeploying}
        >
          Next
          <span>›</span>
        </button>

      </div>
    );
  }


  // ============================================================
  // STEP 6 - KEY VAULT + QUALYS
  //
  // KEY VAULT DEPLOYMENT IS OPTIONAL.
  //
  // NEXT MUST ALWAYS WORK.
  // ============================================================

  if (currentStep === 6) {

    return (
      <div className="wizard-footer">

        <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={isDeploying}
        >
          Back
        </button>

        <div className="wizard-footer-actions">

          <button
            type="button"
            className="next-button"
            onClick={onKeyVaultNext}
            disabled={isDeploying}
          >
            Next
            <span>›</span>
          </button>

        </div>

      </div>
    );
  }


  // ============================================================
  // STEP 7 - FUNCTION DEPLOYMENT
  //
  // DEPLOY:
  //   Calls Function App deployment API.
  //
  // NEXT:
  //   Moves to Step 8 only after successful deployment.
  // ============================================================

  // ============================================================
// STEP 7 - FUNCTION DEPLOYMENT
//
// Both Deploy and Next are disabled ONLY while deploying.
// Otherwise:
//   - Deploy works
//   - Next works
// ============================================================

if (currentStep === 7) {

  return (
    <div className="wizard-footer">

      {/* BACK */}

      <button
        type="button"
        className="back-button"
        onClick={onBack}
        disabled={isDeploying}
      >
        Back
      </button>


      <div className="wizard-footer-actions">

        {/* FUNCTION APP DEPLOY */}

        <button
          type="button"
          className="secondary-button"
          onClick={onDeploy}
          disabled={isDeploying}
        >
          {isDeploying
            ? "Deploying..."
            : completedSteps.includes(7)
            ? "Deployed"
            : "Deploy"}
        </button>


        {/* NEXT */}

        <button
          type="button"
          className="next-button"
          onClick={onFunctionDeploymentNext}
          disabled={isDeploying}
        >
          Next
          <span>›</span>
        </button>

      </div>

    </div>
  );
}


  // ============================================================
  // STEP 8 - NOTIFICATION SERVICE
  //
  // DEPLOY AND NEXT ARE COMPLETELY SEPARATE.
  // ============================================================

  if (currentStep === 8) {

    return (
      <div className="wizard-footer">

      <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={isDeploying}
        >
          Back
        </button>

        <div className="wizard-footer-actions">

          {/* NEXT */}

          <button
            type="button"
            className="next-button"
            onClick={onNotificationARMNext}
            disabled={isDeploying}
          >
            Next
            <span>›</span>
          </button>

        </div>

      </div>
    );
  }


  // ============================================================
  // STEP 9 - SCOPING CONFIGURATION
  //
  // DEPLOYMENT IS HANDLED INSIDE ScopingConfiguration.jsx.
  //
  // The bottom button ONLY navigates to the next step.
  // ============================================================

  if (currentStep === 9) {

    return (
      <div className="wizard-footer">

        {/* BACK */}

        <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={isDeploying}
        >
          Back
        </button>


        {/* NEXT - NAVIGATION ONLY */}

        <button
          type="button"
          className="next-button"
          onClick={onScopingNext}
          disabled={isDeploying}
        >
          Next
          <span>›</span>
        </button>

      </div>
    );
  }


  // ============================================================
  // DEFAULT
  // ============================================================

  return (
    <div className="wizard-footer">

      {currentStep > 1 && (

        <button
          type="button"
          className="back-button"
          onClick={onBack}
          disabled={isDeploying}
        >
          Back
        </button>

      )}

    </div>
  );
}


export default WizardFooter;