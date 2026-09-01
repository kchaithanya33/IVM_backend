import os
import logging
from typing import Dict, List, Optional, Any, Union
# Using azure.cosmosdb.table instead of azure.data.tables
from azure.cosmosdb.table import TableService
from azure.common import AzureMissingResourceHttpError
from azure.identity import DefaultAzureCredential

class ConfigRepository:
    """Repository for accessing configuration data in Azure Table Storage"""
    
    def __init__(self):
        """Initialize the repository with Azure Table Storage connection"""
        self.storage_account_name = os.environ.get("STORAGE_ACCOUNT_NAME")
        self.table_name = os.environ.get("TABLE_NAME", "AppConfiguration")
        self.storage_account_key = os.environ.get("STORAGE_ACCOUNT_KEY", "")
        
        # Log environment variable availability for debugging
        logging.info(f"STORAGE_ACCOUNT_NAME: {'Available' if self.storage_account_name else 'Not available'}")
        logging.info(f"TABLE_NAME: {self.table_name}")
        logging.info(f"STORAGE_ACCOUNT_KEY: {'Available' if self.storage_account_key else 'Not available'}")
        
        # If account name or key missing, try to extract from connection string
        connection_string = os.environ.get("AzureWebJobsStorage", "")
        if (not self.storage_account_name or not self.storage_account_key) and connection_string:
            logging.info("Attempting to extract account info from AzureWebJobsStorage")
            try:
                # Parse connection string
                parts = connection_string.split(';')
                for part in parts:
                    if part.startswith("AccountName="):
                        self.storage_account_name = part[12:]
                    elif part.startswith("AccountKey="):
                        self.storage_account_key = part[11:]
                
                logging.info(f"Extracted account name: {self.storage_account_name is not None}")
                logging.info(f"Extracted account key: {self.storage_account_key is not None}")
            except Exception as e:
                logging.error(f"Error parsing connection string: {str(e)}")
        
        # Using TableService instead of TableServiceClient
        if self.storage_account_name and self.storage_account_key:
            # Using account key if available
            logging.info(f"Creating TableService with account name and key")
            self.table_service = TableService(
                account_name=self.storage_account_name,
                account_key=self.storage_account_key
            )
        elif connection_string:
            # Fallback to connection string directly
            logging.info(f"Creating TableService with connection string")
            self.table_service = TableService(connection_string=connection_string)
        else:
            error_msg = "No valid authentication method for Azure Storage found"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        # Ensure table exists
        self.table_service.create_table(self.table_name, fail_on_exist=False)
        
        logging.info(f"ConfigRepository initialized for table \'{self.table_name}\'")
    
    async def get_config(self, partition_key: str, row_key: str) -> Optional[Dict[str, Any]]:
        """Get a specific configuration entry by partition key and row key"""
        try:
            logging.info(f"Getting config: {partition_key}/{row_key}")
            
            # Handle special characters in keys
            entity = self.table_service.get_entity(
                table_name=self.table_name,
                partition_key=partition_key,
                row_key=row_key
            )
            
            logging.info(f"Config found: {partition_key}/{row_key}")
            return self._format_entity(entity)
        except AzureMissingResourceHttpError:
            logging.info(f"Config not found: {partition_key}/{row_key}")
            return None
        except Exception as e:
            logging.error(f"Error retrieving config {partition_key}/{row_key}: {str(e)}")
            
            # Try an alternative approach by querying and filtering manually
            try:
                logging.info(f"Trying alternative approach with query filtering")
                escaped_partition_key = partition_key.replace("'", "''")
                filter_query = f"PartitionKey eq '{escaped_partition_key}'"
                
                entities = list(self.table_service.query_entities(
                    table_name=self.table_name,
                    filter=filter_query
                ))
                
                # Filter the results to find our exact row key
                for entity in entities:
                    if entity.get("RowKey") == row_key:
                        logging.info(f"Config found using alternative approach: {partition_key}/{row_key}")
                        return self._format_entity(entity)
                
                logging.info(f"Config not found using alternative approach: {partition_key}/{row_key}")
                return None
            except Exception as inner_e:
                logging.error(f"Alternative approach failed: {str(inner_e)}")
                raise e

    async def get_config_by_partition(self, partition_key: str) -> List[Dict[str, Any]]:
        """Get all configuration entries for a specific partition key"""
        try:
            # Handle partition keys with special characters
            logging.info(f"Getting configs for partition: {partition_key}")
            
            # In Azure Table, filters with single quotes need proper escaping
            # Replace single quotes with two single quotes for Azure Table API
            escaped_partition_key = partition_key.replace("'", "''")
            
            filter_query = f"PartitionKey eq '{escaped_partition_key}'"
            logging.info(f"Using filter query: {filter_query}")
            
            entities = list(self.table_service.query_entities(
                table_name=self.table_name,
                filter=filter_query
            ))
            
            logging.info(f"Found {len(entities)} entities for partition {partition_key}")
            return [self._format_entity(entity) for entity in entities]
        except Exception as e:
            logging.error(f"Error retrieving configs for partition {partition_key}: {str(e)}")
            raise
            
    async def get_config_by_pattern(self, partition_key: str, row_key_pattern: str) -> List[Dict[str, Any]]:
        """Get configuration entries matching a row key pattern"""
        try:
            # Using startswith for pattern matching
            # Note: Azure Tables does not support LIKE operators, so we need to filter in code
            logging.info(f"Getting configs with pattern: {partition_key}/{row_key_pattern}*")
            
            # Handle partition keys with special characters
            escaped_partition_key = partition_key.replace("'", "''")
            filter_query = f"PartitionKey eq '{escaped_partition_key}'"
            logging.info(f"Using filter query: {filter_query}")
            
            entities = list(self.table_service.query_entities(
                table_name=self.table_name,
                filter=filter_query
            ))
            
            logging.info(f"Found {len(entities)} total entities for partition {partition_key}")
            
            # Filter in code for pattern matching
            clean_pattern = row_key_pattern.replace("*", "")
            logging.info(f"Using pattern: '{clean_pattern}' for filtering")
            
            matched_entities = [
                entity for entity in entities 
                if entity.get("RowKey", "").startswith(clean_pattern)
            ]
            
            logging.info(f"Found {len(matched_entities)} entities matching pattern {row_key_pattern}*")
            return [self._format_entity(entity) for entity in matched_entities]
        except Exception as e:
            logging.error(f"Error retrieving configurations with pattern {partition_key}:{row_key_pattern}: {str(e)}")
            raise

    async def set_config(self, partition_key: str, row_key: str, data: Dict[str, Any]) -> None:
        """Create or update a configuration entry"""
        try:
            entity = {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                **data
            }
            self.table_service.insert_or_replace_entity(
                table_name=self.table_name,
                entity=entity
            )
            logging.info(f"Config set: {partition_key}/{row_key}")
        except Exception as e:
            logging.error(f"Error setting config {partition_key}/{row_key}: {str(e)}")
            raise

    async def delete_config(self, partition_key: str, row_key: str) -> None:
        """Delete a configuration entry"""
        try:
            self.table_service.delete_entity(
                table_name=self.table_name,
                partition_key=partition_key,
                row_key=row_key
            )
            logging.info(f"Config deleted: {partition_key}/{row_key}")
        except AzureMissingResourceHttpError:
            logging.warning(f"Config not found for deletion: {partition_key}/{row_key}")
        except Exception as e:
            logging.error(f"Error deleting config {partition_key}/{row_key}: {str(e)}")
            raise
            
    def _format_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Format table entity for API response"""
        result = {}
        
        # Process each field individually to ensure JSON serializability
        for key, value in entity.items():
            if key in ["PartitionKey", "RowKey"]:
                # Preserve original partition and row keys but use camelCase in response
                new_key = key[0].lower() + key[1:]
                result[new_key] = value
            elif key == "Timestamp" and hasattr(value, "isoformat"):
                # Convert datetime to ISO format string
                result["timestamp"] = value.isoformat()
            elif isinstance(value, bytes):
                # Convert binary data to base64 string
                import base64
                result[key.lower()] = base64.b64encode(value).decode('utf-8')
            elif hasattr(value, "__dict__"):
                # Convert custom objects to dict
                result[key.lower()] = str(value)
            else:
                # Keep other values as is
                result[key.lower()] = value
        
        # Ensure standard fields exist even if not in entity
        if "value" not in result:
            result["value"] = ""
        if "description" not in result:
            result["description"] = ""
        if "lastModifiedBy" not in result:
            result["lastModifiedBy"] = ""
            
        return result