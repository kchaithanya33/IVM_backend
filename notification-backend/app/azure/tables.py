
import os
import subprocess
import json

from azure.data.tables import (
    TableServiceClient,
    UpdateMode,
)


class AzureCLIError(Exception):
    pass


# ============================================================
# AZURE CLI EXECUTABLE
# ============================================================

# Windows:
#     Azure CLI is normally exposed as az.cmd
#
# Linux/Docker:
#     Azure CLI is exposed as az

AZ_CLI = "az.cmd" if os.name == "nt" else "az"


# ============================================================
# RUN AZURE CLI COMMAND
# ============================================================

def run_az(command: list[str]):

    full_command = [
        AZ_CLI,
        *command
    ]

    print()
    print("=" * 70)
    print("Running Azure CLI command:")
    print(" ".join(full_command))
    print("=" * 70)

    try:

        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            shell=False
        )

    except FileNotFoundError:

        raise AzureCLIError(
            f"Azure CLI executable '{AZ_CLI}' was not found. "
            f"Please make sure Azure CLI is installed and available in PATH."
        )

    # --------------------------------------------------------
    # Azure CLI command failed
    # --------------------------------------------------------

    if result.returncode != 0:

        error = (
            result.stderr.strip()
            or result.stdout.strip()
            or "Azure CLI command failed."
        )

        print()
        print("Azure CLI ERROR:")
        print(error)

        raise AzureCLIError(error)

    # --------------------------------------------------------
    # Command output
    # --------------------------------------------------------

    output = result.stdout.strip()

    print()
    print("Azure CLI command completed successfully.")

    if output:

        print("Output:")
        print(output)

    # --------------------------------------------------------
    # No output
    # --------------------------------------------------------

    if not output:

        return None

    # --------------------------------------------------------
    # Try JSON
    # --------------------------------------------------------

    try:

        return json.loads(output)

    except json.JSONDecodeError:

        return output


# ============================================================
# SET AZURE SUBSCRIPTION
# ============================================================

def set_subscription(
    subscription_id: str
):

    return run_az(
        [
            "account",
            "set",
            "--subscription",
            subscription_id
        ]
    )


# ============================================================
# RESOURCE GROUP
# ============================================================

def create_resource_group(
    resource_group_name: str,
    location: str
):

    return run_az(
        [
            "group",
            "create",

            "--name",
            resource_group_name,

            "--location",
            location,

            "--output",
            "json"
        ]
    )


# ============================================================
# STORAGE ACCOUNT
# ============================================================

def create_storage_account(
    resource_group_name: str,
    storage_account_name: str,
    location: str
):

    return run_az(
        [
            "storage",
            "account",
            "create",

            "--resource-group",
            resource_group_name,

            "--name",
            storage_account_name,

            "--location",
            location,

            "--sku",
            "Standard_LRS",

            "--kind",
            "StorageV2",

            "--output",
            "json"
        ]
    )


# ============================================================
# STORAGE ACCOUNT KEY
# ============================================================

def get_storage_account_key(
    resource_group_name: str,
    storage_account_name: str
):

    return run_az(
        [
            "storage",
            "account",
            "keys",
            "list",

            "--resource-group",
            resource_group_name,

            "--account-name",
            storage_account_name,

            "--query",
            "[0].value",

            "--output",
            "tsv"
        ]
    )


# ============================================================
# CREATE SINGLE TABLE
# ============================================================

def create_table(
    storage_account_name: str,
    storage_account_key: str,
    table_name: str
):

    return run_az(
        [
            "storage",
            "table",
            "create",

            "--name",
            table_name,

            "--account-name",
            storage_account_name,

            "--account-key",
            storage_account_key,

            "--output",
            "json"
        ]
    )


# ============================================================
# CREATE ALL TABLES
# ============================================================

def create_tables(
    storage_account_name: str,
    storage_account_key: str,
    table_names: list[str]
):

    results = []

    for table_name in table_names:

        print()
        print("-" * 70)
        print(f"Creating table: {table_name}")
        print("-" * 70)

        result = create_table(
            storage_account_name,
            storage_account_key,
            table_name
        )

        results.append(
            {
                "table_name": table_name,
                "status": "created",
                "result": result
            }
        )

    return results


# ============================================================
# CREATE SINGLE QUEUE
# ============================================================

