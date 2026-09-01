// ============================================================
// NOTIFICATION ARM SERVICE
// ============================================================

const API_BASE_URL = "http://localhost:8000";


// ============================================================
// DEPLOY NOTIFICATION ARM
//
// POST /notification-arm/deploy
// ============================================================

export const deployNotificationARM = async (
  payload
) => {

  const response =
    await fetch(
      `${API_BASE_URL}/notification-arm/deploy`,
      {

        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        body:
          JSON.stringify(payload),

      }
    );


  // ==========================================================
  // READ RESPONSE
  // ==========================================================

  let data;

  try {

    data =
      await response.json();

  } catch {

    data = {};

  }


  // ==========================================================
  // HANDLE ERROR
  // ==========================================================

  if (!response.ok) {

    throw new Error(
      data.detail ||
      data.message ||
      "Notification ARM deployment failed."
    );

  }


  // ==========================================================
  // RETURN BACKEND RESPONSE
  // ==========================================================

  return data;

};