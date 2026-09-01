import { useEffect, useMemo, useState } from "react";
import "./ApplicationConfiguration.css";

import appConfigurationCsv from "../../tables/AppConfiguration.csv?raw";
import emailRecipientConfigurationCsv from "../../tables/EmailRecipientConfiguration.csv?raw";
import notificationConfigurationCsv from "../../tables/NotificationConfiguration.csv?raw";
import teamsRecipientConfigurationCsv from "../../tables/TeamsRecipientConfiguration.csv?raw";

/* ============================================================
   CSV PARSER
   ============================================================ */

const parseCsv = (csvText) => {
  if (!csvText) {
    return [];
  }

  const text = String(csvText)
    .replace(/^\uFEFF/, "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n");

  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"') {
      if (inQuotes && next === '"') {
        field += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }

      continue;
    }

    if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
      continue;
    }

    if (char === "\n" && !inQuotes) {
      row.push(field);
      field = "";

      if (
        row.some(
          (value) =>
            String(value).trim() !== ""
        )
      ) {
        rows.push(row);
      }

      row = [];
      continue;
    }

    field += char;
  }

  if (field !== "" || row.length > 0) {
    row.push(field);

    if (
      row.some(
        (value) =>
          String(value).trim() !== ""
      )
    ) {
      rows.push(row);
    }
  }

  if (rows.length < 2) {
    return [];
  }

  const headers = rows[0].map((header) =>
    String(header ?? "").trim()
  );

  return rows.slice(1).map((cells) => {
    const result = {};

    headers.forEach((header, index) => {
      if (header) {
        result[header] = String(
          cells[index] ?? ""
        ).trim();
      }
    });

    return result;
  });
};

const csvValue = (row, key) =>
  String(row?.[key] ?? "").trim();

/* ============================================================
   BUILD CONFIGURATION FROM CSV
   ============================================================ */

const buildConfiguration = (
  row,
  id,
  extra = {}
) => {
  const configuration = {
    id,

    partitionKey: csvValue(
      row,
      "PartitionKey"
    ),

    rowKey: csvValue(
      row,
      "RowKey"
    ),

    description: csvValue(
      row,
      "Description"
    ),

    sampleValue:
      csvValue(
        row,
        "SampleValue"
      ) ||
      csvValue(
        row,
        "Value"
      ),

    validation: csvValue(
      row,
      "Validation"
    ),

    ...extra,
  };

  /* ----------------------------------------------------------
     BUSINESS DAY FIELDS
     ---------------------------------------------------------- */

  const businessFields = [
    [
      "businessDays",
      "Business Days",
    ],
    [
      "endTime",
      "End Time",
    ],
    [
      "region",
      "Region",
    ],
    [
      "startTime",
      "Start Time",
    ],
  ]
    .map(([key, label]) => ({
      key,
      label,
      sampleValue: csvValue(
        row,
        key
      ),
    }))
    .filter(
      (field) =>
        field.sampleValue !== ""
    );

  if (
    configuration.partitionKey ===
      "BusinessDay" &&
    configuration.rowKey ===
      "WorkingDayandHour"
  ) {
    configuration.isBusinessHours =
      true;

    configuration.fields =
      businessFields;
  }

  /* ----------------------------------------------------------
     SCHEDULE FIELDS
     ---------------------------------------------------------- */

  const scheduleFields = [
    [
      "targetDay",
      "Target Day",
    ],
    [
      "targetHour",
      "Target Hour",
    ],
    [
      "targetMinute",
      "Target Minute",
    ],
    [
      "targetTimezone",
      "Target Time Zone",
    ],
  ]
    .map(([key, label]) => ({
      key,
      label,
      sampleValue: csvValue(
        row,
        key
      ),
    }))
    .filter(
      (field) =>
        field.sampleValue !== ""
    );

  if (
    scheduleFields.length > 0
  ) {
    configuration.scheduleFields =
      scheduleFields;
  }

  return configuration;
};

/* ============================================================
   COMPONENT
   ============================================================ */

