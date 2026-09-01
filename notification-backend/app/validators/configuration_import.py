import json
import re
from datetime import datetime
from urllib.parse import urlparse


# ============================================================
# BASIC
# ============================================================

def validate_non_empty(value):

    if value is None:
        return False, "Value cannot be empty."

    value = str(value).strip()

    if not value:
        return False, "Value cannot be empty."

    return True, ""


# ============================================================
# OPTIONAL BUSINESS DAY VALUE
# ============================================================

def validate_optional_business_day(value):

    # --------------------------------------------------------
    # ONLY BusinessDay / WorkingDayandHour can be empty
    # --------------------------------------------------------

    if value is None:
        return True, ""

    value = str(value).strip()

    if not value:
        return True, ""

    # If a value is provided, it must still be non-empty.
    return True, ""


# ============================================================
# BOOLEAN
# ============================================================

def validate_boolean(value):

    value = str(value).strip().lower()

    if value not in ("true", "false"):
        return False, "Value must be true or false."

    return True, ""


# ============================================================
# INTEGER
# ============================================================

def validate_integer(value):

    value = str(value).strip()

    if not re.fullmatch(r"-?\d+", value):
        return False, "Enter a whole number."

    return True, ""


def validate_positive_integer(value):

    value = str(value).strip()

    if not re.fullmatch(r"\d+", value):
        return False, "Enter a whole number greater than 0."

    if int(value) <= 0:
        return False, "Value must be greater than 0."

    return True, ""


def validate_non_negative_integer(value):

    value = str(value).strip()

    if not re.fullmatch(r"\d+", value):
        return False, "Enter a whole number greater than or equal to 0."

    return True, ""


# ============================================================
# INTEGER LIST
# ============================================================

def validate_integer_list(
    value,
    positive=False,
    min_value=None,
    max_value=None
):

    if isinstance(value, list):

        parsed = value

    else:

        value = str(value).strip()

        try:
            parsed = json.loads(value)

        except Exception:
            return False, "Enter a valid JSON integer list."

    if not isinstance(parsed, list):
        return False, "Value must be a list."

    if len(parsed) == 0:
        return False, "List cannot be empty."

    for item in parsed:

        if isinstance(item, bool) or not isinstance(item, int):

            return False, "List must contain whole numbers only."

        if positive and item <= 0:

            return False, "List must contain positive whole numbers."

        if min_value is not None and item < min_value:

            return False, f"List values must be at least {min_value}."

        if max_value is not None and item > max_value:

            return False, f"List values must not exceed {max_value}."

    return True, ""


# ============================================================
# LIST
# ============================================================

def validate_list(value):

    if isinstance(value, list):

        return True, ""

    try:

        parsed = json.loads(
            str(value).strip()
        )

        if isinstance(parsed, list):

            return True, ""

    except Exception:

        pass

    return False, "Enter a valid JSON list."


# ============================================================
# JSON OBJECT
# ============================================================

def validate_json_object(value):

    if isinstance(value, dict):

        return True, ""

    try:

        parsed = json.loads(
            str(value).strip()
        )

        if isinstance(parsed, dict):

            return True, ""

    except Exception:

        pass

    return False, "Enter a valid JSON object."


# ============================================================
# EMAIL
# ============================================================

def validate_email(value):

    pattern = (
        r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+"
        r"@[A-Za-z0-9-]+"
        r"(?:\.[A-Za-z0-9-]+)+$"
    )

    value = str(value).strip()

    if not value:

        return False, "Email address cannot be empty."

    if not re.fullmatch(pattern, value):

        return False, "Enter a valid email address."

    return True, ""


# ============================================================
# EMAIL LIST
# ============================================================

