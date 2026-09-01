import csv
import logging
import os

from app.validators.configuration_import import (
    determine_special_validation,
    validate_special,
    validate_email,
    validate_teams_group,
    validate_teams_recipient_id,
)


logger = logging.getLogger(__name__)


# ============================================================
# CSV LOCATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

CSV_BASE_PATH = os.path.join(
    BASE_DIR,
    "data"
)


# ============================================================
# CSV FILES
# ============================================================

APP_CONFIGURATION_CSV = os.path.join(
    CSV_BASE_PATH,
    "AppConfiguration.csv"
)

EMAIL_CONFIGURATION_CSV = os.path.join(
    CSV_BASE_PATH,
    "EmailRecipientConfiguration.csv"
)

NOTIFICATION_TEMPLATES_CSV = os.path.join(
    CSV_BASE_PATH,
    "NotificationTemplates.csv"
)

NOTIFICATION_CONFIGURATION_CSV = os.path.join(
    CSV_BASE_PATH,
    "NotificationConfiguration.csv"
)

TEAMS_CONFIGURATION_CSV = os.path.join(
    CSV_BASE_PATH,
    "TeamsRecipientConfiguration.csv"
)


# ============================================================
# SERVICE
# ============================================================

class ConfigurationImportService:

    def __init__(self, table_storage_service):

        self.table_storage_service = (
            table_storage_service
        )

    # ========================================================
    # READ CSV
    # ========================================================

    def _read_csv(self, csv_path):

        if not os.path.exists(csv_path):

            raise FileNotFoundError(
                f"Configuration CSV not found: {csv_path}"
            )

        rows = []

        with open(
            csv_path,
            mode="r",
            encoding="utf-8-sig",
            newline=""
        ) as file:

            reader = csv.DictReader(file)

            if not reader.fieldnames:

                raise ValueError(
                    f"CSV has no header: {csv_path}"
                )

            required_columns = {
                "PartitionKey",
                "RowKey"
            }

            missing_columns = (
                required_columns
                - set(reader.fieldnames)
            )

            if missing_columns:

                raise ValueError(
                    f"CSV {csv_path} is missing columns: "
                    f"{', '.join(missing_columns)}"
                )

            for row in reader:

                rows.append(row)

        return rows

    # ========================================================
    # APP CONFIGURATION
    # ========================================================

    def process_app_configuration(
        self,
        configurations
    ):

        results = []

        entities = []

        csv_rows = self._read_csv(
            APP_CONFIGURATION_CSV
        )

        if len(configurations) != len(csv_rows):

            raise ValueError(
                "AppConfiguration value count does not match "
                "the number of rows in AppConfiguration.csv. "
                f"CSV rows: {len(csv_rows)}, "
                f"received values: {len(configurations)}"
            )

        for config, csv_row in zip(
            configurations,
            csv_rows
        ):

            partition_key = (
                csv_row["PartitionKey"].strip()
            )

            row_key = (
                csv_row["RowKey"].strip()
            )

            value = config.Value

            logger.info(
                "Processing AppConfiguration %s/%s",
                partition_key,
                row_key
            )

            value_type = self._get_value_type(
                config
            )

            is_business_day_row = (
                partition_key.lower() == "businessday"
                and row_key.lower() == "workingdayandhour"
            )

            special_validation = (
                determine_special_validation(
                    partition_key,
                    row_key,
                    value_type,
                    value
                )
            )

            if is_business_day_row and (
                value is None
                or str(value).strip() == ""
            ):

                logger.info(
                    "Value is empty for "
                    "BusinessDay/WorkingDayandHour. "
                    "Value validation skipped."
                )

            else:

                valid, error = validate_special(
                    value,
                    special_validation
                )

                if not valid:

                    raise ValueError(
                        f"AppConfiguration validation failed "
                        f"for {partition_key}/{row_key}: "
                        f"{error}"
                    )

            entity = {
                "PartitionKey": partition_key,
                "RowKey": row_key
            }

            if (
                value is not None
                and str(value).strip() != ""
            ):

                entity["Value"] = self._convert_value(
                    value,
                    value_type
                )

            if is_business_day_row:

                self._validate_business_day(
                    config
                )

                entity["region"] = (
                    config.region
                )

                entity["startTime"] = (
                    config.startTime
                )

                entity["endTime"] = (
                    config.endTime
                )

                entity["businessDays"] = (
                    config.businessDays
                )

            entities.append(entity)

            results.append({
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "status": "validated"
            })

        logger.info(
            "Uploading %s AppConfiguration entities "
            "in batches of 15.",
            len(entities)
        )

        self.table_storage_service.batch_upsert_entities(
            table_name="AppConfiguration",
            entities=entities,
            batch_size=15
        )

        for result in results:

            result["status"] = "uploaded"

        return results

    # ========================================================
    # EMAIL CONFIGURATION
    # ========================================================

    def process_email_configuration(
        self,
        configurations
    ):

        results = []

        entities = []

        csv_rows = self._read_csv(
            EMAIL_CONFIGURATION_CSV
        )

        if len(configurations) != len(csv_rows):

            raise ValueError(
                "Email configuration value count does not "
                "match EmailRecipientConfiguration.csv. "
                f"CSV rows: {len(csv_rows)}, "
                f"received values: {len(configurations)}"
            )

        for config, csv_row in zip(
            configurations,
            csv_rows
        ):

            partition_key = (
                csv_row["PartitionKey"].strip()
            )

            row_key = (
                csv_row["RowKey"].strip()
            )

            value = config.Value

            if not value:

                raise ValueError(
                    f"Email value is mandatory for "
                    f"{partition_key}/{row_key}"
                )

            if partition_key.lower() == "recipient":

                valid, error = validate_email(
                    value
                )

                if not valid:

                    raise ValueError(
                        f"Invalid email for "
                        f"{partition_key}/{row_key}: "
                        f"{error}"
                    )

            else:

                if not str(value).strip():

                    raise ValueError(
                        f"Value cannot be empty for "
                        f"{partition_key}/{row_key}"
                    )

            entity = {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Value": value
            }

            entities.append(entity)

            results.append({
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "status": "validated"
            })

        logger.info(
            "Uploading %s EmailRecipientConfiguration "
            "entities in batches of 15.",
            len(entities)
        )

        self.table_storage_service.batch_upsert_entities(
            table_name="EmailRecipientConfiguration",
            entities=entities,
            batch_size=15
        )

        for result in results:

            result["status"] = "uploaded"

        return results

    # ========================================================
    # NOTIFICATION TEMPLATES
    # ========================================================

    def process_notification_templates(self):
        """
        Upload NotificationTemplates.csv directly into
        the NotificationTemplates Azure Table.

        No user input is required.

        Every CSV row becomes one Azure Table entity.

        IMPORTANT:
        Columns ending with '@type' are metadata columns
        from the CSV and are NOT uploaded to Azure Table.

        Example:

            AdaptiveContent@type
            Importance@type
            NotificationContent@type

        These are skipped.

        Upload is performed in batches of 15.
        """

        results = []

        entities = []

        # ----------------------------------------------------
        # READ CSV
        # ----------------------------------------------------

        csv_rows = self._read_csv(
            NOTIFICATION_TEMPLATES_CSV
        )

        if not csv_rows:

            logger.info(
                "NotificationTemplates.csv is empty."
            )

            return results

        # ----------------------------------------------------
        # PROCESS ALL CSV ROWS
        # ----------------------------------------------------

        for csv_row in csv_rows:

            # ------------------------------------------------
            # PARTITION KEY
            # ------------------------------------------------

            partition_key = str(
                csv_row.get(
                    "PartitionKey",
                    ""
                )
            ).strip()

            # ------------------------------------------------
            # ROW KEY
            # ------------------------------------------------

            row_key = str(
                csv_row.get(
                    "RowKey",
                    ""
                )
            ).strip()

            if not partition_key:

                raise ValueError(
                    "NotificationTemplates CSV contains "
                    "an empty PartitionKey."
                )

            if not row_key:

                raise ValueError(
                    "NotificationTemplates CSV contains "
                    "an empty RowKey."
                )

            # ------------------------------------------------
            # CREATE ENTITY
            # ------------------------------------------------

            entity = {
                "PartitionKey": partition_key,
                "RowKey": row_key
            }

            # ------------------------------------------------
            # COPY CSV PROPERTIES
            # ------------------------------------------------

            for key, value in csv_row.items():

                # --------------------------------------------
                # Ignore invalid / empty column names
                # --------------------------------------------

                if key is None:

                    continue

                key = str(key).strip()

                if not key:

                    continue

                # --------------------------------------------
                # PartitionKey / RowKey already handled
                # --------------------------------------------

                if key in (
                    "PartitionKey",
                    "RowKey"
                ):

                    continue

                # --------------------------------------------
                # IMPORTANT:
                # Do NOT upload @type metadata columns
                # --------------------------------------------

                if key.endswith("@type"):

                    logger.debug(
                        "Skipping metadata column: %s",
                        key
                    )

                    continue

                # --------------------------------------------
                # Skip completely empty values
                # --------------------------------------------

                if value is None:

                    continue

                value = str(value)

                if value.strip() == "":

                    continue

                # --------------------------------------------
                # Add normal property
                # --------------------------------------------

                entity[key] = value

            # ------------------------------------------------
            # LOG ENTITY
            # ------------------------------------------------

            logger.debug(
                "Prepared NotificationTemplates entity "
                "%s/%s with %s properties.",
                partition_key,
                row_key,
                len(entity)
            )

            # ------------------------------------------------
            # ADD ENTITY
            # ------------------------------------------------

            entities.append(entity)

            results.append({
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "status": "validated"
            })

        # ----------------------------------------------------
        # BATCH UPLOAD
        # ----------------------------------------------------

        logger.info(
            "Uploading %s NotificationTemplates entities "
            "in batches of 15.",
            len(entities)
        )

        self.table_storage_service.batch_upsert_entities(
            table_name="NotificationTemplates",
            entities=entities,
            batch_size=15
        )

        # ----------------------------------------------------
        # UPDATE STATUS
        # ----------------------------------------------------

        for result in results:

            result["status"] = "uploaded"

        logger.info(
            "NotificationTemplates upload completed. "
            "Total entities: %s",
            len(entities)
        )

        return results

    # ========================================================
    # NOTIFICATION CONFIGURATION
    # ========================================================

    def process_notification_configuration(
        self,
        configurations
    ):

        results = []

        entities = []

        csv_rows = self._read_csv(
            NOTIFICATION_CONFIGURATION_CSV
        )

        if len(configurations) != len(csv_rows):

            raise ValueError(
                "Notification configuration value count "
                "does not match NotificationConfiguration.csv. "
                f"CSV rows: {len(csv_rows)}, "
                f"received values: {len(configurations)}"
            )

        for config, csv_row in zip(
            configurations,
            csv_rows
        ):

            partition_key = (
                csv_row["PartitionKey"].strip()
            )

            row_key = (
                csv_row["RowKey"].strip()
            )

            recipient_email = (
                config.RecipientEmail
            )

            teams_group = (
                config.TeamsGroup
            )

            notification_channels = (
                config.NotificationChannels
            )

            valid, error = validate_email(
                recipient_email
            )

            if not valid:

                raise ValueError(
                    f"Invalid RecipientEmail for "
                    f"{partition_key}/{row_key}: "
                    f"{error}"
                )

            if teams_group:

                valid, error = validate_teams_group(
                    teams_group
                )

                if not valid:

                    raise ValueError(
                        f"Invalid TeamsGroup for "
                        f"{partition_key}/{row_key}: "
                        f"{error}"
                    )

            if (
                not notification_channels
                or not notification_channels.strip()
            ):

                raise ValueError(
                    f"NotificationChannels cannot be empty "
                    f"for {partition_key}/{row_key}"
                )

            entity = {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "NotificationChannels":
                    notification_channels,
                "RecipientEmail":
                    recipient_email
            }

            if teams_group:

                entity["TeamsGroup"] = (
                    teams_group
                )

            entities.append(entity)

            results.append({
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "status": "validated"
            })

        logger.info(
            "Uploading %s NotificationConfiguration "
            "entities in batches of 15.",
            len(entities)
        )

        self.table_storage_service.batch_upsert_entities(
            table_name="NotificationConfiguration",
            entities=entities,
            batch_size=15
        )

        for result in results:

            result["status"] = "uploaded"

        return results

    # ========================================================
    # TEAMS CONFIGURATION
    # ========================================================

    def process_teams_configuration(
        self,
        configurations
    ):

        results = []

        entities = []

        csv_rows = self._read_csv(
            TEAMS_CONFIGURATION_CSV
        )

        if len(configurations) != len(csv_rows):

            raise ValueError(
                "Teams configuration value count does not "
                "match TeamsRecipientConfiguration.csv. "
                f"CSV rows: {len(csv_rows)}, "
                f"received values: {len(configurations)}"
            )

        for config, csv_row in zip(
            configurations,
            csv_rows
        ):

            partition_key = (
                csv_row["PartitionKey"].strip()
            )

            row_key = (
                csv_row["RowKey"].strip()
            )

            value = config.Value

            if not value:

                raise ValueError(
                    f"Teams value is mandatory for "
                    f"{partition_key}/{row_key}"
                )

            if partition_key.lower() == "recipient":

                valid, error = (
                    validate_teams_recipient_id(
                        value
                    )
                )

                if not valid:

                    raise ValueError(
                        f"Invalid Teams Recipient ID "
                        f"for {partition_key}/{row_key}: "
                        f"{error}"
                    )

            else:

                if not str(value).strip():

                    raise ValueError(
                        f"Value cannot be empty for "
                        f"{partition_key}/{row_key}"
                    )

            entity = {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Value": value
            }

            entities.append(entity)

            results.append({
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "status": "validated"
            })

        logger.info(
            "Uploading %s TeamsRecipientConfiguration "
            "entities in batches of 15.",
            len(entities)
        )

        self.table_storage_service.batch_upsert_entities(
            table_name="TeamsRecipientConfiguration",
            entities=entities,
            batch_size=15
        )

        for result in results:

            result["status"] = "uploaded"

        return results

    # ========================================================
    # BUSINESS DAY VALIDATION
    # ========================================================

    def _validate_business_day(
        self,
        config
    ):

        required_fields = {
            "region": config.region,
            "startTime": config.startTime,
            "endTime": config.endTime,
            "businessDays": config.businessDays
        }

        for name, value in required_fields.items():

            if (
                value is None
                or str(value).strip() == ""
            ):

                raise ValueError(
                    f"{name} is mandatory for "
                    "BusinessDay/WorkingDayandHour"
                )

        # ----------------------------------------------------
        # REGION
        # ----------------------------------------------------

        valid, error = validate_special(
            config.region,
            "REGION"
        )

        if not valid:

            raise ValueError(
                f"Invalid region: {error}"
            )

        # ----------------------------------------------------
        # START TIME
        # ----------------------------------------------------

        valid, error = validate_special(
            config.startTime,
            "TIME"
        )

        if not valid:

            raise ValueError(
                f"Invalid startTime: {error}"
            )

        # ----------------------------------------------------
        # END TIME
        # ----------------------------------------------------

        valid, error = validate_special(
            config.endTime,
            "TIME"
        )

        if not valid:

            raise ValueError(
                f"Invalid endTime: {error}"
            )

        # ----------------------------------------------------
        # BUSINESS DAYS
        # ----------------------------------------------------

        valid, error = validate_special(
            config.businessDays,
            "INTEGER_LIST_1_7"
        )

        if not valid:

            raise ValueError(
                f"Invalid businessDays: {error}"
            )

    # ========================================================
    # TYPE
    # ========================================================

    def _get_value_type(
        self,
        config
    ):

        value = config.Value

        if isinstance(value, bool):

            return "boolean"

        if isinstance(value, int):

            return "int"

        if isinstance(value, float):

            return "double"

        return "string"

    # ========================================================
    # CONVERSION
    # ========================================================

    def _convert_value(
        self,
        value,
        value_type
    ):

        if value_type == "int":

            return int(value)

        if value_type == "double":

            return float(value)

        if value_type == "boolean":

            return bool(value)

        return str(value)