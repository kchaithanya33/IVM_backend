import logging
import azure.functions as func
import json
import math
from datetime import datetime
from typing import List, Dict, Any, Optional

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    AssetGroupBatchProcessor - HTTP Trigger Azure Function
    
    This function processes asset group data from Qualys and creates batches for processing.
    It simplifies the LA-VulnScan-03.json Logic App by handling the batch creation calculations.
    
    Input: JSON body with asset group information
    Output: Batch information for creating Qualys asset groups and queue messages
    """
    logging.info('AssetGroupBatchProcessor function processing a request')
    
    try:
        # Get request body
        req_body = req.get_json()
        
        # Extract required parameters
        assets = req_body.get('assets', [])
        batch_size = req_body.get('batchSize', 200)
        cycle_id = req_body.get('cycleId')
        
        # Validate required parameters
        if not assets:
            return func.HttpResponse(
                json.dumps({"success": False, "error": "Missing required parameter 'assets'"}),
                status_code=400,
                mimetype="application/json"
            )
            
        if not cycle_id:
            return func.HttpResponse(
                json.dumps({"success": False, "error": "Missing required parameter 'cycleId'"}),
                status_code=400,
                mimetype="application/json"
            )
            
        logging.info(f"Processing {len(assets)} assets with batch size {batch_size}")
          # Create batches
        batches = create_batches(assets, batch_size, cycle_id)
        
        # Format groups for Qualys API format
        groups = []
        for batch in batches:
            group = {
                "name": batch["group_name"],
                "ips": batch["ips"]
            }
            groups.append(group)
        
        # Return both the batches (for backward compatibility) and the groups in Qualys format
        return func.HttpResponse(
            json.dumps({
                "success": True, 
                "batches": batches,
                "cycleId": cycle_id,
                "groups": groups
            }),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in AssetGroupBatchProcessor function: {str(e)}")
        return func.HttpResponse(
            json.dumps({"success": False, "error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )


def create_batches(assets: List[Dict[str, Any]], batch_size: int, cycle_id: str) -> List[Dict[str, Any]]:
    """
    Creates batches from a list of assets
    
    Args:
        assets: List of asset dictionaries
        batch_size: Maximum number of assets per batch
        cycle_id: The cycle ID for the scan
        
    Returns:
        List of batch dictionaries with batch_num, assets, and group_name
        Also includes the formatted 'groups' field required by Qualys API
    """
    # Calculate number of batches needed
    num_assets = len(assets)
    num_batches = math.ceil(num_assets / batch_size)
    
    logging.info(f"Creating {num_batches} batches from {num_assets} assets")
    
    batches = []
    for batch_num in range(num_batches):
        # Calculate start and end indices for this batch
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, num_assets)
        
        # Extract assets for this batch
        batch_assets = assets[start_idx:end_idx]
        
        # Create batch name with default format
        timestamp = datetime.now().strftime('%d%m%y%H%M')
        batch_name = f"VulnScan-Diageo-{timestamp}-Batch-{batch_num}"
        
        # Extract IPs for the Qualys API format
        ips = [asset.get('ip') for asset in batch_assets if asset.get('ip')]
          # Create batch object
        batch = {
            "batch_num": batch_num,
            "group_name": batch_name,
            "asset_count": len(batch_assets),
            "operation": "createGroup",
            "ips": ips
        }
        
        batches.append(batch)
        
    return batches