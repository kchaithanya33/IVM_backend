// ============================================================
// CONNECTION SERVICE
// ============================================================
//
// Handles:
// POST /api/connections/setup
//
// subscription_id, resource_group_name, storage_account_name
// and location are taken automatically from the successful
// infrastructure deployment.
//
// ============================================================

const API_BASE_URL = "http://localhost:8000";


// ============================================================
// CHECK / SETUP CONNECTIONS
// ============================================================

export const setupConnections = async (deploymentInfo) => {

  // ==========================================================
  // VALIDATE DEPLOYMENT INFORMATION OBJECT
  // ==========================================================

  if (!deploymentInfo) {
    throw new Error(
      "Deployment information is not available."
    );
  }


  // ==========================================================
  // GET VALUES FROM FIRST DEPLOYMENT API
  // ==========================================================

  const subscriptionId =
    String(
      deploymentInfo.subscription_id || ""
    ).trim();

  const resourceGroupName =
    String(
      deploymentInfo.resource_group_name || ""
    ).trim();

  const storageAccountName =
    String(
      deploymentInfo.storage_account_name || ""
    ).trim();

  const location =
    String(
      deploymentInfo.location || ""
    ).trim();


  // ==========================================================
  // VALIDATE REQUIRED VALUES
  // ==========================================================

  if (!subscriptionId) {
    throw new Error(
      "Subscription ID is missing from the infrastructure deployment."
    );
  }

  if (!resourceGroupName) {
    throw new Error(
      "Resource group name is missing from the infrastructure deployment."
    );
  }

  if (!storageAccountName) {
    throw new Error(
      "Storage account name is missing from the infrastructure deployment."
    );
  }

  if (!location) {
    throw new Error(
      "Location is missing from the infrastructure deployment."
    );
  }


  // ==========================================================
  // BUILD CONNECTION API PAYLOAD
  // ==========================================================
  //
  // These values are NOT entered again by the user.
  //
  // They come from:
  //
  // POST /api/workflow/deploy
  //
  // ==========================================================

  const payload = {
    subscription_id: subscriptionId,
    resource_group_name: resourceGroupName,
    storage_account_name: storageAccountName,
    location: location,
  };


  // ==========================================================
  // DEBUG REQUEST
  // ==========================================================

  console.log(
    "========================================"
  );

  console.log(
    "CONNECTION SETUP PAYLOAD"
  );

  console.log(
    JSON.stringify(
      payload,
      null,
      2
    )
  );

  console.log(
    "========================================"
  );


  // ==========================================================
  // CALL CONNECTION API
  // ==========================================================

  const response = await fetch(
    `${API_BASE_URL}/api/connection`,
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
  // DEBUG RESPONSE
  // ==========================================================

  console.log(
    "========================================"
  );

  console.log(
    "CONNECTION SETUP RESPONSE"
  );

  console.log(
    JSON.stringify(
      data,
      null,
      2
    )
  );

  console.log(
    "========================================"
  );


  // ==========================================================
  // HANDLE BACKEND ERROR
  // ==========================================================

  if (!response.ok) {
    throw new Error(
      data.detail ||
        data.message ||
        "Connection setup failed."
    );
  }


  // ==========================================================
  // RETURN BACKEND RESPONSE
  // ==========================================================

  return data;
};


// ============================================================
// DEFAULT EXPORT
// ============================================================

export default {
  setupConnections,
};