def validate_email_list(value):

    if isinstance(value, list):

        values = [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    else:

        values = [
            item.strip()
            for item in str(value).split(";")
            if item.strip()
        ]

    if not values:

        return False, "Enter at least one email address."

    for email in values:

        valid, message = validate_email(email)

        if not valid:

            return False, f"Invalid email: {email}"

    return True, ""


# ============================================================
# TEAMS GROUP
# ============================================================

def validate_teams_group(value):

    value = str(value).strip()

    if not value:

        return False, "TeamsGroup cannot be empty."

    if len(value) > 255:

        return False, "TeamsGroup cannot exceed 255 characters."

    return True, ""


# ============================================================
# TEAMS RECIPIENT ID
# ============================================================

def validate_teams_recipient_id(value):

    value = str(value).strip()

    if not value:

        return False, "Teams Recipient ID cannot be empty."

    recipient_ids = [
        item.strip()
        for item in value.split(";")
        if item.strip()
    ]

    pattern = (
        r"^(?:"
        r"19:[A-Za-z0-9._:+\-]+@thread\.v2"
        r"|"
        r"48:[A-Za-z0-9._:+\-]+"
        r")$"
    )

    for recipient_id in recipient_ids:

        if not re.fullmatch(pattern, recipient_id):

            return (
                False,
                f"Invalid Teams Recipient ID: {recipient_id}."
            )

    return True, ""


# ============================================================
# URL
# ============================================================

def validate_https_url(value):

    try:

        parsed = urlparse(
            str(value).strip()
        )

        if parsed.scheme != "https":

            return False, "URL must use HTTPS."

        if not parsed.netloc:

            return False, "Enter a valid HTTPS URL."

    except Exception:

        return False, "Enter a valid HTTPS URL."

    return True, ""


# ============================================================
# TIME
# ============================================================

def validate_time(value):

    try:

        datetime.strptime(
            str(value).strip(),
            "%H:%M:%S"
        )

        return True, ""

    except ValueError:

        return False, "Enter time in HH:MM:SS format."


# ============================================================
# DAY
# ============================================================

def validate_day(value):

    valid_days = {
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday"
    }

    if str(value).strip().lower() not in valid_days:

        return False, "Enter a valid weekday."

    return True, ""


# ============================================================
# HOUR
# ============================================================

def validate_hour(value):

    try:

        number = int(value)

    except Exception:

        return False, "Enter a whole number."

    if number < 0 or number > 23:

        return False, "Hour must be between 0 and 23."

    return True, ""


# ============================================================
# MINUTE
# ============================================================

def validate_minute(value):

    try:

        number = int(value)

    except Exception:

        return False, "Enter a whole number."

    if number < 0 or number > 59:

        return False, "Minute must be between 0 and 59."

    return True, ""


# ============================================================
# TIMEZONE
# ============================================================

def validate_timezone(value):

    value = str(value).strip()

    if not value:

        return False, "Timezone cannot be empty."

    if value.upper() in ("UTC", "GMT", "IST"):

        return True, ""

    if not re.fullmatch(
        r"[A-Za-z_]+(?:/[A-Za-z0-9_+\-]+)+",
        value
    ):

        return (
            False,
            "Enter a valid IANA timezone."
        )

    return True, ""


# ============================================================
# REGION
# ============================================================

def validate_region(value):

    if not str(value).strip():

        return False, "Region cannot be empty."

    return True, ""


# ============================================================
# STORAGE ACCOUNT
# ============================================================

def validate_storage_account_name(value):

    value = str(value).strip()

    if not re.fullmatch(
        r"[a-z0-9]{3,24}",
        value
    ):

        return (
            False,
            "Storage account name must contain "
            "3-24 lowercase letters and numbers."
        )

    return True, ""


# ============================================================
# TABLE NAME
# ============================================================

def validate_table_name(value):

    value = str(value).strip()

    if not re.fullmatch(
        r"[A-Za-z][A-Za-z0-9]{2,62}",
        value
    ):

        return False, "Invalid Azure Table Storage table name."

    return True, ""


# ============================================================
# DETERMINE VALIDATION
# ============================================================

def determine_special_validation(
    partition_key,
    row_key,
    value_type,
    sample_value=None
):

    pk = str(partition_key).lower().strip()
    rk = str(row_key).lower().strip()
    vt = str(value_type).lower().strip()

    # ========================================================
    # SPECIAL CASE
    # BusinessDay / WorkingDayandHour
    #
    # Value is allowed to be EMPTY ONLY for this row.
    # ========================================================

    if (
        pk == "businessday"
        and rk == "workingdayandhour"
    ):

        return "OPTIONAL_BUSINESS_DAY"

    # ========================================================
    # NORMAL VALIDATIONS
    # ========================================================

    if pk == "region" or pk.endswith(":regions"):

        return "REGION"

    if vt == "boolean":

        return "BOOLEAN"

    if vt in ("int", "int32", "int64"):

        return "INTEGER_SPECIAL"

    if (
        "businesshoursstart" in rk
        or "businesshoursend" in rk
        or "starttime" in rk
        or "endtime" in rk
    ):

        return "TIME"

    if "targetday" in rk:

        return "DAY"

    if "targethour" in rk:

        return "HOUR"

    if "targetminute" in rk:

        return "MINUTE"

    if "timezone" in rk:

        return "TIMEZONE"

    if "smtpserver" in rk:

        return "SMTP_SERVER"

    if (
        rk == "escalationlevels"
        and pk == "followup"
    ):

        return "JSON_OBJECT"

    if (
        rk == "notificationtemplates"
        and pk == "followup"
    ):

        return "JSON_OBJECT"

    if (
        "email" in rk
        or "recipients" in rk
        or rk.endswith("dl")
        or "approverdl" in rk
        or "securityteamdl" in rk
    ):

        return "EMAIL_LIST"

    if "webhookurl" in rk or "siteurl" in rk:

        return "HTTPS_URL"

    if "queue" in rk:

        return "QUEUE_NAME"

    if "storageaccountname" in rk:

        return "STORAGE_ACCOUNT_NAME"

    if rk == "tablename" or rk.endswith("tablename"):

        return "TABLE_NAME"

    if "workingdays" in rk or "businessdays" in rk:

        return "INTEGER_LIST_1_7"

    if (
        rk == "qualysscan"
        or "reminderinterval" in rk
    ):

        return "POSITIVE_INTEGER_LIST"

    positive_names = {
        "maxretrycount",
        "initialintervalhours",
        "maxfollowupcount",
        "subsequentintervalhours",
        "reportpollinginterval",
        "maxtriagingdays",
        "cmdb:limit",
        "daystokeep",
        "exclusionapprovalhours",
        "initialassessmentdays",
        "maxassetsperbatch",
        "reporttemplateid"
    }

    if rk in positive_names:

        return "POSITIVE_INTEGER"

    sample = str(sample_value or "").strip()

    if sample.startswith("{"):

        return "JSON_OBJECT"

    if sample.startswith("["):

        return "LIST"

    return "NON_EMPTY"


# ============================================================
# APPLY VALIDATION
# ============================================================

def validate_special(value, validation):

    validation = validation.upper()

    validators = {

        "NON_EMPTY":
            validate_non_empty,

        "OPTIONAL_BUSINESS_DAY":
            validate_optional_business_day,

        "BOOLEAN":
            validate_boolean,

        "INTEGER_SPECIAL":
            validate_non_negative_integer,

        "POSITIVE_INTEGER":
            validate_positive_integer,

        "LIST":
            validate_list,

        "JSON_OBJECT":
            validate_json_object,

        "EMAIL_LIST":
            validate_email_list,

        "HTTPS_URL":
            validate_https_url,

        "TIME":
            validate_time,

        "DAY":
            validate_day,

        "HOUR":
            validate_hour,

        "MINUTE":
            validate_minute,

        "REGION":
            validate_region,

        "TIMEZONE":
            validate_timezone,

        "TABLE_NAME":
            validate_table_name,

        "STORAGE_ACCOUNT_NAME":
            validate_storage_account_name,
    }

    # ========================================================
    # POSITIVE INTEGER LIST
    # ========================================================

    if validation == "POSITIVE_INTEGER_LIST":

        return validate_integer_list(
            value,
            positive=True
        )

    # ========================================================
    # INTEGER LIST 1-7
    # ========================================================

    if validation == "INTEGER_LIST_1_7":

        return validate_integer_list(
            value,
            min_value=1,
            max_value=7
        )

    # ========================================================
    # FIND VALIDATOR
    # ========================================================

    validator = validators.get(
        validation
    )

    if validator:

        return validator(value)

    # ========================================================
    # DEFAULT
    # ========================================================

    return validate_non_empty(value)