def create_queue(
    storage_account_name: str,
    storage_account_key: str,
    queue_name: str
):
    """
    Create a single Azure Storage Queue.
    """

    return run_az(
        [
            "storage",
            "queue",
            "create",

            "--name",
            queue_name,

            "--account-name",
            storage_account_name,

            "--account-key",
            storage_account_key,

            "--output",
            "json"
        ]
    )


# ============================================================
# CREATE ALL QUEUES
# ============================================================

def create_queues(
    storage_account_name: str,
    storage_account_key: str,
    queue_names: list[str]
):
    """
    Create all required Azure Storage Queues.
    """

    results = []

    for queue_name in queue_names:

        print()
        print("-" * 70)
        print(f"Creating queue: {queue_name}")
        print("-" * 70)

        result = create_queue(
            storage_account_name,
            storage_account_key,
            queue_name
        )

        results.append(
            {
                "queue_name": queue_name,
                "status": "created",
                "result": result
            }
        )

    return results


# ============================================================
# INSERT SINGLE ENTITY
# ============================================================

def insert_table_entity(
    storage_account_name: str,
    storage_account_key: str,
    table_name: str,
    entity: dict
):
    """
    Insert one entity into Azure Table Storage.

    This function is only for cases where exactly one
    entity needs to be inserted.

    Multiple entities should use
    batch_upsert_entities().
    """

    if not isinstance(entity, dict):

        raise ValueError(
            "Entity must be a JSON object."
        )

    if "PartitionKey" not in entity:

        raise ValueError(
            "Entity must contain 'PartitionKey'."
        )

    if "RowKey" not in entity:

        raise ValueError(
            "Entity must contain 'RowKey'."
        )

    partition_key = str(
        entity["PartitionKey"]
    )

    row_key = str(
        entity["RowKey"]
    )

    entity_arguments = []

    for key, value in entity.items():

        if isinstance(value, bool):

            value = str(value).lower()

        elif isinstance(value, (dict, list)):

            value = json.dumps(value)

        elif value is None:

            continue

        else:

            value = str(value)

        entity_arguments.append(
            f"{key}={value}"
        )

    print()
    print("-" * 70)
    print(
        f"Inserting single entity into table: {table_name}"
    )
    print(
        f"PartitionKey: {partition_key}"
    )
    print(
        f"RowKey: {row_key}"
    )
    print("-" * 70)

    return run_az(
        [
            "storage",
            "entity",
            "insert",

            "--table-name",
            table_name,

            "--account-name",
            storage_account_name,

            "--account-key",
            storage_account_key,

            "--entity",
            *entity_arguments,

            "--output",
            "json"
        ]
    )


# ============================================================
# BATCH INSERT / UPSERT ENTITIES
# ============================================================

