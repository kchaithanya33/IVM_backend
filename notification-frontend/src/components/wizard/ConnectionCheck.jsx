import { useState } from "react";

import { setupConnections } from "../../services/connectionService";


// ============================================================
// CONNECTION CHECK COMPONENT
// ============================================================

function ConnectionCheck({
  deploymentInfo,
  onComplete,
}) {

  // ==========================================================
  // STATE
  // ==========================================================

  const [isChecking, setIsChecking] =
    useState(false);

  const [connectionResult, setConnectionResult] =
    useState(null);

  const [connectionError, setConnectionError] =
    useState("");


  // ==========================================================
  // CHECK CONNECTIONS
  // ==========================================================

  const handleCheckConnections = async () => {

    // Prevent duplicate requests
    if (isChecking) {
      return;
    }


    setIsChecking(true);

    setConnectionError("");

    setConnectionResult(null);


    try {

      // ========================================================
      // VALIDATE DEPLOYMENT INFORMATION
      // ========================================================

      if (!deploymentInfo) {

        throw new Error(
          "Deployment information is not available."
        );

      }


      // ========================================================
      // VALIDATE SUBSCRIPTION
      // ========================================================

      if (
        !String(
          deploymentInfo.subscription_id || ""
        ).trim()
      ) {

        throw new Error(
          "Subscription ID is not available from the infrastructure deployment."
        );

      }


      // ========================================================
      // VALIDATE RESOURCE GROUP
      // ========================================================

      if (
        !String(
          deploymentInfo.resource_group_name || ""
        ).trim()
      ) {

        throw new Error(
          "Resource group name is not available from the infrastructure deployment."
        );

      }


      // ========================================================
      // VALIDATE LOCATION
      // ========================================================

      if (
        !String(
          deploymentInfo.location || ""
        ).trim()
      ) {

        throw new Error(
          "Location is not available from the infrastructure deployment."
        );

      }


      // ========================================================
      // DEBUG INFORMATION BEING SENT
      // ========================================================

      console.log(
        "========================================"
      );

      console.log(
        "DEPLOYMENT INFORMATION FOR CONNECTION API"
      );

      console.log(
        JSON.stringify(
          deploymentInfo,
          null,
          2
        )
      );

      console.log(
        "========================================"
      );


      // ========================================================
      // CALL CONNECTION API
      // ========================================================
      //
      // setupConnections() extracts:
      //
      // subscription_id
      // resource_group_name
      // location
      //
      // and sends them to:
      //
      // POST /api/connections/setup
      //
      // ========================================================

      const result =
        await setupConnections(
          deploymentInfo
        );


      // ========================================================
      // SAVE CONNECTION RESULT
      // ========================================================

      setConnectionResult(result);


      // ========================================================
      // CALLBACK TO PARENT
      // ========================================================

      if (onComplete) {

        onComplete(result);

      }

    } catch (error) {

      console.error(
        "Connection check error:",
        error
      );


      setConnectionError(
        error.message ||
          "Unable to check connections."
      );

    } finally {

      setIsChecking(false);

    }
  };


  // ==========================================================
  // EXTRACT CONNECTION LIST
  //
  // Supports:
  //
  // 1. Array response
  // 2. { connections: [] }
  // 3. { results: [] }
  // 4. { data: [] }
  //
  // ==========================================================

  const getConnections = () => {

    if (!connectionResult) {
      return [];
    }


    // Direct array

    if (
      Array.isArray(
        connectionResult
      )
    ) {

      return connectionResult;

    }


    // connections array

    if (
      Array.isArray(
        connectionResult.connections
      )
    ) {

      return connectionResult.connections;

    }


    // results array

    if (
      Array.isArray(
        connectionResult.results
      )
    ) {

      return connectionResult.results;

    }


    // data array

    if (
      Array.isArray(
        connectionResult.data
      )
    ) {

      return connectionResult.data;

    }


    return [];

  };


  const connections =
    getConnections();


  // ==========================================================
  // STATUS CLASS
  // ==========================================================

  const getStatusClass = (
    connection
  ) => {

    const status =
      String(
        connection?.status ||
          connection?.connection_status ||
          ""
      ).toLowerCase();


    const authenticated =
      connection?.authenticated ??
      connection?.is_authenticated;


    // --------------------------------------------------------
    // SUCCESS
    // --------------------------------------------------------

    if (
      authenticated === true ||
      status.includes(
        "authenticated"
      ) ||
      status === "connected"
    ) {

      return "connection-status success";

    }


    // --------------------------------------------------------
    // ERROR
    // --------------------------------------------------------

    if (
      status.includes(
        "not authenticated"
      ) ||
      status.includes(
        "failed"
      ) ||
      status.includes(
        "error"
      )
    ) {

      return "connection-status error";

    }


    // --------------------------------------------------------
    // WARNING
    // --------------------------------------------------------

    if (
      status.includes(
        "not connected"
      ) ||
      status.includes(
        "pending"
      )
    ) {

      return "connection-status warning";

    }


    return "connection-status";

  };


  // ==========================================================
  // STATUS TEXT
  // ==========================================================

  const getStatusText = (
    connection
  ) => {

    const status =
      connection?.status ||
      connection?.connection_status;


    if (status) {

      return status;

    }


    if (
      connection?.authenticated === true ||
      connection?.is_authenticated === true
    ) {

      return "Authenticated";

    }


    if (
      connection?.authenticated === false ||
      connection?.is_authenticated === false
    ) {

      return "Not Authenticated";

    }


    return "Unknown";

  };


  // ==========================================================
  // CONNECTION NAME
  // ==========================================================

  const getConnectionName = (
    connection,
    index
  ) => {

    return (
      connection?.name ||
      connection?.connection_name ||
      connection?.service ||
      connection?.type ||
      `Connection ${index + 1}`
    );

  };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <div className="wizard-section">


      {/* ====================================================
          HEADER
          ==================================================== */}

      <div className="wizard-section-header">

        <div>

          <h2>
            API Connections
          </h2>

          <p>
            Check the connection and
            authentication status of
            the required services.
          </p>

        </div>

      </div>


      {/* ====================================================
          DEPLOYMENT INFORMATION
          ====================================================
          
          These are READ ONLY values.

          They came from the first API:
          
          POST /api/workflow/deploy
          
          The user does NOT enter them again.
          ==================================================== */}

      <div className="connection-deployment-info">


        {/* ==================================================
            SUBSCRIPTION
            ================================================== */}

        <div className="connection-info-item">

          <span className="connection-info-label">
            Subscription
          </span>

          <span className="connection-info-value">

            {deploymentInfo?.subscription_id ||
              "—"}

          </span>

        </div>


        {/* ==================================================
            RESOURCE GROUP
            ================================================== */}

        <div className="connection-info-item">

          <span className="connection-info-label">
            Resource Group
          </span>

          <span className="connection-info-value">

            {deploymentInfo?.resource_group_name ||
              "—"}

          </span>

        </div>


        {/* ==================================================
            LOCATION
            ================================================== */}

        <div className="connection-info-item">

          <span className="connection-info-label">
            Location
          </span>

          <span className="connection-info-value">

            {deploymentInfo?.location ||
              "—"}

          </span>

        </div>

      </div>


      {/* ====================================================
          CHECK BUTTON
          ==================================================== */}

      <div className="connection-check-actions">

        <button
          type="button"
          className="primary-button"
          onClick={
            handleCheckConnections
          }
          disabled={isChecking}
        >

          {isChecking
            ? "Checking Connections..."
            : "Check Connections"}

        </button>

      </div>


      {/* ====================================================
          ERROR
          ==================================================== */}

      {connectionError && (

        <div className="connection-error">

          <strong>
            Connection Check Failed
          </strong>

          <p>
            {connectionError}
          </p>

        </div>

      )}


      {/* ====================================================
          RESULTS
          ==================================================== */}

      {connectionResult && (

        <div className="connection-results">


          {/* ==================================================
              RESULT HEADER
              ================================================== */}

          <div className="connection-results-header">

            <div>

              <h3>
                Connection Status
              </h3>

              <p>
                Current status of all
                configured connections.
              </p>

            </div>

          </div>


          {/* ==================================================
              NO CONNECTION ARRAY
              ================================================== */}

          {connections.length === 0 && (

            <div className="connection-result-message">

              <p>
                Connection check completed.
              </p>

              <pre>
                {JSON.stringify(
                  connectionResult,
                  null,
                  2
                )}
              </pre>

            </div>

          )}


          {/* ==================================================
              CONNECTION TABLE
              ================================================== */}

          {connections.length > 0 && (

            <div className="connection-table-wrapper">

              <table className="connection-table">

                <thead>

                  <tr>

                    <th>
                      Connection
                    </th>

                    <th>
                      Status
                    </th>

                    <th>
                      Authentication
                    </th>

                    <th>
                      Details
                    </th>

                  </tr>

                </thead>


                <tbody>

                  {connections.map(
                    (
                      connection,
                      index
                    ) => {

                      const status =
                        getStatusText(
                          connection
                        );


                      const authenticated =
                        connection?.authenticated ??
                        connection?.is_authenticated;


                      return (

                        <tr
                          key={
                            connection?.id ||
                            connection?.name ||
                            index
                          }
                        >


                          {/* =================================
                              CONNECTION NAME
                              ================================= */}

                          <td>

                            <strong>

                              {getConnectionName(
                                connection,
                                index
                              )}

                            </strong>

                          </td>


                          {/* =================================
                              STATUS
                              ================================= */}

                          <td>

                            <span
                              className={
                                getStatusClass(
                                  connection
                                )
                              }
                            >

                              {status}

                            </span>

                          </td>


                          {/* =================================
                              AUTHENTICATION
                              ================================= */}

                          <td>

                            {authenticated === true && (

                              <span className="connection-status success">

                                Authenticated

                              </span>

                            )}


                            {authenticated === false && (

                              <span className="connection-status error">

                                Not Authenticated

                              </span>

                            )}


                            {authenticated === undefined && (

                              <span className="connection-status">

                                —

                              </span>

                            )}

                          </td>


                          {/* =================================
                              DETAILS
                              ================================= */}

                          <td>

                            {connection?.message ||
                              connection?.details ||
                              connection?.error ||
                              "—"}

                          </td>

                        </tr>

                      );

                    }
                  )}

                </tbody>

              </table>

            </div>

          )}

        </div>

      )}

    </div>

  );
}


export default ConnectionCheck;