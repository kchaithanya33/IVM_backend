import logging
import json
from datetime import datetime
import azure.functions as func
from shared_code import ConfigRepository
from shared_code.config_service import CachedConfigService

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Initialize services
config_repo = ConfigRepository()
config_service = CachedConfigService(config_repo)

async def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get all configurations for a partition
    Route:
        GET /api/config/{partition} - Get all configurations in partition
    """
    logging.info('GetPartitionConfigs function processed a request.')

    try:
        # Get partition parameter
        route_params = req.route_params
        partition_key = route_params.get('partition')
        
        if not partition_key:
            return func.HttpResponse(
                "Please provide a partition key in the URL path",
                status_code=400
            )
        
        # Add CORS headers
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Content-Type": "application/json"
        }
        
        # Handle OPTIONS request (CORS preflight)
        if req.method == "OPTIONS":
            return func.HttpResponse(status_code=200, headers=headers)
        
        # Get all configurations in partition
        logging.info(f"Getting all configs for partition: {partition_key}")
        
        try:
            results = await config_service.get_config_by_partition(partition_key)
            logging.info(f"Found {len(results)} configs in partition: {partition_key}")
            
            # Transform results to key-value pairs format
            key_value_results = {item.get("rowKey", ""): item.get("value", "") for item in results}
            
            return func.HttpResponse(
                json.dumps(key_value_results, cls=DateTimeEncoder),
                status_code=200,
                headers=headers
            )
        except Exception as e:
            logging.error(f"Error retrieving configs for partition: {str(e)}")
            return func.HttpResponse(
                json.dumps({"error": f"Error retrieving configurations for partition: {str(e)}"}),
                status_code=500,
                headers=headers
            )
            
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )