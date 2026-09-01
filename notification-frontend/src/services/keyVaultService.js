// ============================================================
// KEY VAULT SERVICE
// ============================================================

const API_BASE_URL =
  "http://localhost:8000";


// ============================================================
// SETUP KEY VAULT
// ============================================================

export const setupKeyVault = async (
  payload
) => {

  const response = await fetch(
    `${API_BASE_URL}/api/key-vault/setup`,
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
        "Key Vault setup failed."
    );

  }


  // ==========================================================
  // SUCCESS
  // ==========================================================

  return data;

};