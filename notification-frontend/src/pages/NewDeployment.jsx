import { useState } from "react";

// ============================================================
// SERVICES
// ============================================================

import {
  setupKeyVault,
} from "../services/keyVaultService";

import {
  deployNotificationARM,
} from "../services/notificationArmService";

// ============================================================
// COMPONENTS
// ============================================================

import PageLayout from "../components/layout/PageLayout";

import WizardSidebar from "../components/wizard/WizardSidebar";

import InfrastructureForm from "../components/wizard/InfrastructureForm";

import ConfigurationForm from "../components/wizard/ConfigurationForm";

import DeploymentResult from "../components/wizard/DeploymentResult";

import ApplicationConfiguration from "../components/wizard/ApplicationConfiguration";

import ConnectionCheck from "../components/wizard/ConnectionCheck";

import KeyVaultConfiguration from "../components/wizard/KeyVaultConfiguration";

import FunctionDeployment from "../components/wizard/FunctionDeployment";

import NotificationARMConfiguration from "../components/wizard/NotificationARMConfiguration";

import WizardFooter from "../components/wizard/WizardFooter";

import ScopingConfiguration from "../components/wizard/ScopingConfiguration";


// ============================================================
// NEW DEPLOYMENT
// ============================================================

function NewDeployment() {

  // ==========================================================
  // WIZARD STATE
  // ==========================================================

  const [currentStep, setCurrentStep] =
    useState(1);

  const [completedSteps, setCompletedSteps] =
    useState([]);


  // ==========================================================
  // INFRASTRUCTURE DEPLOYMENT STATE
  // ==========================================================

  const [isDeploying, setIsDeploying] =
    useState(false);

  const [deploymentResult, setDeploymentResult] =
    useState(null);

  const [deploymentError, setDeploymentError] =
    useState("");


  // ==========================================================
  // CONFIGURATION DEPLOYMENT STATE
  // ==========================================================

  const [
    isConfigurationDeploying,
    setIsConfigurationDeploying,
  ] = useState(false);

  const [
    configurationDeploymentResult,
    setConfigurationDeploymentResult,
  ] = useState(null);

  const [
    configurationDeploymentError,
    setConfigurationDeploymentError,
  ] = useState("");


  // ==========================================================
  // CONNECTION CHECK STATE
  // ==========================================================

  const [
    isCheckingConnections,
    setIsCheckingConnections,
  ] = useState(false);

  const [
    connectionCheckResult,
    setConnectionCheckResult,
  ] = useState(null);

  const [
    connectionCheckError,
    setConnectionCheckError,
  ] = useState("");


  // ==========================================================
  // KEY VAULT STATE
  // ==========================================================

  const [
    isKeyVaultDeploying,
    setIsKeyVaultDeploying,
  ] = useState(false);

  const [
    keyVaultResult,
    setKeyVaultResult,
  ] = useState(null);

  const [
    keyVaultError,
    setKeyVaultError,
  ] = useState("");


  // ==========================================================
  // FUNCTION APP DEPLOYMENT STATE
  // ==========================================================

  const [
    isFunctionDeploying,
    setIsFunctionDeploying,
  ] = useState(false);

  const [
    functionDeploymentResult,
    setFunctionDeploymentResult,
  ] = useState(null);

  const [
    functionDeploymentError,
    setFunctionDeploymentError,
  ] = useState("");


  // ==========================================================
  // NOTIFICATION ARM STATE
  // ==========================================================

  const [
    isNotificationARMDeploying,
    setIsNotificationARMDeploying,
  ] = useState(false);

  const [
    notificationARMResult,
    setNotificationARMResult,
  ] = useState(null);

  const [
    notificationARMError,
    setNotificationARMError,
  ] = useState("");


  // ==========================================================
  // SCOPING DEPLOYMENT STATE
  // ==========================================================

  const [
    isScopingDeploying,
    setIsScopingDeploying,
  ] = useState(false);

  const [
    scopingResult,
    setScopingResult,
  ] = useState(null);

  const [
    scopingError,
    setScopingError,
  ] = useState("");


  // ==========================================================
  // RESOURCE INFORMATION
  // ==========================================================

  const [
    deployedResourceInfo,
    setDeployedResourceInfo,
  ] = useState({

    subscription_id: "",

    resource_group_name: "",

    location: "",

    storage_account_name: "",

    function_app_name: "",

  });


  // ==========================================================
  // INFRASTRUCTURE FORM DATA
  // ==========================================================

  const [formData, setFormData] =
    useState({

      subscriptionId: "",

      resourceGroupName: "",

      resourceGroupLocation: "",

      storageAccountName: "",

      storageAccountLocation: "",

      functionAppName: "",

    });


  // ==========================================================
  // APPLICATION CONFIGURATION
  // ==========================================================

  const [
    applicationConfigurations,
    setApplicationConfigurations,
  ] = useState({});


  // ==========================================================
  // EMAIL CONFIGURATION
  // ==========================================================

  const [
    emailConfigurations,
    setEmailConfigurations,
  ] = useState([]);


  // ==========================================================
  // NOTIFICATION CONFIGURATION
  // ==========================================================

  const [
    notificationConfigurations,
    setNotificationConfigurations,
  ] = useState([]);


  // ==========================================================
  // TEAMS CONFIGURATION
  // ==========================================================

  const [
    teamsConfigurations,
    setTeamsConfigurations,
  ] = useState([]);


  // ==========================================================
  // KEY VAULT + QUALYS FORM DATA
  // ==========================================================

  const [
    keyVaultFormData,
    setKeyVaultFormData,
  ] = useState({

    key_vault_name: "",

    qualys_username: "",

    qualys_password: "",

    qualys_base_url: "",

  });


  // ==========================================================
  // NOTIFICATION ARM FIXED CONFIGURATION
  // ==========================================================

  const notificationARMConfiguration = {

    logic_app_name:
      "notification-service",

    completion_logic_app_name:
      "notification-completion",

    notification_followup_logic_app_name:
      "notification-followup",

    followup_queue_name:
      "taskreminder",

    notification_log_table_name:
      "NotificationLogs",

    notification_status_table_name:
      "NotificationStatus",

    azure_tables_connection_name:
      "azuretables-1",

    azure_queues_connection_name:
      "azurequeues-1",

    office365_connection_name:
      "office365-1",

    teams_connection_name:
      "teams-1",

  };


  // ==========================================================
  // SCOPING FIXED CONFIGURATION
  // ==========================================================

  const scopingConfiguration = {

    logic_app_name:
      "LA-Scoping-00",

    scoping01_logic_app_name:
      "LA-Scoping-01",

    scoping02_logic_app_name:
      "LA-Scoping-02",

    table_connection_name:
      "azuretables-1",

    queue_connection_name:
      "azurequeues-1",

    sharepoint_connection_name:
      "sharepointonline-1",

    notification_log_table_name:
      "NotificationLogs",

    notification_status_table_name:
      "NotificationStatus",

    queue_name:
      "scopingschedulequeue",

    authscan_queue_name:
      "authscan00",

  };


  // ==========================================================
  // SCOPING USER CONFIGURATION
  // ==========================================================

  const [
    scopingFormData,
    setScopingFormData,
  ] = useState({

    sharepoint_url: "",

    callback_secret_key: "",

    completion_logic_app_url: "",

  });


  // ==========================================================
  // INFRASTRUCTURE CHANGE
  // ==========================================================

  const handleChange = (
    field,
    value
  ) => {

    setFormData(
      (previous) => ({

        ...previous,

        [field]: value,

      })
    );

  };


  // ==========================================================
  // KEY VAULT CHANGE
  // ==========================================================

  const handleKeyVaultChange = (
    field,
    value
  ) => {

    setKeyVaultFormData(
      (previous) => ({

        ...previous,

        [field]: value,

      })
    );

  };


  // ==========================================================
  // SCOPING FORM CHANGE
  // ==========================================================

  const handleScopingChange = (
    field,
    value
  ) => {

    setScopingFormData(
      (previous) => ({

        ...previous,

        [field]: value,

      })
    );

  };


  // ==========================================================
  // APPLICATION CONFIGURATION CHANGE
  // ==========================================================

  const handleApplicationConfigurationChange =
    (
      payload,
      legacyValue
    ) => {

      if (!payload) {

        return;

      }


      if (
        typeof payload === "number" ||
        typeof payload === "string"
      ) {

        const id = payload;

        const value =
          legacyValue;

        setApplicationConfigurations(
          (previous) => ({

            ...previous,

            [id]: value,

          })
        );

        return;

      }


      setApplicationConfigurations(
        (previous) => ({

          ...previous,

          [payload.id]: payload,

        })
      );

    };


  // ==========================================================
  // EMAIL CONFIGURATION CHANGE
  // ==========================================================

  const handleEmailConfigurationChange =
    (update) => {

      setEmailConfigurations(
        (previous) => {

          if (
            typeof update === "function"
          ) {

            const result =
              update(previous);

            return Array.isArray(result)
              ? result
              : previous;

          }


          if (
            Array.isArray(update)
          ) {

            return update;

          }


          if (
            update !== undefined &&
            update !== null
          ) {

            return [
              ...previous,
              update,
            ];

          }


          return previous;

        }
      );

    };


  // ==========================================================
  // NOTIFICATION CONFIGURATION CHANGE
  // ==========================================================

  const handleNotificationConfigurationChange =
    (update) => {

      setNotificationConfigurations(
        (previous) => {

          if (
            typeof update === "function"
          ) {

            const result =
              update(previous);

            return Array.isArray(result)
              ? result
              : previous;

          }


          if (
            Array.isArray(update)
          ) {

            return update;

          }


          if (
            update !== undefined &&
            update !== null
          ) {

            return [
              ...previous,
              update,
            ];

          }


          return previous;

        }
      );

    };


  // ==========================================================
  // TEAMS CONFIGURATION CHANGE
  // ==========================================================

  const handleTeamsConfigurationChange =
    (update) => {

      setTeamsConfigurations(
        (previous) => {

          if (
            typeof update === "function"
          ) {

            const result =
              update(previous);

            return Array.isArray(result)
              ? result
              : previous;

          }


          if (
            Array.isArray(update)
          ) {

            return update;

          }


          if (
            update !== undefined &&
            update !== null
          ) {

            return [
              ...previous,
              update,
            ];

          }


          return previous;

        }
      );

    };


  // ==========================================================
  // STEP 1 -> STEP 2
  // ==========================================================

  const handleNext = () => {

    const requiredFields = [

      "subscriptionId",

      "resourceGroupName",

      "resourceGroupLocation",

      "storageAccountName",

      "storageAccountLocation",

      "functionAppName",

    ];


    const missingFields =
      requiredFields.filter(
        (field) =>
          !String(
            formData[field] || ""
          ).trim()
      );


    if (
      missingFields.length > 0
    ) {

      alert(
        "Please fill in all required fields before proceeding."
      );

      return;

    }


    setCompletedSteps(
      (previous) => {

        if (
          previous.includes(1)
        ) {

          return previous;

        }


        return [
          ...previous,
          1,
        ];

      }
    );


    setCurrentStep(2);

  };


  // ==========================================================
  // STEP 2 -> STEP 3
  // ==========================================================

  const handleConfigurationNext =
    () => {

      setCompletedSteps(
        (previous) => {

          if (
            previous.includes(2)
          ) {

            return previous;

          }


          return [
            ...previous,
            2,
          ];

        }
      );


      setCurrentStep(3);

    };


  // ==========================================================
  // BACK
  // ==========================================================

  const handleBack = () => {

    if (
      isDeploying ||
      isConfigurationDeploying ||
      isCheckingConnections ||
      isKeyVaultDeploying ||
      isFunctionDeploying ||
      isNotificationARMDeploying ||
      isScopingDeploying
    ) {

      return;

    }


    if (currentStep === 2) {

      setCurrentStep(1);

      return;

    }


    if (currentStep === 3) {

      setCurrentStep(2);

      return;

    }


    if (currentStep === 4) {

      setCurrentStep(3);

      return;

    }


    if (currentStep === 5) {

      setCurrentStep(4);

      return;

    }


    if (currentStep === 6) {

      setCurrentStep(5);

      return;

    }


    if (currentStep === 7) {

      setCurrentStep(6);

      return;

    }


    if (currentStep === 8) {

      setCurrentStep(7);

      return;

    }


    if (currentStep === 9) {

      setCurrentStep(8);

      return;

    }

  };


  // ==========================================================
  // APPLICATION CONFIGURATION PAYLOAD
  // ==========================================================

  const buildApplicationConfigurationPayload =
    () => {

      const configurationValues = [];


      for (
        let id = 1;
        id <= 87;
        id += 1
      ) {

        const value =
          applicationConfigurations[id];


        if (
          value &&
          typeof value === "object" &&
          !Array.isArray(value)
        ) {

          configurationValues.push({

            Value:
              value.Value ?? "",

            businessDays:
              value.businessDays ?? "",

            region:
              value.region ?? "",

            startTime:
              value.startTime ?? "",

            endTime:
              value.endTime ?? "",

          });

          continue;

        }


        configurationValues.push({

          Value:
            value === undefined ||
            value === null
              ? ""
              : String(value),

        });

      }


      return configurationValues;

    };


  // ==========================================================
  // EMAIL PAYLOAD
  // ==========================================================

  const buildEmailConfigurationPayload =
    () => {

      if (
        !Array.isArray(
          emailConfigurations
        )
      ) {

        return [];

      }


      return emailConfigurations.map(
        (item) => ({

          Value:
            item &&
            typeof item === "object" &&
            !Array.isArray(item)

              ? String(
                  item.Value ??
                  item.value ??
                  ""
                )

              : item === undefined ||
                item === null

              ? ""

              : String(item),

        })
      );

    };


  // ==========================================================
  // NOTIFICATION PAYLOAD
  // ==========================================================

  const buildNotificationConfigurationPayload =
    () => {

      if (
        !Array.isArray(
          notificationConfigurations
        )
      ) {

        return [];

      }


      return notificationConfigurations.map(
        (item) => ({

          NotificationChannels:
            item &&
            typeof item === "object" &&
            !Array.isArray(item)

              ? String(
                  item.NotificationChannels ??
                  ""
                )

              : "",


          RecipientEmail:
            item &&
            typeof item === "object" &&
            !Array.isArray(item)

              ? String(
                  item.RecipientEmail ??
                  ""
                )

              : item === undefined ||
                item === null

              ? ""

              : String(item),


          TeamsGroup:
            item &&
            typeof item === "object" &&
            !Array.isArray(item)

              ? String(
                  item.TeamsGroup ??
                  ""
                )

              : "",

        })
      );

    };


  // ==========================================================
  // TEAMS PAYLOAD
  // ==========================================================

  const buildTeamsConfigurationPayload =
    () => {

      if (
        !Array.isArray(
          teamsConfigurations
        )
      ) {

        return [];

      }


      return teamsConfigurations.map(
        (item) => ({

          Value:
            item &&
            typeof item === "object" &&
            !Array.isArray(item)

              ? String(
                  item.Value ??
                  item.value ??
                  ""
                )

              : item === undefined ||
                item === null

              ? ""

              : String(item),

        })
      );

    };


  // ==========================================================
  // CONFIGURATION DEPLOYMENT PAYLOAD
  // ==========================================================

  const buildConfigurationDeploymentPayload =
    () => {

      return {

        resource_group_name:
          String(
            deployedResourceInfo
              .resource_group_name ||
              ""
          ).trim(),


        storage_account_name:
          String(
            deployedResourceInfo
              .storage_account_name ||
              ""
          ).trim(),


        app_configuration:
          buildApplicationConfigurationPayload(),


        email_configuration:
          buildEmailConfigurationPayload(),


        notification_configuration:
          buildNotificationConfigurationPayload(),


        teams_configuration:
          buildTeamsConfigurationPayload(),

      };

    };


  // ==========================================================
  // FIRST API
  // ==========================================================

  const handleDeploy = async () => {

    if (isDeploying) {

      return;

    }


    setIsDeploying(true);

    setDeploymentError("");

    setDeploymentResult(null);


    try {

      const deploymentPayload = {

        resource_group_name:
          formData.resourceGroupName.trim(),

        storage_account_name:
          formData.storageAccountName.trim(),

        subscription_id:
          formData.subscriptionId.trim(),

        resource_group_location:
          formData.resourceGroupLocation.trim(),

        storage_account_location:
          formData.storageAccountLocation.trim(),

        function_app_name:
          formData.functionAppName.trim(),

      };


      const response =
        await fetch(
          "http://localhost:8000/api/workflow/deploy",
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


      let data;


      try {

        data =
          await response.json();

      } catch {

        data = {};

      }


      if (!response.ok) {

        throw new Error(
          data.detail ||
          data.message ||
          "Infrastructure deployment failed."
        );

      }


      setDeploymentResult(data);


      const resourceGroupName =
        data.resource_group_name ||
        data.resourceGroupName ||
        data.resources?.resource_group_name ||
        deploymentPayload.resource_group_name;


      const storageAccountName =
        data.storage_account_name ||
        data.storageAccountName ||
        data.resources?.storage_account_name ||
        deploymentPayload.storage_account_name;


      const subscriptionId =
        data.subscription_id ||
        data.subscriptionId ||
        data.resources?.subscription_id ||
        deploymentPayload.subscription_id;


      const location =
        data.location ||
        data.resource_group_location ||
        data.resourceGroupLocation ||
        data.resources?.location ||
        deploymentPayload.resource_group_location;


      const functionAppName =
        data.function_app_name ||
        data.functionAppName ||
        data.resources?.function_app_name ||
        deploymentPayload.function_app_name;


      setDeployedResourceInfo({

        subscription_id:
          subscriptionId,

        resource_group_name:
          resourceGroupName,

        location:
          location,

        storage_account_name:
          storageAccountName,

        function_app_name:
          functionAppName,

      });


      setCompletedSteps(
        (previous) => {

          const updated = [
            ...previous,
          ];


          if (
            !updated.includes(2)
          ) {

            updated.push(2);

          }


          if (
            !updated.includes(3)
          ) {

            updated.push(3);

          }


          return updated;

        }
      );


      setCurrentStep(3);

    } catch (error) {

      console.error(
        "Infrastructure deployment error:",
        error
      );


      setDeploymentError(
        error.message ||
        "Unable to connect to the backend."
      );

    } finally {

      setIsDeploying(false);

    }

  };


  // ==========================================================
  // STEP 3 -> STEP 4
  // ==========================================================

  const handleDeploymentNext = () => {

    if (
      !completedSteps.includes(3)
    ) {

      return;

    }


    setCurrentStep(4);

  };


  // ==========================================================
  // CONFIGURATION DEPLOYMENT
  // ==========================================================

  const handleApplicationConfigurationDeploy =
    async () => {

      if (
        isConfigurationDeploying
      ) {

        return;

      }


      setIsConfigurationDeploying(
        true
      );

      setConfigurationDeploymentError(
        ""
      );

      setConfigurationDeploymentResult(
        null
      );


      try {

        if (
          !deployedResourceInfo
            .resource_group_name
        ) {

          throw new Error(
            "Resource group information was not returned by the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .storage_account_name
        ) {

          throw new Error(
            "Storage account information was not returned by the infrastructure deployment."
          );

        }


        const configurationPayload =
          buildConfigurationDeploymentPayload();


        const response =
          await fetch(
            "http://localhost:8000/configuration/deploy",
            {

              method: "POST",

              headers: {
                "Content-Type":
                  "application/json",
              },

              body:
                JSON.stringify(
                  configurationPayload
                ),

            }
          );


        let data;


        try {

          data =
            await response.json();

        } catch {

          data = {};

        }


        if (!response.ok) {

          throw new Error(
            data.detail ||
            data.message ||
            "Configuration deployment failed."
          );

        }


        setConfigurationDeploymentResult(
          data
        );


        setCompletedSteps(
          (previous) => {

            if (
              previous.includes(4)
            ) {

              return previous;

            }


            return [
              ...previous,
              4,
            ];

          }
        );


        setCurrentStep(5);

      } catch (error) {

        console.error(
          "Configuration deployment error:",
          error
        );


        setConfigurationDeploymentError(
          error.message ||
          "Unable to connect to the configuration backend."
        );


        alert(
          error.message ||
          "Configuration deployment failed."
        );

      } finally {

        setIsConfigurationDeploying(
          false
        );

      }

    };


  // ==========================================================
  // STEP 4 -> STEP 5
  // ==========================================================

  const handleApplicationConfigurationNext =
    () => {

      console.log(
        "Application Configuration Next clicked."
      );


      setCurrentStep(5);

    };


  // ==========================================================
  // STEP 5 -> STEP 6
  // ==========================================================

  const handleConnectionNext =
    () => {

      console.log(
        "Connection Check Next clicked."
      );


      setCurrentStep(6);

    };


  // ==========================================================
  // CONNECTION CHECK COMPLETE
  // ==========================================================

  const handleConnectionComplete =
    (result) => {

      setConnectionCheckResult(
        result
      );

      setConnectionCheckError("");


      setCompletedSteps(
        (previous) => {

          if (
            previous.includes(5)
          ) {

            return previous;

          }


          return [
            ...previous,
            5,
          ];

        }
      );


      console.log(
        "CONNECTION CHECK COMPLETED:",
        result
      );

    };


  // ==========================================================
  // KEY VAULT + QUALYS SETUP
  // ==========================================================

  const handleKeyVaultDeploy =
    async () => {

      if (
        isKeyVaultDeploying
      ) {

        return;

      }


      setIsKeyVaultDeploying(
        true
      );

      setKeyVaultError("");

      setKeyVaultResult(null);


      try {

        if (
          !deployedResourceInfo
            .subscription_id
        ) {

          throw new Error(
            "Subscription information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .resource_group_name
        ) {

          throw new Error(
            "Resource group information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .location
        ) {

          throw new Error(
            "Location information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .function_app_name
        ) {

          throw new Error(
            "Function App information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .storage_account_name
        ) {

          throw new Error(
            "Storage Account information is not available from the infrastructure deployment."
          );

        }


        const requiredFields = [

          "key_vault_name",

          "qualys_username",

          "qualys_password",

          "qualys_base_url",

        ];


        const missingFields =
          requiredFields.filter(
            (field) =>
              !String(
                keyVaultFormData[field] ||
                ""
              ).trim()
          );


        if (
          missingFields.length > 0
        ) {

          throw new Error(
            "Please fill in all Key Vault and Qualys fields."
          );

        }


        const keyVaultPayload = {

          subscription_id:
            deployedResourceInfo
              .subscription_id,

          resource_group_name:
            deployedResourceInfo
              .resource_group_name,

          location:
            deployedResourceInfo
              .location,

          function_app_name:
            deployedResourceInfo
              .function_app_name,

          storage_account_name:
            deployedResourceInfo
              .storage_account_name,

          key_vault_name:
            keyVaultFormData
              .key_vault_name
              .trim(),

          qualys_username:
            keyVaultFormData
              .qualys_username
              .trim(),

          qualys_password:
            keyVaultFormData
              .qualys_password,

          qualys_base_url:
            keyVaultFormData
              .qualys_base_url
              .trim(),

        };


        console.log(
          "KEY VAULT + QUALYS SETUP PAYLOAD:",
          {
            ...keyVaultPayload,
            qualys_password: "********",
          }
        );


        const result =
          await setupKeyVault(
            keyVaultPayload
          );


        console.log(
          "KEY VAULT SETUP RESPONSE:",
          result
        );


        setKeyVaultResult(
          result
        );


        setCompletedSteps(
          (previous) => {

            if (
              previous.includes(6)
            ) {

              return previous;

            }


            return [
              ...previous,
              6,
            ];

          }
        );

      } catch (error) {

        console.error(
          "Key Vault setup error:",
          error
        );


        setKeyVaultError(
          error.message ||
          "Unable to setup Key Vault."
        );


        alert(
          error.message ||
          "Key Vault setup failed."
        );

      } finally {

        setIsKeyVaultDeploying(
          false
        );

      }

    };


  // ==========================================================
  // STEP 6 -> STEP 7
  // ==========================================================

  const handleKeyVaultNext =
    () => {

      console.log(
        "Key Vault deployment is optional."
      );


      setCurrentStep(7);

    };


  // ==========================================================
  // FUNCTION APP DEPLOYMENT - STEP 7
  // ==========================================================

  const handleFunctionDeployment =
    async () => {

      if (
        isFunctionDeploying
      ) {

        return;

      }


      setIsFunctionDeploying(
        true
      );

      setFunctionDeploymentError("");

      setFunctionDeploymentResult(null);


      try {

        // ------------------------------------------------------
        // VALUES COME FROM FIRST INFRASTRUCTURE API
        // ------------------------------------------------------

        if (
          !deployedResourceInfo
            .subscription_id
        ) {

          throw new Error(
            "Subscription information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .resource_group_name
        ) {

          throw new Error(
            "Resource group information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .location
        ) {

          throw new Error(
            "Location information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .storage_account_name
        ) {

          throw new Error(
            "Storage account information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .function_app_name
        ) {

          throw new Error(
            "Function App information is not available from the infrastructure deployment."
          );

        }


        // ------------------------------------------------------
        // FUNCTION APP DEPLOYMENT PAYLOAD
        // ------------------------------------------------------

        const functionDeploymentPayload = {

          subscription_id:
            deployedResourceInfo
              .subscription_id,

          resource_group_name:
            deployedResourceInfo
              .resource_group_name,

          location:
            deployedResourceInfo
              .location,

          storage_account_name:
            deployedResourceInfo
              .storage_account_name,

          function_app_name:
            deployedResourceInfo
              .function_app_name,

          table_name:
            "AppConfiguration",

          cache_expiration_minutes:
            10,

        };


        console.log(
          "FUNCTION APP DEPLOYMENT PAYLOAD:",
          functionDeploymentPayload
        );


        // ------------------------------------------------------
        // FUNCTION APP DEPLOYMENT API
        // ------------------------------------------------------

        const response =
          await fetch(
            "http://localhost:8000/api/deployment/function-app",
            {

              method: "POST",

              headers: {

                "Content-Type":
                  "application/json",

              },

              body:
                JSON.stringify(
                  functionDeploymentPayload
                ),

            }
          );


        let data;


        try {

          data =
            await response.json();

        } catch {

          data = {};

        }


        if (!response.ok) {

          throw new Error(
            data.detail ||
            data.message ||
            "Function App deployment failed."
          );

        }


        console.log(
          "FUNCTION APP DEPLOYMENT RESPONSE:",
          data
        );


        setFunctionDeploymentResult(
          data
        );


        // ------------------------------------------------------
        // MARK STEP 7 COMPLETE
        // ------------------------------------------------------

        setCompletedSteps(
          (previous) => {

            if (
              previous.includes(7)
            ) {

              return previous;

            }


            return [
              ...previous,
              7,
            ];

          }
        );


      } catch (error) {

        console.error(
          "Function App deployment error:",
          error
        );


        setFunctionDeploymentError(
          error.message ||
          "Unable to deploy Function App."
        );


        alert(
          error.message ||
          "Function App deployment failed."
        );

      } finally {

        setIsFunctionDeploying(
          false
        );

      }

    };


  // ==========================================================
  // STEP 7 -> STEP 8
  // ==========================================================

  // ==========================================================
// STEP 7 -> STEP 8
// ==========================================================

const handleFunctionDeploymentNext =
  () => {

    // Next should work whether Function App
    // has been deployed or not.
    //
    // The only thing that should prevent Next
    // is an active deployment.

    if (isFunctionDeploying) {

      return;

    }

    console.log(
      "Moving to Notification ARM Deployment."
    );

    setCurrentStep(8);

  };

  // ==========================================================
  // NOTIFICATION ARM DEPLOYMENT
  // ==========================================================

  const handleNotificationARMDeploy =
    async () => {

      if (
        isNotificationARMDeploying
      ) {

        return;

      }


      setIsNotificationARMDeploying(
        true
      );

      setNotificationARMError("");

      setNotificationARMResult(null);


      try {

        if (
          !deployedResourceInfo
            .subscription_id
        ) {

          throw new Error(
            "Subscription information is not available."
          );

        }


        if (
          !deployedResourceInfo
            .resource_group_name
        ) {

          throw new Error(
            "Resource group information is not available."
          );

        }


        if (
          !deployedResourceInfo
            .location
        ) {

          throw new Error(
            "Location information is not available."
          );

        }


        if (
          !deployedResourceInfo
            .storage_account_name
        ) {

          throw new Error(
            "Storage account information is not available."
          );

        }


        const notificationPayload = {

          subscription_id:
            deployedResourceInfo
              .subscription_id,

          resource_group_name:
            deployedResourceInfo
              .resource_group_name,

          location:
            deployedResourceInfo
              .location,

          storage_account_name:
            deployedResourceInfo
              .storage_account_name,

          logic_app_name:
            notificationARMConfiguration
              .logic_app_name,

          completion_logic_app_name:
            notificationARMConfiguration
              .completion_logic_app_name,

          notification_followup_logic_app_name:
            notificationARMConfiguration
              .notification_followup_logic_app_name,

          followup_queue_name:
            notificationARMConfiguration
              .followup_queue_name,

          notification_log_table_name:
            notificationARMConfiguration
              .notification_log_table_name,

          notification_status_table_name:
            notificationARMConfiguration
              .notification_status_table_name,

          azure_tables_connection_name:
            notificationARMConfiguration
              .azure_tables_connection_name,

          azure_queues_connection_name:
            notificationARMConfiguration
              .azure_queues_connection_name,

          office365_connection_name:
            notificationARMConfiguration
              .office365_connection_name,

          teams_connection_name:
            notificationARMConfiguration
              .teams_connection_name,

        };


        console.log(
          "NOTIFICATION ARM DEPLOYMENT PAYLOAD:",
          notificationPayload
        );


        const result =
          await deployNotificationARM(
            notificationPayload
          );


        console.log(
          "NOTIFICATION ARM DEPLOYMENT RESPONSE:",
          result
        );


        setNotificationARMResult(
          result
        );


        setCompletedSteps(
          (previous) => {

            if (
              previous.includes(8)
            ) {

              return previous;

            }


            return [
              ...previous,
              8,
            ];

          }
        );

      } catch (error) {

        console.error(
          "Notification ARM deployment error:",
          error
        );


        setNotificationARMError(
          error.message ||
          "Unable to deploy Notification ARM resources."
        );


        alert(
          error.message ||
          "Notification ARM deployment failed."
        );

      } finally {

        setIsNotificationARMDeploying(
          false
        );

      }

    };


  // ==========================================================
  // STEP 8 -> STEP 9
  // ==========================================================

  const handleNotificationARMNext =
    () => {

      console.log(
        "Moving to Scoping Configuration."
      );


      setCurrentStep(9);

    };


  // ==========================================================
  // SCOPING DEPLOYMENT
  // ==========================================================

  const handleScopingDeploy =
    async () => {

      if (
        isScopingDeploying
      ) {

        return;

      }


      setIsScopingDeploying(
        true
      );

      setScopingError("");

      setScopingResult(null);


      try {

        if (
          !deployedResourceInfo
            .subscription_id
        ) {

          throw new Error(
            "Subscription information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .resource_group_name
        ) {

          throw new Error(
            "Resource group information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .location
        ) {

          throw new Error(
            "Location information is not available from the infrastructure deployment."
          );

        }


        if (
          !deployedResourceInfo
            .storage_account_name
        ) {

          throw new Error(
            "Storage account information is not available from the infrastructure deployment."
          );

        }


        const requiredFields = [

          "sharepoint_url",

          "callback_secret_key",

          "completion_logic_app_url",

        ];


        const missingFields =
          requiredFields.filter(
            (field) =>
              !String(
                scopingFormData[field] ||
                ""
              ).trim()
          );


        if (
          missingFields.length > 0
        ) {

          throw new Error(
            "Please fill in SharePoint URL, Callback Secret Key, and Completion Logic App URL."
          );

        }


        const scopingPayload = {

          subscription_id:
            deployedResourceInfo
              .subscription_id,

          resource_group_name:
            deployedResourceInfo
              .resource_group_name,

          location:
            deployedResourceInfo
              .location,

          storage_account_name:
            deployedResourceInfo
              .storage_account_name,

          sharepoint_url:
            scopingFormData
              .sharepoint_url
              .trim(),

          callback_secret_key:
            scopingFormData
              .callback_secret_key,

          completion_logic_app_url:
            scopingFormData
              .completion_logic_app_url
              .trim(),

          logic_app_name:
            scopingConfiguration
              .logic_app_name,

          scoping01_logic_app_name:
            scopingConfiguration
              .scoping01_logic_app_name,

          scoping02_logic_app_name:
            scopingConfiguration
              .scoping02_logic_app_name,

          table_connection_name:
            scopingConfiguration
              .table_connection_name,

          queue_connection_name:
            scopingConfiguration
              .queue_connection_name,

          sharepoint_connection_name:
            scopingConfiguration
              .sharepoint_connection_name,

          notification_log_table_name:
            scopingConfiguration
              .notification_log_table_name,

          notification_status_table_name:
            scopingConfiguration
              .notification_status_table_name,

          queue_name:
            scopingConfiguration
              .queue_name,

          authscan_queue_name:
            scopingConfiguration
              .authscan_queue_name,

        };


        console.log(
          "SCOPING DEPLOYMENT PAYLOAD:",
          {
            ...scopingPayload,

            callback_secret_key:
              "********",
          }
        );


        const response =
          await fetch(
            "http://localhost:8000/api/scoping/deploy",
            {

              method: "POST",

              headers: {

                "Content-Type":
                  "application/json",

              },

              body:
                JSON.stringify(
                  scopingPayload
                ),

            }
          );


        let data;


        try {

          data =
            await response.json();

        } catch {

          data = {};

        }


        if (!response.ok) {

          throw new Error(
            data.detail ||
            data.message ||
            "Scoping deployment failed."
          );

        }


        setScopingResult(
          data
        );


        setCompletedSteps(
          (previous) => {

            if (
              previous.includes(9)
            ) {

              return previous;

            }


            return [
              ...previous,
              9,
            ];

          }
        );


      } catch (error) {

        console.error(
          "Scoping deployment error:",
          error
        );


        setScopingError(
          error.message ||
          "Unable to deploy Scoping Logic Apps."
        );


        alert(
          error.message ||
          "Scoping deployment failed."
        );

      } finally {

        setIsScopingDeploying(
          false
        );

      }

    };


  // ==========================================================
  // RENDER
  // ==========================================================

  return (

    <PageLayout>

      <div className="wizard-layout">

        {/* ====================================================
            SIDEBAR
            ==================================================== */}

        <WizardSidebar
          currentStep={currentStep}
          completedSteps={completedSteps}
          onStepClick={(stepId) => {
            setCurrentStep(stepId);
          }}
        />


        {/* ====================================================
            MAIN
            ==================================================== */}

        <main className="wizard-main">


          {/* ==================================================
              STEP 1
              ================================================== */}

          {currentStep === 1 && (

            <InfrastructureForm

              formData={
                formData
              }

              onChange={
                handleChange
              }

            />

          )}


          {/* ==================================================
              STEP 2
              ================================================== */}

          {currentStep === 2 && (

            <ConfigurationForm

              formData={
                formData
              }

              onNext={
                handleConfigurationNext
              }

            />

          )}


          {/* ==================================================
              STEP 3
              ================================================== */}

          {currentStep === 3 && (

            <DeploymentResult

              formData={
                formData
              }

              result={
                deploymentResult
              }

              error={
                deploymentError
              }

            />

          )}


          {/* ==================================================
              STEP 4
              ================================================== */}

          {currentStep === 4 && (

            <ApplicationConfiguration

              formData={
                formData
              }

              configurations={
                applicationConfigurations
              }

              onConfigurationChange={
                handleApplicationConfigurationChange
              }

              onEmailConfigurationChange={
                handleEmailConfigurationChange
              }

              onNotificationConfigurationChange={
                handleNotificationConfigurationChange
              }

              onTeamsConfigurationChange={
                handleTeamsConfigurationChange
              }

              emailConfigurations={
                emailConfigurations
              }

              notificationConfigurations={
                notificationConfigurations
              }

              teamsConfigurations={
                teamsConfigurations
              }

              onNext={
                handleApplicationConfigurationNext
              }

              onDeploy={
                handleApplicationConfigurationDeploy
              }

              isDeploying={
                isConfigurationDeploying
              }

              deploymentResult={
                configurationDeploymentResult
              }

              deploymentError={
                configurationDeploymentError
              }

            />

          )}


          {/* ==================================================
              STEP 5
              ================================================== */}

          {currentStep === 5 && (

            <ConnectionCheck

              deploymentInfo={
                deployedResourceInfo
              }

              onComplete={
                handleConnectionComplete
              }

            />

          )}


          {/* ==================================================
              STEP 6
              KEY VAULT
              ================================================== */}

          {currentStep === 6 && (

            <KeyVaultConfiguration

              deploymentInfo={
                deployedResourceInfo
              }

              formData={
                keyVaultFormData
              }

              onChange={
                handleKeyVaultChange
              }

              onDeploy={
                handleKeyVaultDeploy
              }

              isDeploying={
                isKeyVaultDeploying
              }

              result={
                keyVaultResult
              }

              error={
                keyVaultError
              }

            />

          )}


          {/* ==================================================
              STEP 7
              FUNCTION APP DEPLOYMENT
              ================================================== */}

          {currentStep === 7 && (

            <FunctionDeployment

              deploymentInfo={
                deployedResourceInfo
              }

              onDeploy={
                handleFunctionDeployment
              }

              isDeploying={
                isFunctionDeploying
              }

              result={
                functionDeploymentResult
              }

              error={
                functionDeploymentError
              }

            />

          )}


          {/* ==================================================
              STEP 8
              NOTIFICATION ARM
              ================================================== */}

          {currentStep === 8 && (

            <NotificationARMConfiguration

              deploymentInfo={
                deployedResourceInfo
              }

              configuration={
                notificationARMConfiguration
              }

              onDeploy={
                handleNotificationARMDeploy
              }

              isDeploying={
                isNotificationARMDeploying
              }

              result={
                notificationARMResult
              }

              error={
                notificationARMError
              }

            />

          )}


          {/* ==================================================
              STEP 9
              SCOPING CONFIGURATION
              ================================================== */}

          {currentStep === 9 && (

            <ScopingConfiguration

              deploymentInfo={
                deployedResourceInfo
              }

              configuration={
                scopingConfiguration
              }

              formData={
                scopingFormData
              }

              onChange={
                handleScopingChange
              }

              onDeploy={
                handleScopingDeploy
              }

              isDeploying={
                isScopingDeploying
              }

              result={
                scopingResult
              }

              error={
                scopingError
              }

            />

          )}


          {/* ==================================================
              FOOTER
              ================================================== */}

          <WizardFooter

            currentStep={
              currentStep
            }

            onBack={
              handleBack
            }

            onNext={
              handleNext
            }

            onDeploy={
              currentStep === 7
                ? handleFunctionDeployment
                : handleDeploy
            }

            onDeploymentNext={
              handleDeploymentNext
            }

            onApplicationConfigurationNext={
              handleApplicationConfigurationNext
            }

            onConnectionNext={
              handleConnectionNext
            }

            onKeyVaultNext={
              handleKeyVaultNext
            }

            onFunctionDeploymentNext={
              handleFunctionDeploymentNext
            }

            onNotificationARMDeploy={
              handleNotificationARMDeploy
            }

            onNotificationARMNext={
              handleNotificationARMNext
            }

            onScopingDeploy={
              handleScopingDeploy
            }

            isDeploying={

              isDeploying ||

              isConfigurationDeploying ||

              isCheckingConnections ||

              isKeyVaultDeploying ||

              isFunctionDeploying ||

              isNotificationARMDeploying ||

              isScopingDeploying

            }

            completedSteps={
              completedSteps
            }

          />

        </main>

      </div>

    </PageLayout>

  );

}


export default NewDeployment;