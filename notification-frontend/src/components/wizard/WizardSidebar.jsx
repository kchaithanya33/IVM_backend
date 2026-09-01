function WizardSidebar({
  currentStep,
  completedSteps = [],
  onStepClick,
}) {

  // ============================================================
  // WIZARD STEPS
  // ============================================================

  const steps = [

    {
      id: 1,
      title: "Infrastructure Details",
    },

    {
      id: 2,
      title: "Application Configuration",
    },

    {
      id: 3,
      title: "Deployment Status",
    },

    {
      id: 4,
      title: "Application Configuration",
    },

    {
      id: 5,
      title: "API Connection Check",
    },

    {
      id: 6,
      title: "Key Vault & Qualys",
    },

    {
      id: 7,
      title: "Function Deployment",
    },

    {
      id: 8,
      title: "Common Services",
    },

    {
      id: 9,
      title: "Scoping Service",
    },

  ];


  // ============================================================
  // TOTAL STEPS
  // ============================================================

  const totalSteps =
    steps.length;


  // ============================================================
  // STEP STATUS
  // ============================================================

  const getStepStatus = (
    stepId
  ) => {

    if (
      completedSteps.includes(stepId)
    ) {

      return "completed";

    }


    if (
      currentStep === stepId
    ) {

      return "active";

    }


    return "locked";

  };


  // ============================================================
  // OVERALL PROGRESS
  // ============================================================

  const completedCount =
    completedSteps.filter(
      (stepId) =>
        steps.some(
          (step) =>
            step.id === stepId
        )
    ).length;


  const overallProgress =
    Math.round(
      (completedCount / totalSteps) *
        100
    );


  // ============================================================
  // HANDLE STEP CLICK
  // ============================================================

  const handleStepClick = (stepId) => {

    if (onStepClick) {

      onStepClick(stepId);

    }

  };


  // ============================================================
  // RENDER
  // ============================================================

  return (

    <aside className="wizard-sidebar">

      {/* ======================================================
          SIDEBAR TITLE
          ====================================================== */}

      <h2 className="sidebar-title">
        Summary
      </h2>


      {/* ======================================================
          STEPS
          ====================================================== */}

      <div className="sidebar-steps">

        {steps.map(
          (step, index) => {

            const status =
              getStepStatus(
                step.id
              );


            return (

              <div
                key={step.id}
                className="sidebar-step-wrapper"
              >

                {/* ============================================
                    STEP
                    ============================================ */}

                <div
                  className={`sidebar-step ${status}`}
                  onClick={() =>
                    handleStepClick(step.id)
                  }
                  role="button"
                  tabIndex={0}
                  onKeyDown={(event) => {

                    if (
                      event.key === "Enter" ||
                      event.key === " "
                    ) {

                      handleStepClick(
                        step.id
                      );

                    }

                  }}
                >

                  {/* ==========================================
                      STEP NUMBER
                      ========================================== */}

                  <div className="step-number">

                    {status ===
                    "completed"

                      ? "✓"

                      : step.id}

                  </div>


                  {/* ==========================================
                      STEP INFORMATION
                      ========================================== */}

                  <div className="step-information">

                    <div className="step-title">
                      {step.title}
                    </div>


                    <div className="step-status">

                      {status ===
                        "completed" &&
                        "Completed"}


                      {status ===
                        "active" &&
                        "(In Progress)"}


                      {status ===
                        "locked" &&
                        "(Locked)"}

                    </div>

                  </div>

                </div>


                {/* ============================================
                    CONNECTING LINE
                    ============================================ */}

                {index <
                  steps.length - 1 && (

                  <div
                    className={`step-line ${
                      status ===
                      "completed"
                        ? "completed-line"
                        : ""
                    }`}
                  />

                )}

              </div>

            );

          }
        )}

      </div>


      {/* ======================================================
          APPLICATION CONFIGURATION PROGRESS
          ====================================================== */}

      {currentStep === 4 && (

        <div className="wizard-progress-card">

          <h3>
            Application Configuration Progress
          </h3>


          <div className="progress-bar-container">

            <div
              className="progress-bar"
              style={{
                width: "16%",
              }}
            />

          </div>


          <div className="progress-info">

            <span>
              Page 1 of 6
            </span>


            <span>
              1 - 15 of 86
            </span>

          </div>

        </div>

      )}


      {/* ======================================================
          OVERALL PROGRESS
          ====================================================== */}

      <div className="wizard-progress-card">

        <h3>
          Overall Progress
        </h3>


        <div className="progress-bar-container">

          <div
            className="progress-bar"
            style={{
              width:
                `${overallProgress}%`,
            }}
          />

        </div>


        <div className="progress-info">

          <span>

            {completedCount} of{" "}
            {totalSteps} steps
            completed

          </span>


          <span>
            {overallProgress}%
          </span>

        </div>

      </div>

    </aside>

  );

}


export default WizardSidebar;