"""
Mock ServiceNow Task API Function

This module provides a mock implementation of the MuleSoft ServiceNow Task API.
It's designed to mimic the behavior of the real API for development and testing purposes.

The module handles creating generic tasks, retrieving them, and viewing task information.

Author: GitHub Copilot
Date: June 2025
"""

import logging
import json
import os
import uuid
import re
from datetime import datetime
import azure.functions as func
from azure.data.tables import TableServiceClient, TableClient, UpdateMode
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

# Configuration
MOCK_API_KEY = os.environ.get("MULESOFT_API_KEY", "mock-mulesoft-api-key")
MOCK_SERVICENOW_URL = "https://mockdev.service-now.com"

# Azure Table Storage configuration
CONNECTION_STRING = os.environ.get("AzureWebJobsStorage")
TABLE_NAME = "mocktasks"

# In-memory cache
tasks = {}

# Define task fields
TASK_FIELDS = ["sys_id", "number", "short_description", "description", "state", 
               "priority", "category", "due_date", "created_by", "created_on",
               "assigned_to", "assignment_group", "u_business_service", "task_type"]

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Mock implementation of the MuleSoft ServiceNow Task API.
    
    This function handles:
    - Creating new tasks (POST to /task)
    - Getting task details (GET from /task/records/{sys_id})
    - Getting task ticket URLs (GET from /task/ticket-url/{sys_id})
    - Viewing task details as HTML (GET from /task/view/{sys_id})
    
    It validates API keys and returns responses in the same format as the real API.
    """
    logging.info('Processing mock MuleSoft ServiceNow Task API request')
    
    # Check API Key
    api_key = req.headers.get('x-api-key')
    if req.method == "POST" and (not api_key or api_key != MOCK_API_KEY):
        return func.HttpResponse(
            json.dumps({"error": "Unauthorized: Invalid or missing API key"}),
            status_code=401,
            mimetype="application/json"
        )
    
    try:
        # Ensure the table exists and load tasks from table storage
        ensure_table_exists()
        load_tasks_from_table()
        
        # Parse the route from the request
        route = req.route_params.get('route', '')
        logging.info(f"Processing route: {route}")
        
        # Check if this is a request for a ticket URL
        if req.method == "GET" and route.startswith('ticket-url/'):
            sys_id = route.split('/', 1)[1] if '/' in route else None
            if not sys_id:
                return func.HttpResponse(
                    json.dumps({"error": "Task sys_id not provided in URL"}),
                    status_code=400,
                    mimetype="application/json"
                )
            return get_task_ticket_url(sys_id)
        
        # Check if this is a request for task details by sys_id
        elif req.method == "GET" and route.startswith('records/'):
            sys_id = route.split('/', 1)[1] if '/' in route else None
            if sys_id:
                return get_task_by_sys_id(sys_id)
            else:
                return func.HttpResponse(
                    json.dumps({"error": "Task sys_id not provided in URL"}),
                    status_code=400,
                    mimetype="application/json"
                )
                
        # Check if this is a request to view task as HTML
        elif req.method == "GET" and route.startswith('view/'):
            sys_id = route.split('/', 1)[1] if '/' in route else None
            if sys_id:
                return view_task_html(sys_id)
            else:
                return func.HttpResponse(
                    "Task sys_id not provided in URL",
                    status_code=400,
                    mimetype="text/html"
                )
        
        # Handle POST requests for creating tasks
        elif req.method == "POST" and (not route or route == "" or route == "records"):
            return create_task(req)
            
        # No matching route
        else:
            return func.HttpResponse(
                json.dumps({"error": "Method or route not supported"}),
                status_code=405,
                mimetype="application/json"
            )
            
    except Exception as e:
        logging.error(f"Error processing request: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def create_task(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create a new task based on the request body
    """
    logging.info("Creating mock task")
    
    try:
        # Parse request body
        req_body = req.get_json()
        
        # Generate a unique ID for this task
        sys_id = str(uuid.uuid4())
        
        # Generate a task number with TASK prefix
        current_time = datetime.now()
        task_number = f"TASK{current_time.strftime('%Y%m%d%H%M%S')}"
        
        # Extract fields from request or use defaults
        short_description = req_body.get('short_description', 'New Task')
        description = req_body.get('description', 'This is a generic task')
        state = req_body.get('state', 'Open')
        priority = req_body.get('priority', '3')
        category = req_body.get('category', 'Request')
        
        # Calculate dates
        created_on = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Create task object
        task = {
            "sys_id": sys_id,
            "number": task_number,
            "short_description": short_description,
            "description": description,
            "state": state,
            "priority": priority,
            "category": category,
            "due_date": req_body.get('due_date', ''),
            "created_by": req_body.get('created_by', 'system'),
            "created_on": created_on,
            "assigned_to": req_body.get('assigned_to', ''),
            "assignment_group": req_body.get('assignment_group', 'Service Desk'),
            "u_business_service": req_body.get('u_business_service', ''),
            "task_type": req_body.get('task_type', 'task')
        }
        
        # Store the task in memory
        tasks[sys_id] = task
        
        # Save to Azure Table Storage
        save_task_to_table(task)
        
        # Return response
        return func.HttpResponse(
            json.dumps({
                "sys_id": task["sys_id"],
                "number": task["number"]
            }),
            status_code=201,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error creating task: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to create task: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def get_task_ticket_url(sys_id: str) -> func.HttpResponse:
    """
    Get the ticket URL for a task based on its sys_id
    """
    try:
        # Generate a mock URL that points to the HTML view endpoint
        mock_url = f"/api/servicenow/task/view/{sys_id}"
        
        # Format the response like the real API
        response = {
            "ticket_url": mock_url,
            "sys_id": sys_id
        }
        
        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error getting task ticket URL: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to get task ticket URL: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def get_task_by_sys_id(sys_id: str) -> func.HttpResponse:
    """
    Get task details based on its sys_id
    """
    logging.info(f"Getting task with sys_id: {sys_id}")
    
    try:
        # Check if task exists in memory, otherwise try to get from storage
        task = tasks.get(sys_id)
        
        if not task:
            # Try to get the task from table storage directly
            task = get_task_from_table(sys_id)
        
        if not task:
            return func.HttpResponse(
                json.dumps({"error": "Task not found"}),
                status_code=404,
                mimetype="application/json"
            )
        
        # Return the task details
        return func.HttpResponse(
            json.dumps(task),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.error(f"Error getting task: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to get task: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

def view_task_html(sys_id: str) -> func.HttpResponse:
    """
    Generate HTML view of task details
    """
    logging.info(f"Viewing task with sys_id: {sys_id}")
    
    try:
        # Get task details
        task = tasks.get(sys_id)
        
        if not task:
            # Try to get from table storage
            task = get_task_from_table(sys_id)
        
        if not task:
            return func.HttpResponse(
                "<html><body><h1>Task Not Found</h1><p>The requested task does not exist.</p></body></html>",
                status_code=404,
                mimetype="text/html"
            )
        
        # Generate HTML representation
        html = f"""
        <html>
        <head>
            <title>Task {task['number']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #0057a6; color: white; padding: 10px; border-radius: 5px; }}
                .task-details {{ border: 1px solid #ddd; padding: 15px; margin-top: 20px; }}
                .field {{ margin-bottom: 10px; }}
                .field-name {{ font-weight: bold; }}
                .description {{ white-space: pre-wrap; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Task {task['number']}</h1>
            </div>
            
            <div class="task-details">
                <div class="field">
                    <span class="field-name">Short Description:</span>
                    <span>{task['short_description']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">State:</span>
                    <span>{task['state']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">Priority:</span>
                    <span>{task['priority']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">Category:</span>
                    <span>{task['category']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">Created By:</span>
                    <span>{task['created_by']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">Created On:</span>
                    <span>{task['created_on']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">Assigned To:</span>
                    <span>{task['assigned_to']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">Assignment Group:</span>
                    <span>{task['assignment_group']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">Business Service:</span>
                    <span>{task['u_business_service']}</span>
                </div>
                
                <div class="field">
                    <span class="field-name">Due Date:</span>
                    <span>{task['due_date']}</span>
                </div>
                
                <div class="description">
                    <div class="field-name">Description:</div>
                    <div>{task['description']}</div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return func.HttpResponse(
            html,
            status_code=200,
            mimetype="text/html"
        )
    except Exception as e:
        logging.error(f"Error viewing task HTML: {str(e)}")
        return func.HttpResponse(
            f"<html><body><h1>Error</h1><p>Failed to generate task view: {str(e)}</p></body></html>",
            status_code=500,
            mimetype="text/html"
        )

# Azure Table Storage Functions

def ensure_table_exists():
    """
    Ensure that the Azure Table Storage table exists
    """
    try:
        # Create the table client
        table_service_client = TableServiceClient.from_connection_string(CONNECTION_STRING)
        
        # Create the table if it doesn't exist
        try:
            table_service_client.create_table(TABLE_NAME)
            logging.info(f"Created table {TABLE_NAME}")
        except ResourceExistsError:
            logging.info(f"Table {TABLE_NAME} already exists")
    except Exception as e:
        logging.error(f"Error ensuring table exists: {str(e)}")
        # Continue even if table creation fails, we'll use in-memory storage

def load_tasks_from_table():
    """
    Load all tasks from Azure Table Storage into memory
    """
    try:
        # Create the table client
        table_client = TableClient.from_connection_string(CONNECTION_STRING, TABLE_NAME)
        
        # Query all entities
        entities = table_client.query_entities("")
        
        # Store in memory
        for entity in entities:
            sys_id = entity.get('RowKey')
            if sys_id:
                task = {
                    "sys_id": sys_id,
                    "number": entity.get('number', ''),
                    "short_description": entity.get('short_description', ''),
                    "description": entity.get('description', ''),
                    "state": entity.get('state', ''),
                    "priority": entity.get('priority', ''),
                    "category": entity.get('category', ''),
                    "due_date": entity.get('due_date', ''),
                    "created_by": entity.get('created_by', ''),
                    "created_on": entity.get('created_on', ''),
                    "assigned_to": entity.get('assigned_to', ''),
                    "assignment_group": entity.get('assignment_group', ''),
                    "u_business_service": entity.get('u_business_service', ''),
                    "task_type": entity.get('task_type', '')
                }
                tasks[sys_id] = task
        
        logging.info(f"Loaded {len(tasks)} tasks from table storage")
    except Exception as e:
        logging.error(f"Error loading tasks from table: {str(e)}")
        # Continue with empty in-memory storage

def save_task_to_table(task):
    """
    Save a task to Azure Table Storage
    """
    try:
        # Create the table client
        table_client = TableClient.from_connection_string(CONNECTION_STRING, TABLE_NAME)
        
        # Create entity
        entity = {
            "PartitionKey": "task",
            "RowKey": task["sys_id"],
            "number": task["number"],
            "short_description": task["short_description"],
            "description": task["description"],
            "state": task["state"],
            "priority": task["priority"],
            "category": task["category"],
            "due_date": task["due_date"],
            "created_by": task["created_by"],
            "created_on": task["created_on"],
            "assigned_to": task["assigned_to"],
            "assignment_group": task["assignment_group"],
            "u_business_service": task["u_business_service"],
            "task_type": task["task_type"]
        }
        
        # Save to table
        table_client.create_entity(entity)
        logging.info(f"Saved task {task['number']} to table storage")
    except Exception as e:
        logging.error(f"Error saving task to table: {str(e)}")
        # Continue even if saving fails, we still have in-memory copy

def get_task_from_table(sys_id):
    """
    Get a task directly from Azure Table Storage by sys_id
    """
    try:
        # Create the table client
        table_client = TableClient.from_connection_string(CONNECTION_STRING, TABLE_NAME)
        
        # Get the entity
        entity = table_client.get_entity("task", sys_id)
        
        # Convert to task object
        task = {
            "sys_id": sys_id,
            "number": entity.get('number', ''),
            "short_description": entity.get('short_description', ''),
            "description": entity.get('description', ''),
            "state": entity.get('state', ''),
            "priority": entity.get('priority', ''),
            "category": entity.get('category', ''),
            "due_date": entity.get('due_date', ''),
            "created_by": entity.get('created_by', ''),
            "created_on": entity.get('created_on', ''),
            "assigned_to": entity.get('assigned_to', ''),
            "assignment_group": entity.get('assignment_group', ''),
            "u_business_service": entity.get('u_business_service', ''),
            "task_type": entity.get('task_type', '')
        }
        
        return task
    except ResourceNotFoundError:
        logging.warning(f"Task with sys_id {sys_id} not found in table storage")
        return None
    except Exception as e:
        logging.error(f"Error getting task from table: {str(e)}")
        return None