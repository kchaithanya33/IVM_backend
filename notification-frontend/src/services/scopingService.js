
// ============================================================
// SCOPING DEPLOYMENT SERVICE
// ============================================================
//
// Calls the FastAPI Scoping deployment endpoint:
//
// POST /scoping/deploy
//
// ============================================================

const API_BASE_URL = "http://localhost:8000";


// ============================================================
// DEPLOY SCOPING
// ============================================================

export const deployScoping = async (payload) => {

  const response = await fetch(
    `${API_BASE_URL}/scoping/deploy`,
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(payload),
    }
  );


  // ==========================================================
  // READ RESPONSE
  // ==========================================================

  let data;

  try {

    data = await response.json();

  } catch {

    data = {};

  }


  // ==========================================================
  // ERROR
  // ==========================================================

  if (!response.ok) {

    throw new Error(
      data.detail ||
      data.message ||
      "Scoping deployment failed."
    );

  }


  // ==========================================================
  // SUCCESS
  // ==========================================================

  return data;

};