def insert_table_entities_batch(
    storage_account_name: str,
    storage_account_key: str,
    table_name: str,
    entities: list[dict],
    batch_size: int = 15
):
    """
    Upload multiple Azure Table entities in batches.

    IMPORTANT:

    - This function does NOT call Azure CLI for every row.
    - It uses TableServiceClient.
    - It groups entities by PartitionKey.
    - Each transaction contains up to 15 entities.
    - All entities in a transaction must have the same
      PartitionKey.

    Example:

        39 entities

        Batch 1 -> 15
        Batch 2 -> 15
        Batch 3 -> 9
    """

    # ========================================================
    # VALIDATE INPUT
    # ========================================================

    if not isinstance(entities, list):

        raise ValueError(
            "entities must be a list."
        )

    if not entities:

        print(
            "No entities to upload."
        )

        return []

    if batch_size <= 0:

        raise ValueError(
            "batch_size must be greater than 0."
        )

    # --------------------------------------------------------
    # Application maximum
    # --------------------------------------------------------

    if batch_size > 15:

        print(
            "Requested batch size is greater than 15."
        )

        print(
            "Using batch size = 15."
        )

        batch_size = 15

    # ========================================================
    # VALIDATE AND GROUP BY PARTITION KEY
    # ========================================================

    entities_by_partition = {}

    for index, entity in enumerate(
        entities,
        start=1
    ):

        if not isinstance(entity, dict):

            raise ValueError(
                f"Entity {index} must be a JSON object."
            )

        if "PartitionKey" not in entity:

            raise ValueError(
                f"Entity {index} must contain "
                "'PartitionKey'."
            )

        if "RowKey" not in entity:

            raise ValueError(
                f"Entity {index} must contain "
                "'RowKey'."
            )

        partition_key = str(
            entity["PartitionKey"]
        ).strip()

        row_key = str(
            entity["RowKey"]
        ).strip()

        if not partition_key:

            raise ValueError(
                f"Entity {index} has an empty PartitionKey."
            )

        if not row_key:

            raise ValueError(
                f"Entity {index} has an empty RowKey."
            )

        if partition_key not in entities_by_partition:

            entities_by_partition[
                partition_key
            ] = []

        entities_by_partition[
            partition_key
        ].append(entity)

    # ========================================================
    # CREATE CONNECTION STRING
    # ========================================================

    connection_string = (
        "DefaultEndpointsProtocol=https;"
        f"AccountName={storage_account_name};"
        f"AccountKey={storage_account_key};"
        "EndpointSuffix=core.windows.net"
    )

    # ========================================================
    # CREATE TABLE SERVICE CLIENT
    # ========================================================

    table_service_client = (
        TableServiceClient.from_connection_string(
            conn_str=connection_string
        )
    )

    table_client = (
        table_service_client.get_table_client(
            table_name=table_name
        )
    )

    # ========================================================
    # INFORMATION
    # ========================================================

    total_entities = len(entities)

    total_partitions = len(
        entities_by_partition
    )

    print()
    print("=" * 70)
    print("STARTING BATCH UPLOAD")
    print("=" * 70)

    print(
        f"Table           : {table_name}"
    )

    print(
        f"Total entities  : {total_entities}"
    )

    print(
        f"Batch size      : {batch_size}"
    )

    print(
        f"Partitions      : {total_partitions}"
    )

    print("=" * 70)

    results = []

    batch_number = 0

    uploaded_count = 0

    # ========================================================
    # PROCESS EACH PARTITION
    # ========================================================

    try:

        for partition_key, partition_entities in (
            entities_by_partition.items()
        ):

            print()
            print(
                f"PartitionKey '{partition_key}' "
                f"contains "
                f"{len(partition_entities)} entities."
            )

            # =================================================
            # SPLIT PARTITION INTO BATCHES
            # =================================================

            for start in range(
                0,
                len(partition_entities),
                batch_size
            ):

                batch = partition_entities[
                    start:start + batch_size
                ]

                batch_number += 1

                print()
                print("-" * 70)

                print(
                    f"Uploading Batch {batch_number}"
                )

                print(
                    f"Table        : {table_name}"
                )

                print(
                    f"PartitionKey : {partition_key}"
                )

                print(
                    f"Rows         : {len(batch)}"
                )

                print("-" * 70)

                # =================================================
                # VALIDATE BATCH
                # =================================================

                operations = []

                seen_row_keys = set()

                for entity in batch:

                    entity_copy = dict(entity)

                    entity_copy[
                        "PartitionKey"
                    ] = str(
                        entity_copy[
                            "PartitionKey"
                        ]
                    )

                    entity_copy[
                        "RowKey"
                    ] = str(
                        entity_copy[
                            "RowKey"
                        ]
                    )

                    row_key = entity_copy[
                        "RowKey"
                    ]

                    if row_key in seen_row_keys:

                        raise ValueError(
                            "Duplicate RowKey found in "
                            f"PartitionKey '{partition_key}': "
                            f"{row_key}"
                        )

                    seen_row_keys.add(
                        row_key
                    )

                    operations.append(
                        (
                            "upsert",
                            entity_copy,
                            {
                                "mode": UpdateMode.MERGE
                            }
                        )
                    )

                # =================================================
                # SUBMIT ENTIRE BATCH
                # =================================================

                try:

                    response = (
                        table_client.submit_transaction(
                            operations
                        )
                    )

                    uploaded_count += len(
                        batch
                    )

                    results.append(
                        {
                            "table_name":
                                table_name,

                            "partition_key":
                                partition_key,

                            "batch_number":
                                batch_number,

                            "count":
                                len(batch),

                            "status":
                                "success",

                            "result":
                                response
                        }
                    )

                    print()
                    print(
                        f"Batch {batch_number} "
                        "uploaded successfully."
                    )

                    print(
                        f"Progress: "
                        f"{uploaded_count}/"
                        f"{total_entities}"
                    )

                except Exception as exc:

                    print()
                    print("=" * 70)

                    print(
                        f"BATCH {batch_number} FAILED"
                    )

                    print(
                        f"Table: {table_name}"
                    )

                    print(
                        f"PartitionKey: "
                        f"{partition_key}"
                    )

                    print(
                        f"Rows: {len(batch)}"
                    )

                    print()
                    print(
                        "Entities in failed batch:"
                    )

                    print("-" * 70)

                    for entity_index, entity in enumerate(
                        batch,
                        start=1
                    ):

                        print()
                        print(
                            f"Entity {entity_index}:"
                        )

                        for key, value in (
                            entity.items()
                        ):

                            print(
                                f"  {key} = "
                                f"{repr(value)} "
                                f"(type="
                                f"{type(value).__name__})"
                            )

                    print()
                    print(
                        "Azure Table Error:"
                    )

                    print(
                        str(exc)
                    )

                    print("=" * 70)

                    raise

    finally:

        # ====================================================
        # CLOSE CLIENT
        # ====================================================

        table_service_client.close()

    # ========================================================
    # FINAL RESULT
    # ========================================================

    print()
    print("=" * 70)
    print("BATCH UPLOAD COMPLETED")
    print("=" * 70)

    print(
        f"Table             : {table_name}"
    )

    print(
        f"Total entities    : {total_entities}"
    )

    print(
        f"Uploaded entities : {uploaded_count}"
    )

    print(
        f"Total batches     : {batch_number}"
    )

    print("=" * 70)

    return results


