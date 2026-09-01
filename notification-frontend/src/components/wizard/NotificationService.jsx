// ============================================================
// NOTIFICATION SERVICE
// ============================================================
//
// STEP 8
//
// This is a separate component because Notification Service
// has its own ARM deployment API:
//
// POST /notification-arm/deploy
//
// The actual fields/API integration will be added here.
// ============================================================

function NotificationService({
  deploymentInfo,
}) {

  return (

    <div className="wizard-section">

      {/* ======================================================
          HEADER
          ====================================================== */}

      <div className="wizard-section-header">

        <div>

          <h2>
            Notification Service
          </h2>

          <p>
            Configure and deploy the Notification Service.
          </p>

        </div>

      </div>


      {/* ======================================================
          TEMPORARY CONTENT
          ====================================================== */}

      <div className="configuration-card">

        <div className="configuration-card-header">

          <h3>
            Notification Service Configuration
          </h3>

          <p>
            Notification Service configuration will be added
            here.
          </p>

        </div>

      </div>

    </div>

  );
}


export default NotificationService;