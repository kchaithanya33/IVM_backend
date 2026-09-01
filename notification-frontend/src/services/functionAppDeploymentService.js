// ============================================================
// FUNCTION APP DEPLOYMENT SERVICE
// ============================================================
//
// Calls the backend API:
//
// POST /api/deployment/function-app
//
// ============================================================

const FUNCTION_APP_DEPLOYMENT_URL =
  "http://localhost:8000/api/deployment/function-app";


// ============================================================
// DEPLOY FUNCTION APP
// ============================================================

export const deployFunctionApp = async (
  deploymentPayload
) => {

  try {

    console.log(
      "FUNCTION APP DEPLOYMENT REQUEST:",
      deploymentPayload
    );


    const response =
      await fetch(
        FUNCTION_APP_DEPLOYMENT_URL,
        {

          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body:
            JSON.stringify(
              deploymentPayload
            ),

        }
      );


    // ========================================================
    // RESPONSE
    // ========================================================

    let data;

    try {

      data =
        await response.json();

    } catch {

      data = {};

    }


    // ========================================================
    // ERROR
    // ========================================================

    if (!response.ok) {

      throw new Error(
        data.detail ||
        data.message ||
        "Function App deployment failed."
      );

    }


    // ========================================================
    // SUCCESS
    // ========================================================

    console.log(
      "FUNCTION APP DEPLOYMENT RESPONSE:",
      data
    );


    return data;

  } catch (error) {

    console.error(
      "Function App deployment service error:",
      error
    );

    throw error;

  }

};