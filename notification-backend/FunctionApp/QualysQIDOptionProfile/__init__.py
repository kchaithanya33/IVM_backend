import azure.functions as func
import logging
import json
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from datetime import datetime
import os
import base64
import threading


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    FIRE AND FORGET: Returns 202 immediately, processes in background, invokes Logic App when ready
    
    Expected JSON payload:
    {
        "qids": ["38601", "378819", ...],
        "title_prefix": "Custom Profile",
        "global": true,
        "callback_url": "https://prod-51.northeurope.logic.azure.com:443/workflows/.../invoke?...",
        "callback_payload": {
            "assetGroup": ["10.0.0.1", "10.0.0.2"],
            "scannerName": "azeunqlsp001",
            "scanTitle": "Scan Title",
            "priority": "2",
            "cycleId": "2025-10-CYCLE",
            "taskId": "task_12345",
            "valueStream": "VS-Finance",
            "severity": "Critical"
        }
    }
    
    Returns 202 immediately, then creates profile and calls Logic App
    """
    
    logging.info('Processing QID option profile - FIRE AND FORGET MODE')
    
    try:
        req_body = req.get_json()
        
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        qids = req_body.get('qids', [])
        if not qids or not isinstance(qids, list):
            return func.HttpResponse(
                json.dumps({"error": "QIDs array is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        title_prefix = req_body.get('title_prefix', 'Auto Generated')
        global_flag = req_body.get('global', True)
        callback_url = req_body.get('callback_url')
        callback_payload = req_body.get('callback_payload', {})
        
        # Validate callback URL
        if not callback_url or not callback_url.startswith('http'):
            return func.HttpResponse(
                json.dumps({"error": "Valid callback_url is required for Logic App invocation"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Get Qualys config
        qualys_base_url = os.environ.get('QUALYS_API_URL', 'https://qualysapi.qualys.eu')
        qualys_username = os.environ.get('QUALYS_USERNAME')
        qualys_password = os.environ.get('QUALYS_PASSWORD')
        
        if not qualys_username or not qualys_password:
            return func.HttpResponse(
                json.dumps({"error": "Qualys credentials not configured"}),
                status_code=500,
                mimetype="application/json"
            )
        
        credentials = f"{qualys_username}:{qualys_password}"
        qualys_auth = base64.b64encode(credentials.encode()).decode()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        request_id = f"qid_{timestamp}_{os.urandom(4).hex()}"
        
        # Pre-generate titles
        search_list_title = f"{title_prefix} SL {timestamp}"
        option_profile_title = f"{title_prefix} OP {timestamp}"
        
        logging.info(f'==================== REQUEST RECEIVED ====================')
        logging.info(f'Request ID: {request_id}')
        logging.info(f'QIDs Count: {len(qids)}')
        logging.info(f'Callback URL: {callback_url}')
        logging.info(f'Task ID: {callback_payload.get("taskId", "N/A")}')
        logging.info(f'Value Stream: {callback_payload.get("valueStream", "N/A")}')
        logging.info(f'Severity: {callback_payload.get("severity", "N/A")}')
        logging.info(f'Mode: FIRE AND FORGET (returning 202, processing in background)')
        logging.info(f'==========================================================')
        
        # Start background thread - NO WAITING
        thread = threading.Thread(
            target=process_and_trigger_logic_app,
            args=(qualys_base_url, qualys_auth, qids, 
                  search_list_title, option_profile_title, global_flag,
                  callback_url, callback_payload, request_id),
            daemon=True
        )
        thread.start()
        
        # Return IMMEDIATELY - don't wait for anything
        response = {
            "success": True,
            "status": "accepted",
            "request_id": request_id,
            "message": "Request accepted. Processing in background. Logic App will be triggered when ready.",
            "expected_option_profile_title": option_profile_title,
            "expected_search_list_title": search_list_title,
            "qids_count": len(qids),
            "task_id": callback_payload.get('taskId'),
            "value_stream": callback_payload.get('valueStream'),
            "severity": callback_payload.get('severity'),
            "estimated_time": "2-5 minutes depending on QID count"
        }
        
        logging.info(f'[{request_id}] Returning 202 Accepted. Background thread started.')
        
        return func.HttpResponse(
            json.dumps(response),
            status_code=202,  # Accepted
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f'Error: {str(e)}', exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": f"Error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


def process_and_trigger_logic_app(base_url: str, auth_header: str, qids: List[str],
                                   search_list_title: str, option_profile_title: str, 
                                   global_flag: bool, callback_url: str, 
                                   callback_payload: dict, request_id: str):
    """
    Background thread function - creates profile then triggers Logic App
    Takes as long as needed, no rush, no timeouts to worry about
    """
    try:
        import time
        start_time = time.time()
        
        logging.info(f'==================== BACKGROUND PROCESSING STARTED ====================')
        logging.info(f'[{request_id}] Request ID: {request_id}')
        logging.info(f'[{request_id}] QIDs Count: {len(qids)}')
        logging.info(f'[{request_id}] Search List Title: {search_list_title}')
        logging.info(f'[{request_id}] Option Profile Title: {option_profile_title}')
        logging.info(f'[{request_id}] Callback URL: {callback_url}')
        logging.info(f'[{request_id}] Task ID: {callback_payload.get("taskId", "N/A")}')
        logging.info(f'[{request_id}] Value Stream: {callback_payload.get("valueStream", "N/A")}')
        logging.info(f'[{request_id}] Severity: {callback_payload.get("severity", "N/A")}')
        logging.info(f'[{request_id}] Processing will take as long as needed...')
        logging.info(f'======================================================================')
        
        # Step 1: Create search list
        logging.info(f'[{request_id}] ===== STEP 1: Creating Search List =====')
        logging.info(f'[{request_id}] Calling Qualys API with {len(qids)} QIDs...')
        search_list_result = create_search_list(
            base_url, auth_header, qids, search_list_title, global_flag
        )
        
        if not search_list_result['success']:
            error_msg = search_list_result['error']
            elapsed = time.time() - start_time
            logging.error(f'[{request_id}] ❌ SEARCH LIST CREATION FAILED')
            logging.error(f'[{request_id}] Error: {error_msg}')
            logging.error(f'[{request_id}] Elapsed Time: {elapsed:.2f} seconds')
            logging.error(f'[{request_id}] Sending ERROR to Logic App...')
            
            # Send error to Logic App
            trigger_logic_app_callback(callback_url, {
                "success": False,
                "error": f"Search list creation failed: {error_msg}",
                "request_id": request_id,
                "stage": "search_list"
            })
            logging.error(f'[{request_id}] ERROR sent to Logic App. Process terminated.')
            return
        
        search_list_id = search_list_result['search_list_id']
        search_list_time = time.time() - start_time
        logging.info(f'[{request_id}] ✅ SEARCH LIST CREATED')
        logging.info(f'[{request_id}] Search List ID: {search_list_id}')
        logging.info(f'[{request_id}] Time: {search_list_time:.2f} seconds')
        logging.info(f'[{request_id}] =============================================')
        
        # Step 2: Create option profile
        logging.info(f'[{request_id}] ===== STEP 2: Creating Option Profile =====')
        logging.info(f'[{request_id}] Using Search List ID: {search_list_id}')
        option_profile_result = create_option_profile(
            base_url, auth_header, search_list_id, option_profile_title, global_flag
        )
        
        total_time = time.time() - start_time
        
        if not option_profile_result['success']:
            error_msg = option_profile_result['error']
            logging.error(f'[{request_id}] ❌ OPTION PROFILE CREATION FAILED')
            logging.error(f'[{request_id}] Error: {error_msg}')
            logging.error(f'[{request_id}] Total Time: {total_time:.2f} seconds')
            logging.error(f'[{request_id}] Sending ERROR to Logic App...')
            
            # Send error to Logic App
            trigger_logic_app_callback(callback_url, {
                "success": False,
                "error": f"Option profile creation failed: {error_msg}",
                "request_id": request_id,
                "search_list_id": search_list_id,
                "stage": "option_profile"
            })
            logging.error(f'[{request_id}] ERROR sent to Logic App. Process terminated.')
            return
        
        option_profile_id = option_profile_result['option_profile_id']
        option_profile_time = total_time - search_list_time
        logging.info(f'[{request_id}] ✅ OPTION PROFILE CREATED')
        logging.info(f'[{request_id}] Option Profile ID: {option_profile_id}')
        logging.info(f'[{request_id}] Option Profile Title: {option_profile_title}')
        logging.info(f'[{request_id}] Time: {option_profile_time:.2f} seconds')
        logging.info(f'[{request_id}] Total Time: {total_time:.2f} seconds')
        logging.info(f'[{request_id}] =============================================')
        
        # Step 3: Prepare Logic App payload with the EXACT schema you need
        logging.info(f'[{request_id}] ===== STEP 3: Preparing Logic App Payload =====')
        
        # Build the exact payload structure Logic App expects
        logic_app_payload = {
            "cycleId": callback_payload.get('cycleId', ''),
            "taskId": callback_payload.get('taskId', ''),
            "assetGroup": callback_payload.get('assetGroup', []),
            "scannerName": callback_payload.get('scannerName', ''),
            "scanTitle": callback_payload.get('scanTitle', ''),
            "optionProfile": option_profile_title,  # The newly created profile title
            "priority": str(callback_payload.get('priority', '1')),  # Ensure it's a string
            "valueStream": callback_payload.get('valueStream', ''),
            "severity": callback_payload.get('severity', '')
        }
        
        logging.info(f'[{request_id}] Logic App payload prepared:')
        logging.info(f'[{request_id}]   - cycleId: {logic_app_payload["cycleId"]}')
        logging.info(f'[{request_id}]   - taskId: {logic_app_payload["taskId"]}')
        logging.info(f'[{request_id}]   - scannerName: {logic_app_payload["scannerName"]}')
        logging.info(f'[{request_id}]   - scanTitle: {logic_app_payload["scanTitle"]}')
        logging.info(f'[{request_id}]   - optionProfile: {logic_app_payload["optionProfile"]}')
        logging.info(f'[{request_id}]   - priority: {logic_app_payload["priority"]}')
        logging.info(f'[{request_id}]   - valueStream: {logic_app_payload["valueStream"]}')
        logging.info(f'[{request_id}]   - severity: {logic_app_payload["severity"]}')
        logging.info(f'[{request_id}]   - assetGroup: {len(logic_app_payload["assetGroup"])} IPs')
        logging.info(f'[{request_id}] =============================================')
        
        # Step 4: Trigger Logic App
        logging.info(f'[{request_id}] ===== STEP 4: Triggering Logic App =====')
        logging.info(f'[{request_id}] Calling Logic App...')
        callback_result = trigger_logic_app_callback(callback_url, logic_app_payload)
        
        if callback_result['success']:
            logging.info(f'[{request_id}] ✅✅✅ SUCCESS - LOGIC APP TRIGGERED ✅✅✅')
            logging.info(f'[{request_id}] Logic App Status: {callback_result.get("status_code")}')
            logging.info(f'[{request_id}] Total End-to-End Time: {total_time:.2f} seconds')
            logging.info(f'[{request_id}] Logic App will now handle the scan')
            logging.info(f'==================== PROCESS COMPLETED SUCCESSFULLY ====================')
        else:
            logging.error(f'[{request_id}] ❌ LOGIC APP CALLBACK FAILED')
            logging.error(f'[{request_id}] Error: {callback_result.get("error")}')
            logging.error(f'[{request_id}] Option profile was created but Logic App not triggered')
            logging.error(f'[{request_id}] Manual intervention required:')
            logging.error(f'[{request_id}]   - Option Profile: {option_profile_title}')
            logging.error(f'[{request_id}]   - Option Profile ID: {option_profile_id}')
            logging.error(f'==================== COMPLETED WITH ERROR ====================')
            
    except Exception as e:
        logging.error(f'==================== UNEXPECTED ERROR ====================')
        logging.error(f'[{request_id}] EXCEPTION: {str(e)}', exc_info=True)
        
        # Try to notify Logic App of the error
        try:
            trigger_logic_app_callback(callback_url, {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "request_id": request_id,
                "stage": "processing"
            })
        except:
            pass
        
        logging.error(f'==================== PROCESS TERMINATED ====================')


def trigger_logic_app_callback(callback_url: str, payload: dict) -> dict:
    """Trigger Logic App with the result"""
    try:
        logging.info(f'[CALLBACK] Calling Logic App...')
        logging.info(f'[CALLBACK] URL: {callback_url[:100]}...')
        logging.info(f'[CALLBACK] Payload: {json.dumps(payload, indent=2)[:500]}...')
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            callback_url, 
            json=payload, 
            headers=headers,
            timeout=60
        )
        
        logging.info(f'[CALLBACK] Logic App Status Code: {response.status_code}')
        
        if response.status_code in [200, 202, 204]:
            logging.info(f'[CALLBACK] ✅ Logic App accepted the request')
            return {
                "success": True,
                "status_code": response.status_code,
                "message": "Logic App triggered successfully"
            }
        else:
            logging.error(f'[CALLBACK] ❌ Logic App error: {response.status_code}')
            logging.error(f'[CALLBACK] Response: {response.text[:500]}')
            return {
                "success": False,
                "error": f"Logic App returned status {response.status_code}",
                "response": response.text[:200]
            }
            
    except requests.exceptions.Timeout:
        logging.error(f'[CALLBACK] ❌ Timeout after 60 seconds')
        return {
            "success": False,
            "error": "Logic App callback timeout"
        }
    except Exception as e:
        logging.error(f'[CALLBACK] ❌ Exception: {str(e)}', exc_info=True)
        return {
            "success": False,
            "error": f"Callback error: {str(e)}"
        }


def create_search_list(base_url: str, auth_header: str, qids: List[str], 
                       title: str, global_flag: bool) -> Dict[str, Any]:
    """Create search list - takes as long as needed"""
    try:
        session = requests.Session()
        session.headers.update({
            'X-Requested-With': 'Azure Function',
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        qids_string = ','.join(qids)
        url = f"{base_url}/api/2.0/fo/qid/search_list/static/"
        
        data = {
            'action': 'create',
            'title': title,
            'global': '1' if global_flag else '0',
            'qids': qids_string
        }
        
        logging.info(f'Creating search list with {len(qids)} QIDs...')
        
        # Long timeout - we can wait as long as needed
        response = session.post(url, data=data, timeout=300)
        
        logging.info(f'Search list API response: {response.status_code}')
        
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            
            # Check for errors
            error_element = root.find('.//CODE')
            if error_element is not None:
                error_text = root.find('.//TEXT')
                error_msg = error_text.text if error_text is not None else 'Unknown error'
                logging.error(f'Qualys API error: {error_msg}')
                return {'success': False, 'error': error_msg}
            
            # Look for success
            text_element = root.find('.//TEXT')
            if text_element is not None and 'successfully' in text_element.text.lower():
                id_element = root.find('.//ITEM[KEY="ID"]/VALUE')
                if id_element is not None:
                    search_list_id = id_element.text
                    return {
                        'success': True,
                        'search_list_id': search_list_id
                    }
            
            logging.warning(f'Unexpected XML response: {response.text[:300]}')
            return {'success': False, 'error': 'Unexpected response format'}
        elif response.status_code == 409:
            return {'success': False, 'error': 'Conflict - duplicate title'}
        else:
            logging.error(f'HTTP {response.status_code}: {response.text[:200]}')
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.Timeout:
        logging.error('Request timeout after 300 seconds')
        return {'success': False, 'error': 'Timeout'}
    except Exception as e:
        logging.error(f'Exception: {str(e)}', exc_info=True)
        return {'success': False, 'error': str(e)}
    finally:
        try:
            session.close()
        except:
            pass


def create_option_profile(base_url: str, auth_header: str, search_list_id: str, 
                          title: str, global_flag: bool) -> Dict[str, Any]:
    """Create option profile"""
    try:
        session = requests.Session()
        session.headers.update({
            'X-Requested-With': 'Azure Function',
            'Authorization': f'Basic {auth_header}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
        
        url = f"{base_url}/api/2.0/fo/subscription/option_profile/vm/"
        
        data = {
            'action': 'create',
            'title': title,
            'global': '1' if global_flag else '0',
            'scan_tcp_ports': 'standard',
            'scan_udp_ports': 'standard',
            'scan_overall_performance': 'normal',
            'vulnerability_detection': 'custom',
            'basic_information_gathering': 'none',
            'custom_search_list_ids': search_list_id
        }
        
        logging.info(f'Creating option profile with search list: {search_list_id}')
        
        response = session.post(url, data=data, timeout=120)
        
        logging.info(f'Option profile API response: {response.status_code}')
        
        if response.status_code == 200:
            root = ET.fromstring(response.text)
            
            # Check for errors
            error_element = root.find('.//CODE')
            if error_element is not None:
                error_text = root.find('.//TEXT')
                error_msg = error_text.text if error_text is not None else 'Unknown error'
                logging.error(f'Qualys API error: {error_msg}')
                return {'success': False, 'error': error_msg}
            
            # Look for success
            text_element = root.find('.//TEXT')
            if text_element is not None and 'successfully' in text_element.text.lower():
                id_element = root.find('.//ITEM[KEY="ID"]/VALUE')
                if id_element is not None:
                    option_profile_id = id_element.text
                    logging.info(f'Option profile created: {option_profile_id}')
                    return {
                        'success': True,
                        'option_profile_id': option_profile_id
                    }
            
            logging.warning(f'Unexpected XML response: {response.text[:300]}')
            return {'success': False, 'error': 'Unexpected response format'}
        elif response.status_code == 409:
            return {'success': False, 'error': 'Conflict - duplicate title'}
        else:
            logging.error(f'HTTP {response.status_code}: {response.text[:200]}')
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        logging.error(f'Exception: {str(e)}', exc_info=True)
        return {'success': False, 'error': str(e)}
    finally:
        try:
            session.close()
        except:
            pass