# ============================================================
# TABLE STORAGE SERVICE
# ============================================================

class TableStorageService:
    """
    Wrapper around Azure Table Storage.

    Supports:

        1. Single entity upload
        2. Batch entity upload

    Batch upload:

        - Groups by PartitionKey
        - Maximum 15 entities per batch
        - Uses Azure Table transactional batches
        - Uses UPSERT/MERGE
    """

    def __init__(
        self,
        storage_account_name: str,
        storage_account_key: str
    ):

        self.storage_account_name = (
            storage_account_name
        )

        self.storage_account_key = (
            storage_account_key
        )

    # ========================================================
    # SINGLE ENTITY
    # ========================================================

    def upsert_entity(
        self,
        table_name: str,
        entity: dict
    ):
        """
        Upload exactly one entity.

        This uses Azure CLI.

        For multiple rows, use:

            batch_upsert_entities()
        """

        return insert_table_entity(
            storage_account_name=(
                self.storage_account_name
            ),

            storage_account_key=(
                self.storage_account_key
            ),

            table_name=table_name,

            entity=entity
        )

    # ========================================================
    # BATCH ENTITIES
    # ========================================================

    def batch_upsert_entities(
        self,
        table_name: str,
        entities: list[dict],
        batch_size: int = 15
    ):
        """
        Upload multiple entities using Azure Table
        transactional batches.
        """

        return insert_table_entities_batch(
            storage_account_name=(
                self.storage_account_name
            ),

            storage_account_key=(
                self.storage_account_key
            ),

            table_name=table_name,

            entities=entities,

            batch_size=batch_size
        )


# ============================================================
# GET TABLE STORAGE SERVICE
# ============================================================

def get_table_storage_service(
    resource_group_name: str,
    storage_account_name: str
):
    """
    Create TableStorageService using the storage account
    created during the workflow deployment.

    The storage account key is retrieved using Azure CLI.
    """

    # ========================================================
    # VALIDATE RESOURCE GROUP
    # ========================================================

    if not resource_group_name:

        raise ValueError(
            "resource_group_name is required."
        )

    # ========================================================
    # VALIDATE STORAGE ACCOUNT
    # ========================================================

    if not storage_account_name:

        raise ValueError(
            "storage_account_name is required."
        )

    print()
    print(
        f"Storage account: "
        f"{storage_account_name}"
    )

    # ========================================================
    # GET STORAGE ACCOUNT KEY
    # ========================================================

    storage_account_key = (
        get_storage_account_key(
            resource_group_name=(
                resource_group_name
            ),

            storage_account_name=(
                storage_account_name
            )
        )
    )

    if not storage_account_key:

        raise RuntimeError(
            "Unable to retrieve storage account key."
        )

    storage_account_key = (
        str(
            storage_account_key
        ).strip()
    )

    print(
        "Storage account key retrieved "
        "successfully."
    )

    # ========================================================
    # RETURN SERVICE
    # ========================================================

    return TableStorageService(
        storage_account_name=(
            storage_account_name
        ),

        storage_account_key=(
            storage_account_key
        )
    )