function ApplicationConfiguration({
  configurations = [],
  onConfigurationChange,
  onEmailConfigurationChange,
  onNotificationConfigurationChange,
  onTeamsConfigurationChange,
  emailConfigurations = [],
  notificationConfigurations = [],
  teamsConfigurations = [],
  onDeploy,
  isDeploying = false,
}) {
  /* ==========================================================
     PAGINATION CONSTANTS
     ========================================================== */

  const ITEMS_PER_PAGE = 10;

  const SECOND_TABLE_ITEMS_PER_PAGE =
    10;

  const THIRD_TABLE_ITEMS_PER_PAGE =
    10;

  const FOURTH_TABLE_ITEMS_PER_PAGE =
    10;

  /* ==========================================================
     LOCAL STATE
     ========================================================== */

  const [values, setValues] =
    useState({});

  const [currentPage, setCurrentPage] =
    useState(1);

  const [
    secondTablePage,
    setSecondTablePage,
  ] = useState(1);

  const [
    thirdTablePage,
    setThirdTablePage,
  ] = useState(1);

  const [
    fourthTablePage,
    setFourthTablePage,
  ] = useState(1);

  /* ==========================================================
     CSV DATA
     ========================================================== */

  const appConfigurationRows =
    useMemo(
      () =>
        parseCsv(
          appConfigurationCsv
        ),
      []
    );

  const emailConfigurationRows =
    useMemo(
      () =>
        parseCsv(
          emailRecipientConfigurationCsv
        ),
      []
    );

  const notificationConfigurationRows =
    useMemo(
      () =>
        parseCsv(
          notificationConfigurationCsv
        ),
      []
    );

  const teamsConfigurationRows =
    useMemo(
      () =>
        parseCsv(
          teamsRecipientConfigurationCsv
        ),
      []
    );

  /* ==========================================================
     CONFIGURATION DEFINITIONS
     
     IMPORTANT:
     These are no longer hardcoded.
     They are generated from the CSV rows.
     ========================================================== */

  const defaultConfigurations =
    useMemo(
      () =>
        appConfigurationRows.map(
          (row, index) =>
            buildConfiguration(
              row,
              index + 1
            )
        ),
      [appConfigurationRows]
    );

  const notificationConfigurationDefinitions =
    useMemo(
      () =>
        emailConfigurationRows.map(
          (row, index) =>
            buildConfiguration(
              row,
              88 + index,
              {
                displayNumber:
                  index + 1,
              }
            )
        ),
      [emailConfigurationRows]
    );

  const channelConfigurations =
    useMemo(
      () =>
        notificationConfigurationRows.map(
          (row, index) =>
            buildConfiguration(
              row,
              93 + index
            )
        ),
      [
        notificationConfigurationRows,
      ]
    );

  const teamsConfigurationDefinitions =
    useMemo(
      () =>
        teamsConfigurationRows.map(
          (row, index) =>
            buildConfiguration(
              row,
              128 + index
            )
        ),
      [teamsConfigurationRows]
    );

  /* ==========================================================
     ALL CONFIGURATIONS
     ========================================================== */

  const allConfigurations =
    useMemo(
      () => [
        ...defaultConfigurations,
        ...notificationConfigurationDefinitions,
        ...channelConfigurations,
        ...teamsConfigurationDefinitions,
      ],
      [
        defaultConfigurations,
        notificationConfigurationDefinitions,
        channelConfigurations,
        teamsConfigurationDefinitions,
      ]
    );

  /* ==========================================================
     LOAD BACKEND VALUES
     ========================================================== */

  useEffect(() => {
    if (
      !Array.isArray(
        configurations
      )
    ) {
      return;
    }

    const loadedValues = {};

    configurations.forEach(
      (item, index) => {
        if (!item) {
          return;
        }

        const configurationId =
          item.id ||
          item.configurationId ||
          allConfigurations[index]?.id;

        if (!configurationId) {
          return;
        }

        /* ----------------------------------------------------
           Notification channel configuration
           ---------------------------------------------------- */

        if (
          item.NotificationChannels !==
            undefined ||
          item.RecipientEmail !==
            undefined ||
          item.TeamsGroup !== undefined
        ) {
          loadedValues[
            configurationId
          ] = {
            NotificationChannels:
              item.NotificationChannels ??
              "Email,TeamsCard",

            RecipientEmail:
              item.RecipientEmail ??
              "",

            TeamsGroup:
              item.TeamsGroup ??
              "",
          };

          return;
        }

        /* ----------------------------------------------------
           Normal Azure Table configuration
           ---------------------------------------------------- */

        if (
          item.Value !== undefined &&
          item.Value !== null
        ) {
          loadedValues[
            configurationId
          ] = {
            value: String(
              item.Value
            ),
          };

          return;
        }

        if (
          item.value !== undefined &&
          item.value !== null
        ) {
          loadedValues[
            configurationId
          ] = {
            value: String(
              item.value
            ),
          };

          return;
        }

        const directFields = {};

        [
          "businessDays",
          "endTime",
          "region",
          "startTime",
          "targetDay",
          "targetHour",
          "targetMinute",
          "targetTimezone",
        ].forEach((field) => {
          if (
            item[field] !==
              undefined &&
            item[field] !== null
          ) {
            directFields[field] =
              String(
                item[field]
              );
          }
        });

        if (
          Object.keys(
            directFields
          ).length > 0
        ) {
          loadedValues[
            configurationId
          ] = directFields;
        }
      }
    );

    if (
      Object.keys(
        loadedValues
      ).length > 0
    ) {
      setValues(
        (previous) => ({
          ...previous,
          ...loadedValues,
        })
      );
    }
  }, [
    configurations,
    allConfigurations,
  ]);

  /* ==========================================================
     LOAD EMAIL CONFIGURATIONS
     ========================================================== */

  useEffect(() => {
    if (
      !Array.isArray(
        emailConfigurations
      )
    ) {
      return;
    }

    if (
      emailConfigurations.length ===
      0
    ) {
      return;
    }

    const loadedEmailValues = {};

    emailConfigurations.forEach(
      (item) => {
        if (!item) {
          return;
        }

        const matchedDefinition =
          notificationConfigurationDefinitions.find(
            (definition) =>
              definition.id ===
                item.id ||
              (definition.partitionKey ===
                item.partitionKey &&
                definition.rowKey ===
                  item.rowKey)
          );

        if (!matchedDefinition) {
          return;
        }

        const value =
          item.Value ??
          item.value ??
          item.Email ??
          item.email ??
          "";

        loadedEmailValues[
          matchedDefinition.id
        ] = {
          value: String(
            value
          ),
        };
      }
    );

    if (
      Object.keys(
        loadedEmailValues
      ).length > 0
    ) {
      setValues(
        (previous) => ({
          ...previous,
          ...loadedEmailValues,
        })
      );
    }
  }, [
    emailConfigurations,
    notificationConfigurationDefinitions,
  ]);

  /* ==========================================================
     LOAD NOTIFICATION CHANNEL CONFIGURATIONS
     ========================================================== */

  useEffect(() => {
    if (
      !Array.isArray(
        notificationConfigurations
      )
    ) {
      return;
    }

    if (
      notificationConfigurations.length ===
      0
    ) {
      return;
    }

    const loadedChannelValues =
      {};

    notificationConfigurations.forEach(
      (item) => {
        if (!item) {
          return;
        }

        const matchedDefinition =
          channelConfigurations.find(
            (definition) =>
              definition.id ===
                item.id ||
              (definition.partitionKey ===
                item.partitionKey &&
                definition.rowKey ===
                  item.rowKey)
          );

        if (!matchedDefinition) {
          return;
        }

        loadedChannelValues[
          matchedDefinition.id
        ] = {
          NotificationChannels:
            item.NotificationChannels ??
            "Email,TeamsCard",

          RecipientEmail:
            item.RecipientEmail ??
            "",

          TeamsGroup:
            item.TeamsGroup ??
            "",
        };
      }
    );

    if (
      Object.keys(
        loadedChannelValues
      ).length > 0
    ) {
      setValues(
        (previous) => ({
          ...previous,
          ...loadedChannelValues,
        })
      );
    }
  }, [
    notificationConfigurations,
    channelConfigurations,
  ]);

  /* ==========================================================
     LOAD TEAMS CONFIGURATIONS
     ========================================================== */

  useEffect(() => {
    if (
      !Array.isArray(
        teamsConfigurations
      )
    ) {
      return;
    }

    if (
      teamsConfigurations.length ===
      0
    ) {
      return;
    }

    const loadedTeamsValues = {};

    teamsConfigurations.forEach(
      (item) => {
        if (!item) {
          return;
        }

        const matchedDefinition =
          teamsConfigurationDefinitions.find(
            (definition) =>
              definition.id ===
                item.id ||
              (definition.partitionKey ===
                item.partitionKey &&
                definition.rowKey ===
                  item.rowKey)
          );

        if (!matchedDefinition) {
          return;
        }

        const value =
          item.Value ??
          item.value ??
          "";

        loadedTeamsValues[
          matchedDefinition.id
        ] = {
          value: String(
            value
          ),
        };
      }
    );

    if (
      Object.keys(
        loadedTeamsValues
      ).length > 0
    ) {
      setValues(
        (previous) => ({
          ...previous,
          ...loadedTeamsValues,
        })
      );
    }
  }, [
    teamsConfigurations,
    teamsConfigurationDefinitions,
  ]);

  /* ==========================================================
     FIRST TABLE PAGINATION
     ========================================================== */

  const totalItems =
    defaultConfigurations.length;

  const totalPages = Math.max(
    1,
    Math.ceil(
      totalItems /
        ITEMS_PER_PAGE
    )
  );

  const safeCurrentPage =
    Math.min(
      currentPage,
      totalPages
    );

  const startIndex =
    (safeCurrentPage - 1) *
    ITEMS_PER_PAGE;

  const endIndex =
    startIndex +
    ITEMS_PER_PAGE;

  const currentConfigurations =
    useMemo(
      () =>
        defaultConfigurations.slice(
          startIndex,
          endIndex
        ),
      [
        defaultConfigurations,
        startIndex,
        endIndex,
      ]
    );

  /* ==========================================================
     SECOND TABLE PAGINATION
     ========================================================== */

  const secondTableTotalItems =
    notificationConfigurationDefinitions.length;

  const secondTableTotalPages =
    Math.max(
      1,
      Math.ceil(
        secondTableTotalItems /
          SECOND_TABLE_ITEMS_PER_PAGE
      )
    );

  const safeSecondTablePage =
    Math.min(
      secondTablePage,
      secondTableTotalPages
    );

  const secondTableStartIndex =
    (safeSecondTablePage - 1) *
    SECOND_TABLE_ITEMS_PER_PAGE;

  const secondTableEndIndex =
    secondTableStartIndex +
    SECOND_TABLE_ITEMS_PER_PAGE;

  const currentNotificationConfigurations =
    useMemo(
      () =>
        notificationConfigurationDefinitions.slice(
          secondTableStartIndex,
          secondTableEndIndex
        ),
      [
        notificationConfigurationDefinitions,
        secondTableStartIndex,
        secondTableEndIndex,
      ]
    );

  /* ==========================================================
     THIRD TABLE PAGINATION
     ========================================================== */

  const thirdTableTotalItems =
    channelConfigurations.length;

  const thirdTableTotalPages =
    Math.max(
      1,
      Math.ceil(
        thirdTableTotalItems /
          THIRD_TABLE_ITEMS_PER_PAGE
      )
    );

  const safeThirdTablePage =
    Math.min(
      thirdTablePage,
      thirdTableTotalPages
    );

  const thirdTableStartIndex =
    (safeThirdTablePage - 1) *
    THIRD_TABLE_ITEMS_PER_PAGE;

  const thirdTableEndIndex =
    thirdTableStartIndex +
    THIRD_TABLE_ITEMS_PER_PAGE;

  const currentChannelConfigurations =
    useMemo(
      () =>
        channelConfigurations.slice(
          thirdTableStartIndex,
          thirdTableEndIndex
        ),
      [
        channelConfigurations,
        thirdTableStartIndex,
        thirdTableEndIndex,
      ]
    );

  /* ==========================================================
     FOURTH TABLE PAGINATION
     ========================================================== */

  const fourthTableTotalItems =
    teamsConfigurationDefinitions.length;

  const fourthTableTotalPages =
    Math.max(
      1,
      Math.ceil(
        fourthTableTotalItems /
          FOURTH_TABLE_ITEMS_PER_PAGE
      )
    );

  const safeFourthTablePage =
    Math.min(
      fourthTablePage,
      fourthTableTotalPages
    );

  const fourthTableStartIndex =
    (safeFourthTablePage - 1) *
    FOURTH_TABLE_ITEMS_PER_PAGE;

  const fourthTableEndIndex =
    fourthTableStartIndex +
    FOURTH_TABLE_ITEMS_PER_PAGE;

  const currentTeamsRecipientConfigurations =
    useMemo(
      () =>
        teamsConfigurationDefinitions.slice(
          fourthTableStartIndex,
          fourthTableEndIndex
        ),
      [
        teamsConfigurationDefinitions,
        fourthTableStartIndex,
        fourthTableEndIndex,
      ]
    );

  /* ==========================================================
     SEND CHANGE TO PARENT
     ========================================================== */

  const notifyParent = (
    section,
    configuration,
    data
  ) => {
    const base = {
      id: configuration.id,

      partitionKey:
        configuration.partitionKey,

      rowKey:
        configuration.rowKey,
    };

    /* --------------------------------------------------------
       EMAIL CONFIGURATION
       -------------------------------------------------------- */

    if (
      section ===
      "email_configuration"
    ) {
      onEmailConfigurationChange?.(
        (previous) => {
          const current =
            Array.isArray(previous)
              ? previous
              : [];

          const item = {
            ...base,

            Value: String(
              data.Value ?? ""
            ),
          };

          const index =
            current.findIndex(
              (entry) =>
                entry?.id ===
                configuration.id
            );

          if (index === -1) {
            return [
              ...current,
              item,
            ];
          }

          return current.map(
            (entry, i) =>
              i === index
                ? {
                    ...entry,
                    ...item,
                  }
                : entry
          );
        }
      );

      return;
    }

    /* --------------------------------------------------------
       NOTIFICATION CHANNEL CONFIGURATION
       -------------------------------------------------------- */

    if (
      section ===
      "notification_configuration"
    ) {
      onNotificationConfigurationChange?.(
        (previous) => {
          const current =
            Array.isArray(previous)
              ? previous
              : [];

          const item = {
            ...base,

            NotificationChannels:
              String(
                data.NotificationChannels ??
                  ""
              ),

            RecipientEmail:
              String(
                data.RecipientEmail ??
                  ""
              ),

            TeamsGroup:
              String(
                data.TeamsGroup ??
                  ""
              ),
          };

          const index =
            current.findIndex(
              (entry) =>
                entry?.id ===
                configuration.id
            );

          if (index === -1) {
            return [
              ...current,
              item,
            ];
          }

          return current.map(
            (entry, i) =>
              i === index
                ? {
                    ...entry,
                    ...item,
                  }
                : entry
          );
        }
      );

      return;
    }

    /* --------------------------------------------------------
       TEAMS CONFIGURATION
       -------------------------------------------------------- */

    if (
      section ===
      "teams_configuration"
    ) {
      onTeamsConfigurationChange?.(
        (previous) => {
          const current =
            Array.isArray(previous)
              ? previous
              : [];

          const item = {
            ...base,

            Value: String(
              data.Value ?? ""
            ),
          };

          const index =
            current.findIndex(
              (entry) =>
                entry?.id ===
                configuration.id
            );

          if (index === -1) {
            return [
              ...current,
              item,
            ];
          }

          return current.map(
            (entry, i) =>
              i === index
                ? {
                    ...entry,
                    ...item,
                  }
                : entry
          );
        }
      );

      return;
    }

    /* --------------------------------------------------------
       NORMAL APPLICATION CONFIGURATION
       -------------------------------------------------------- */

    onConfigurationChange?.({
      ...base,
      ...data,
    });
  };

  /* ==========================================================
     FIRST TABLE VALUE CHANGE
     ========================================================== */

  const handleValueChange = (
    configuration,
    fieldKey,
    value
  ) => {
    const configurationId =
      configuration.id;

    const updatedConfiguration = {
      ...(values[
        configurationId
      ] || {}),

      ...(fieldKey
        ? {
            [fieldKey]: value,
          }
        : {
            value,
          }),
    };

    setValues(
      (previous) => ({
        ...previous,

        [configurationId]:
          updatedConfiguration,
      })
    );

    /* --------------------------------------------------------
       Normal configuration
       -------------------------------------------------------- */

    if (!fieldKey) {
      notifyParent(
        "app_configuration",
        configuration,
        {
          Value: value,
        }
      );

      return;
    }

    /* --------------------------------------------------------
       Multi-field configuration
       -------------------------------------------------------- */

    if (
      configuration.isBusinessHours ||
      configuration.scheduleFields
    ) {
      const updatedFields = {
        ...(values[
          configurationId
        ] || {}),

        [fieldKey]: value,
      };

      /* ------------------------------------------------------
         BusinessDay
         ------------------------------------------------------ */

      if (
        configuration.isBusinessHours
      ) {
        notifyParent(
          "app_configuration",
          configuration,
          {
            Value:
              updatedFields.businessDays ||
              "",

            businessDays:
              updatedFields.businessDays ||
              "",

            region:
              updatedFields.region ||
              "",

            startTime:
              updatedFields.startTime ||
              "",

            endTime:
              updatedFields.endTime ||
              "",
          }
        );

        return;
      }

      /* ------------------------------------------------------
         Schedule
         ------------------------------------------------------ */

      notifyParent(
        "app_configuration",
        configuration,
        {
          Value:
            JSON.stringify(
              updatedFields
            ),

          ...updatedFields,
        }
      );

      return;
    }

    notifyParent(
      "app_configuration",
      configuration,
      {
        Value: value,
      }
    );
  };

  /* ==========================================================
     EMAIL TABLE VALUE CHANGE
     ========================================================== */

  const handleEmailValueChange = (
    configuration,
    value
  ) => {
    const configurationId =
      configuration.id;

    setValues(
      (previous) => ({
        ...previous,

        [configurationId]: {
          ...(previous[
            configurationId
          ] || {}),

          value,
        },
      })
    );

    notifyParent(
      "email_configuration",
      configuration,
      {
        Value: value,
      }
    );
  };

  /* ==========================================================
     THIRD TABLE CHANGE
     ========================================================== */

  const handleChannelValueChange = (
    configuration,
    fieldKey,
    value
  ) => {
    const configurationId =
      configuration.id;

    const existing =
      values[configurationId] ||
      {};

    const updatedConfiguration = {
      NotificationChannels:
        existing.NotificationChannels ||
        "Email,TeamsCard",

      RecipientEmail:
        existing.RecipientEmail ||
        "",

      TeamsGroup:
        existing.TeamsGroup ||
        "",

      [fieldKey]: value,
    };

    setValues(
      (previous) => ({
        ...previous,

        [configurationId]:
          updatedConfiguration,
      })
    );

    notifyParent(
      "notification_configuration",
      configuration,
      {
        NotificationChannels:
          updatedConfiguration.NotificationChannels,

        RecipientEmail:
          updatedConfiguration.RecipientEmail,

        TeamsGroup:
          updatedConfiguration.TeamsGroup,
      }
    );
  };

  /* ==========================================================
     FOURTH TABLE CHANGE
     ========================================================== */

  const handleTeamsRecipientValueChange =
    (
      configuration,
      value
    ) => {
      const configurationId =
        configuration.id;

      setValues(
        (previous) => ({
          ...previous,

          [configurationId]: {
            ...(previous[
              configurationId
            ] || {}),

            value,
          },
        })
      );

      notifyParent(
        "teams_configuration",
        configuration,
        {
          Value: value,
        }
      );
    };

  /* ==========================================================
     NAVIGATION
     ========================================================== */

  const goToPage = (page) => {
    if (
      page < 1 ||
      page > totalPages
    ) {
      return;
    }

    setCurrentPage(page);
  };

  const goToSecondTablePage =
    (page) => {
      if (
        page < 1 ||
        page > secondTableTotalPages
      ) {
        return;
      }

      setSecondTablePage(page);
    };

  const goToThirdTablePage =
    (page) => {
      if (
        page < 1 ||
        page > thirdTableTotalPages
      ) {
        return;
      }

      setThirdTablePage(page);
    };

  const goToFourthTablePage =
    (page) => {
      if (
        page < 1 ||
        page > fourthTableTotalPages
      ) {
        return;
      }

      setFourthTablePage(page);
    };

  /* ==========================================================
     PAGE NUMBERS
     ========================================================== */

  const pageNumbers = Array.from(
    {
      length: totalPages,
    },
    (_, index) =>
      index + 1
  );

  const secondTablePageNumbers =
    Array.from(
      {
        length:
          secondTableTotalPages,
      },
      (_, index) =>
        index + 1
    );

  const thirdTablePageNumbers =
    Array.from(
      {
        length:
          thirdTableTotalPages,
      },
      (_, index) =>
        index + 1
    );

  const fourthTablePageNumbers =
    Array.from(
      {
        length:
          fourthTableTotalPages,
      },
      (_, index) =>
        index + 1
    );

  /* ==========================================================
     GETTERS
     ========================================================== */

  const getValue = (
    configuration
  ) => {
    const value =
      values[
        configuration.id
      ]?.value;

    return value ===
      undefined ||
      value === null
      ? ""
      : value;
  };

  const getFieldValue = (
    configuration,
    fieldKey
  ) => {
    const value =
      values[
        configuration.id
      ]?.[fieldKey];

    return value ===
      undefined ||
      value === null
      ? ""
      : value;
  };

  const getChannelValue = (
    configuration,
    fieldKey
  ) => {
    const value =
      values[
        configuration.id
      ]?.[fieldKey];

    if (
      value === undefined ||
      value === null
    ) {
      if (
        fieldKey ===
        "NotificationChannels"
      ) {
        return "Email,TeamsCard";
      }

      return "";
    }

    return value;
  };

  /* ==========================================================
     INFORMATION
     ========================================================== */

  const showInformation = (
    configuration
  ) => {
    const isMultiField =
      configuration.isBusinessHours ||
      configuration.scheduleFields;

    const fields =
      configuration.fields ||
      configuration.scheduleFields ||
      [];

    const sampleText =
      isMultiField
        ? fields
            .map(
              (field) =>
                `${field.label}: ${field.sampleValue}`
            )
            .join("\n")
        : configuration.sampleValue;

    alert(
      `${configuration.description}

Sample Value:
${sampleText}

Validation:
${
  configuration.validation ||
  "No validation information available."
}`
    );
  };

  /* ==========================================================
     RENDER
     ========================================================== */

  return (
    <div className="application-configuration">

      {/* ======================================================
          FIRST TABLE
          ====================================================== */}

      <div className="application-configuration-toolbar">
        <h2>
          Application Configuration
        </h2>
      </div>

      <div className="application-configuration-table">

        <div className="configuration-table-header">

          <div className="configuration-col-number">
            #
          </div>

          <div className="configuration-col-description">
            Configuration Description
          </div>

          <div className="configuration-col-sample">
            Sample Value
          </div>

          <div className="configuration-col-value">
            Your Value
          </div>

          <div className="configuration-col-required">
            *
          </div>

          <div className="configuration-col-info">
            Info
          </div>

        </div>

        {currentConfigurations.map(
          (configuration) => {
            const isMultiField =
              configuration.isBusinessHours ||
              configuration.scheduleFields;

            const fields =
              configuration.fields ||
              configuration.scheduleFields ||
              [];

            return (
              <div
                className={`configuration-table-row ${
                  isMultiField
                    ? "configuration-multi-field-row"
                    : ""
                }`}
                key={configuration.id}
              >

                <div className="configuration-col-number">
                  {configuration.id}
                </div>

                <div className="configuration-col-description">
                  {
                    configuration.description
                  }
                </div>

                {isMultiField ? (
                  <div className="configuration-col-sample multi-field-sample">

                    {fields.map(
                      (field) => (
                        <div
                          className="configuration-sub-field"
                          key={field.key}
                        >
                          <span className="configuration-sub-field-label">
                            {field.label}:
                          </span>

                          <span className="sample-value">
                            {
                              field.sampleValue
                            }
                          </span>
                        </div>
                      )
                    )}

                  </div>
                ) : (
                  <div className="configuration-col-sample">

                    <span className="sample-value">
                      {
                        configuration.sampleValue
                      }
                    </span>

                  </div>
                )}

                {isMultiField ? (
                  <div className="configuration-col-value multi-field-value">

                    {fields.map(
                      (field) => (
                        <div
                          className="configuration-sub-field-input"
                          key={field.key}
                        >
                          <input
                            type="text"
                            value={getFieldValue(
                              configuration,
                              field.key
                            )}
                            placeholder="Enter value"
                            onChange={(
                              event
                            ) =>
                              handleValueChange(
                                configuration,
                                field.key,
                                event.target.value
                              )
                            }
                          />
                        </div>
                      )
                    )}

                  </div>
                ) : (
                  <div className="configuration-col-value">

                    <input
                      type="text"
                      value={getValue(
                        configuration
                      )}
                      placeholder="Enter value"
                      onChange={(
                        event
                      ) =>
                        handleValueChange(
                          configuration,
                          null,
                          event.target.value
                        )
                      }
                    />

                  </div>
                )}

                <div className="configuration-col-required">
                  <span className="required-star">
                    *
                  </span>
                </div>

                <div className="configuration-col-info">

                  <button
                    type="button"
                    className="configuration-info-button"
                    title={
                      configuration.validation ||
                      configuration.description
                    }
                    onClick={() =>
                      showInformation(
                        configuration
                      )
                    }
                  >
                    ⓘ
                  </button>

                </div>

              </div>
            );
          }
        )}

      </div>

      {/* ======================================================
          FIRST TABLE FOOTER
          ====================================================== */}

      <div className="application-configuration-footer">

        <div className="configuration-count">
          {totalItems === 0
            ? "0 - 0 of 0"
            : `${startIndex + 1} - ${Math.min(
                endIndex,
                totalItems
              )} of ${totalItems}`}
        </div>

        <div className="configuration-pagination">

          <button
            type="button"
            onClick={() =>
              goToPage(
                safeCurrentPage - 1
              )
            }
            disabled={
              safeCurrentPage === 1
            }
            className="pagination-button"
          >
            ‹
          </button>

          {pageNumbers.map(
            (page) => (
              <button
                type="button"
                key={page}
                onClick={() =>
                  goToPage(page)
                }
                className={`pagination-button ${
                  safeCurrentPage === page
                    ? "active"
                    : ""
                }`}
              >
                {page}
              </button>
            )
          )}

          <button
            type="button"
            onClick={() =>
              goToPage(
                safeCurrentPage + 1
              )
            }
            disabled={
              safeCurrentPage ===
              totalPages
            }
            className="pagination-button"
          >
            ›
          </button>

        </div>

      </div>

      {/* ======================================================
          SECOND TABLE - EMAIL CONFIGURATION
          ====================================================== */}

      <div className="application-configuration-second-section">

        <div className="application-configuration-toolbar">

          <h2>
            Notification Configuration
          </h2>

          <p>
            Configure the email addresses used
            to notify the respective security
            teams.
          </p>

        </div>

        <div className="notification-configuration-table">

          <div className="notification-table-header">

            <div className="notification-col-number">
              #
            </div>

            <div className="notification-col-partition">
              PartitionKey
            </div>

            <div className="notification-col-row">
              RowKey
            </div>

            <div className="notification-col-description">
              Description
            </div>

            <div className="notification-col-sample">
              Sample Value
            </div>

            <div className="notification-col-value">
              Your Value
            </div>

            <div className="notification-col-required">
              *
            </div>

            <div className="notification-col-info">
              Info
            </div>

          </div>

          {currentNotificationConfigurations.map(
            (configuration) => (
              <div
                className="notification-table-row"
                key={configuration.id}
              >

                <div className="notification-col-number">
                  {
                    configuration.displayNumber
                  }
                </div>

                <div className="notification-col-partition">
                  {
                    configuration.partitionKey
                  }
                </div>

                <div className="notification-col-row">
                  {
                    configuration.rowKey
                  }
                </div>

                <div className="notification-col-description">
                  {
                    configuration.description
                  }
                </div>

                <div className="notification-col-sample">

                  <span className="sample-value">
                    {
                      configuration.sampleValue
                    }
                  </span>

                </div>

                <div className="notification-col-value">

                  <input
                    type="email"
                    value={getValue(
                      configuration
                    )}
                    placeholder="Enter email address"
                    onChange={(
                      event
                    ) =>
                      handleEmailValueChange(
                        configuration,
                        event.target.value
                      )
                    }
                  />

                </div>

                <div className="notification-col-required">

                  <span className="required-star">
                    *
                  </span>

                </div>

                <div className="notification-col-info">

                  <button
                    type="button"
                    className="configuration-info-button"
                    title={
                      configuration.validation ||
                      configuration.description
                    }
                    onClick={() =>
                      showInformation(
                        configuration
                      )
                    }
                  >
                    ⓘ
                  </button>

                </div>

              </div>
            )
          )}

        </div>

        {/* SECOND TABLE FOOTER */}

        <div className="application-configuration-footer">

          <div className="configuration-count">
            {secondTableTotalItems ===
            0
              ? "0 - 0 of 0"
              : `${secondTableStartIndex + 1} - ${Math.min(
                  secondTableEndIndex,
                  secondTableTotalItems
                )} of ${secondTableTotalItems}`}
          </div>

          <div className="configuration-pagination">

            <button
              type="button"
              onClick={() =>
                goToSecondTablePage(
                  safeSecondTablePage -
                    1
                )
              }
              disabled={
                safeSecondTablePage ===
                1
              }
              className="pagination-button"
            >
              ‹
            </button>

            {secondTablePageNumbers.map(
              (page) => (
                <button
                  type="button"
                  key={page}
                  onClick={() =>
                    goToSecondTablePage(
                      page
                    )
                  }
                  className={`pagination-button ${
                    safeSecondTablePage ===
                    page
                      ? "active"
                      : ""
                  }`}
                >
                  {page}
                </button>
              )
            )}

            <button
              type="button"
              onClick={() =>
                goToSecondTablePage(
                  safeSecondTablePage +
                    1
                )
              }
              disabled={
                safeSecondTablePage ===
                secondTableTotalPages
              }
              className="pagination-button"
            >
              ›
            </button>

          </div>

        </div>

      </div>

      {/* ======================================================
          THIRD TABLE
          ====================================================== */}

      <div className="application-configuration-third-section">

        <div className="application-configuration-toolbar">

          <h2>
            Notification Channel Configuration
          </h2>

          <p>
            Configure the notification channels,
            recipient email addresses, and Teams
            groups for each workflow.
          </p>

        </div>

        <div className="channel-configuration-table">

          <div className="channel-table-header">

            <div className="channel-col-number">
              #
            </div>

            <div className="channel-col-partition">
              PartitionKey
            </div>

            <div className="channel-col-row">
              RowKey
            </div>

            <div className="channel-col-channels">
              NotificationChannels
            </div>

            <div className="channel-col-type">
              Type
            </div>

            <div className="channel-col-email">
              RecipientEmail
            </div>

            <div className="channel-col-type">
              Type
            </div>

            <div className="channel-col-teams">
              TeamsGroup
            </div>

            <div className="channel-col-type">
              Type
            </div>

          </div>

          {currentChannelConfigurations.map(
            (
              configuration,
              index
            ) => (
              <div
                className="channel-table-row"
                key={configuration.id}
              >

                <div className="channel-col-number">
                  {
                    thirdTableStartIndex +
                    index +
                    1
                  }
                </div>

                <div className="channel-col-partition">
                  {
                    configuration.partitionKey
                  }
                </div>

                <div className="channel-col-row">
                  {
                    configuration.rowKey
                  }
                </div>

                <div className="channel-col-channels">

                  <input
                    type="text"
                    value={getChannelValue(
                      configuration,
                      "NotificationChannels"
                    )}
                    placeholder="Email,TeamsCard"
                    onChange={(
                      event
                    ) =>
                      handleChannelValueChange(
                        configuration,
                        "NotificationChannels",
                        event.target.value
                      )
                    }
                  />

                </div>

                <div className="channel-col-type">

                  <span className="channel-type-value">
                    String
                  </span>

                </div>

                <div className="channel-col-email">

                  <input
                    type="email"
                    value={getChannelValue(
                      configuration,
                      "RecipientEmail"
                    )}
                    placeholder="Enter email"
                    onChange={(
                      event
                    ) =>
                      handleChannelValueChange(
                        configuration,
                        "RecipientEmail",
                        event.target.value
                      )
                    }
                  />

                </div>

                <div className="channel-col-type">

                  <span className="channel-type-value">
                    String
                  </span>

                </div>

                <div className="channel-col-teams">

                  <input
                    type="text"
                    value={getChannelValue(
                      configuration,
                      "TeamsGroup"
                    )}
                    placeholder="Enter Teams Channel ID"
                    onChange={(
                      event
                    ) =>
                      handleChannelValueChange(
                        configuration,
                        "TeamsGroup",
                        event.target.value
                      )
                    }
                  />

                </div>

                <div className="channel-col-type">

                  <span className="channel-type-value">
                    String
                  </span>

                </div>

              </div>
            )
          )}

        </div>

        {/* THIRD TABLE FOOTER */}

        <div className="application-configuration-footer">

          <div className="configuration-count">
            {thirdTableTotalItems ===
            0
              ? "0 - 0 of 0"
              : `${thirdTableStartIndex + 1} - ${Math.min(
                  thirdTableEndIndex,
                  thirdTableTotalItems
                )} of ${thirdTableTotalItems}`}
          </div>

          <div className="configuration-pagination">

            <button
              type="button"
              onClick={() =>
                goToThirdTablePage(
                  safeThirdTablePage -
                    1
                )
              }
              disabled={
                safeThirdTablePage ===
                1
              }
              className="pagination-button"
            >
              ‹
            </button>

            {thirdTablePageNumbers.map(
              (page) => (
                <button
                  type="button"
                  key={page}
                  onClick={() =>
                    goToThirdTablePage(
                      page
                    )
                  }
                  className={`pagination-button ${
                    safeThirdTablePage ===
                    page
                      ? "active"
                      : ""
                  }`}
                >
                  {page}
                </button>
              )
            )}

            <button
              type="button"
              onClick={() =>
                goToThirdTablePage(
                  safeThirdTablePage +
                    1
                )
              }
              disabled={
                safeThirdTablePage ===
                thirdTableTotalPages
              }
              className="pagination-button"
            >
              ›
            </button>

          </div>

        </div>

      </div>

      {/* ======================================================
          FOURTH TABLE
          ====================================================== */}

      <div className="application-configuration-fourth-section">

        <div className="application-configuration-toolbar">

          <h2>
            Teams Recipient Configuration
          </h2>

          <p>
            Configure the Teams recipient values
            for each recipient and value stream.
          </p>

        </div>

        <div className="teams-recipient-configuration-table">

          <div className="teams-recipient-table-header">

            <div className="teams-recipient-col-number">
              #
            </div>

            <div className="teams-recipient-col-partition">
              PartitionKey
            </div>

            <div className="teams-recipient-col-row">
              RowKey
            </div>

            <div className="teams-recipient-col-value">
              Value
            </div>

            <div className="teams-recipient-col-type">
              Value@type
            </div>

          </div>

          {currentTeamsRecipientConfigurations.map(
            (
              configuration,
              index
            ) => (
              <div
                className="teams-recipient-table-row"
                key={configuration.id}
              >

                <div className="teams-recipient-col-number">
                  {
                    fourthTableStartIndex +
                    index +
                    1
                  }
                </div>

                <div className="teams-recipient-col-partition">
                  {
                    configuration.partitionKey
                  }
                </div>

                <div className="teams-recipient-col-row">
                  {
                    configuration.rowKey
                  }
                </div>

                <div className="teams-recipient-col-value">

                  <input
                    type="text"
                    value={getValue(
                      configuration
                    )}
                    placeholder="Enter Teams Channel ID"
                    onChange={(
                      event
                    ) =>
                      handleTeamsRecipientValueChange(
                        configuration,
                        event.target.value
                      )
                    }
                  />

                </div>

                <div className="teams-recipient-col-type">

                  <span className="channel-type-value">
                    String
                  </span>

                </div>

              </div>
            )
          )}

        </div>

        {/* FOURTH TABLE FOOTER */}

        <div className="application-configuration-footer">

          <div className="configuration-count">
            {fourthTableTotalItems ===
            0
              ? "0 - 0 of 0"
              : `${fourthTableStartIndex + 1} - ${Math.min(
                  fourthTableEndIndex,
                  fourthTableTotalItems
                )} of ${fourthTableTotalItems}`}
          </div>

          <div className="configuration-pagination">

            <button
              type="button"
              onClick={() =>
                goToFourthTablePage(
                  safeFourthTablePage -
                    1
                )
              }
              disabled={
                safeFourthTablePage ===
                1
              }
              className="pagination-button"
            >
              ‹
            </button>

            {fourthTablePageNumbers.map(
              (page) => (
                <button
                  type="button"
                  key={page}
                  onClick={() =>
                    goToFourthTablePage(
                      page
                    )
                  }
                  className={`pagination-button ${
                    safeFourthTablePage ===
                    page
                      ? "active"
                      : ""
                  }`}
                >
                  {page}
                </button>
              )
            )}

            <button
              type="button"
              onClick={() =>
                goToFourthTablePage(
                  safeFourthTablePage +
                    1
                )
              }
              disabled={
                safeFourthTablePage ===
                fourthTableTotalPages
              }
              className="pagination-button"
            >
              ›
            </button>

          </div>

        </div>

      </div>

      {/* ======================================================
          DEPLOYMENT
          ====================================================== */}

      <div className="configuration-deployment-section">

        <button
          type="button"
          className="configuration-deploy-button"
          onClick={onDeploy}
          disabled={isDeploying}
        >
          {isDeploying
            ? "Deploying..."
            : "Deploy"}
        </button>

      </div>

      {/* ======================================================
          REQUIRED INFO
          ====================================================== */}

      <div className="configuration-required-info">

        <span className="configuration-info-circle">
          i
        </span>

        <span>
          All fields marked with{" "}
          <strong>*</strong>{" "}
          are required.
        </span>

      </div>

    </div>
  );
}

export default ApplicationConfiguration;