import asyncio
from google.genai import types
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters, StdioConnectionParams
import os
import warnings
from google.adk.tools.function_tool import FunctionTool
import uuid
from google.adk.tools import FunctionTool
import logging
from datetime import datetime
from typing import Optional
from vertexai import rag
from vertexai.generative_models import GenerativeModel, Tool
import vertexai
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from google.cloud import bigquery
import pandas as pd
from mem0 import MemoryClient
from create import PROJECT_ID, LOCATION_ID, DATASET_ID, ACTION_TABLE_ID, ANCHOR_TABLE_ID, CUSTOMER_TABLE_ID, ORDER_TABLE_ID, ITEM_TABLE_ID

# # Setup BigQuery credentials
# PROJECT_ID = "traversaal-research"
# LOCATION_ID = "us-central1"
# DATASET_ID = "home_depot_policy"
# ACTION_TABLE_ID = "action_tab"
# ORDER_TABLE_ID = "order_tab"
# ANCHOR_TABLE_ID = "anchor_tab"
# CUSTOMER_TABLE_ID = "customer_tab"

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION_ID

order_tables_detail = f"""Order table name: `{PROJECT_ID}.{DATASET_ID}.{ORDER_TABLE_ID}`
Order table Schema:
customer_id (STRING): Unique identifier for each customer
customer_name (STRING): Full name of the customer
order_number (STRING): Unique order number
order_date (DATE): Date when the order was placed
quantity (INTEGER): Quantity of items ordered
total_sale (FLOAT): Total sales amount for the order
sku_price (FLOAT): Price of the individual item SKU
sku_name (STRING): Name of the product item
sku_id (STRING): Unique SKU identifier for the product
delivery_type (STRING): Delivery method (Store or Home)
status (STRING): Order status (Delivered or Pending)
pickup_person (STRING): Order pickup person name when delivery_type is Store"""

anchor_tables_detail = f"""Anchor table name: `{PROJECT_ID}.{DATASET_ID}.{ANCHOR_TABLE_ID}`
Anchor table Schema:
sku_id (STRING): Unique SKU identifier for the product
sku_name (STRING): Name of the product item
recommended_sku_id (STRING): Unique SKU identifier for recommended item
recommended_sku_name (STRING): Name of the recommended product item
recommended_price (FLOAT): Price of the recommended item"""


def get_customer_context(user_id: str) -> str:
    """
    Retrieve customer data from BigQuery and return formatted context string for agent.
    
    Args:
        user_id (str): The customer ID to look up
        
    Returns:
        str: Formatted context string for agent system instruction
    """
    try:
        # Initialize BigQuery client
        client = bigquery.Client(project=PROJECT_ID)
        
        # SQL query to get customer data
        query = f"""
        SELECT customer_id, name, phone, email, address 
        FROM `{PROJECT_ID}.{DATASET_ID}.{CUSTOMER_TABLE_ID}` 
        WHERE customer_id = @user_id
        LIMIT 1
        """
        
        # Configure query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
            ]
        )
        
        # Execute query
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()
        
        # Process results
        customer_data = None
        for row in results:
            customer_data = {
                "customer_id": row.customer_id,
                "name": row.name,
                "phone": row.phone,
                "email": row.email,
                "address": row.address
            }
            break
        
        # Format context string
        if customer_data:
            context = f"""
- customer_id: {customer_data['customer_id']}
- name: {customer_data['name']}
- phone: {customer_data['phone']}
- email: {customer_data['email']}
- address: {customer_data['address']}

Please personalize your responses using the customer's name ({customer_data['name']}) and consider their contact information when relevant. Provide helpful and courteous service tailored to this specific customer.
"""
        else:
            context = f"""
- customer_id: {user_id}
- status: Customer not found in database

Please provide general assistance as no specific customer information is available.
"""
        
        return context.strip()
        
    except Exception as e:
        print(f"Error retrieving customer data: {e}")
        return f"""
- customer_id: {user_id}
- status: Error retrieving customer information

Please provide general assistance due to technical difficulties accessing customer data.
"""

    
######################################### Multiple Action Tools for Sub Action Agent

def return_damaged_item_tool(user_id: str, order_number: str, query: str) -> str:
    """Processes return or damaged item requests for a customer.

    Args:
        user_id (str): The customer ID number who is requesting the return/damaged item action
        order_number (str): The order number for the item to be returned or reported as damaged
        query (str): The customer's specific request or reason for return/damage report

    Returns:
        str: A message confirming the return/damage process initiation with details
    """
    print(f"--- Tool: return_damaged_item_tool called for Customer: {user_id}, Order: {order_number}, Query: {query}  ---")
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{ACTION_TABLE_ID}"
        
        rows_to_insert = [{
            "customer_id": user_id,
            "order_number": order_number,
            "query": query,
            "action_type": "return_damaged_item"
        }]
        
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if not errors:
            print("Successfully added return/damaged item request to BigQuery")
        else:
            print(f"BigQuery insert errors: {errors}")
            
    except Exception as e:
        print(f"BigQuery error: {e}")
    
    return "Your return/damaged item request has been successfully initiated. You can expect a confirmation email shortly with return instructions and next steps."

def delivery_method_change_tool(user_id: str, order_number: str, query: str) -> str:
    """Processes delivery method changes for a customer's order.

    Args:
        user_id (str): The customer ID number who is requesting the delivery method change
        order_number (str): The order number for which delivery method needs to be changed
        query (str): The customer's specific delivery method change request

    Returns:
        str: A message confirming the delivery method change process initiation
    """
    print(f"--- Tool: delivery_method_change_tool called for Customer: {user_id}, Order: {order_number}, Query: {query}  ---")
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{ACTION_TABLE_ID}"
        
        rows_to_insert = [{
            "customer_id": user_id,
            "order_number": order_number,
            "query": query,
            "action_type": "delivery_method_change"
        }]
        
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if not errors:
            print("Successfully added delivery method change request to BigQuery")
        else:
            print(f"BigQuery insert errors: {errors}")
            
    except Exception as e:
        print(f"BigQuery error: {e}")
    
    return "Your delivery method change request has been successfully submitted. You will receive a confirmation email with updated delivery details within 24 hours."

def pickup_person_change_tool(user_id: str, order_number: str, query: str) -> str:
    """Processes pickup person name changes for a customer's order.

    Args:
        user_id (str): The customer ID number who is requesting the pickup person name change
        order_number (str): The order number for which pickup person needs to be changed
        query (str): The customer's request with new pickup person details

    Returns:
        str: A message confirming the pickup person change process initiation
    """
    print(f"--- Tool: pickup_person_change_tool called for Customer: {user_id}, Order: {order_number}, Query: {query}  ---")
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{ACTION_TABLE_ID}"
        
        rows_to_insert = [{
            "customer_id": user_id,
            "order_number": order_number,
            "query": query,
            "action_type": "pickup_person_change"
        }]
        
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if not errors:
            print("Successfully added pickup person change request to BigQuery")
        else:
            print(f"BigQuery insert errors: {errors}")
            
    except Exception as e:
        print(f"BigQuery error: {e}")
    
    return "Your pickup person change request has been successfully processed. The new authorized pickup person information has been updated for your order."

def apply_coupon_tool(user_id: str, order_number: str, query: str) -> str:
    """Processes coupon application requests for a customer's order.

    Args:
        user_id (str): The customer ID number who is requesting to apply a coupon
        order_number (str): The order number to which the coupon should be applied
        query (str): The customer's coupon application request with coupon details

    Returns:
        str: A message confirming the coupon application process initiation
    """
    print(f"--- Tool: apply_coupon_tool called for Customer: {user_id}, Order: {order_number}, Query: {query}  ---")
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{ACTION_TABLE_ID}"
        
        rows_to_insert = [{
            "customer_id": user_id,
            "order_number": order_number,
            "query": query,
            "action_type": "apply_coupon"
        }]
        
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if not errors:
            print("Successfully added coupon application request to BigQuery")
        else:
            print(f"BigQuery insert errors: {errors}")
            
    except Exception as e:
        print(f"BigQuery error: {e}")
    
    return "Your coupon application request has been successfully submitted. If the coupon is valid and applicable, the discount will be processed and you'll receive an updated order confirmation."

def customer_support_tool(user_id: str, query: str) -> str:
    """Processes customer details change request that don't require an order number.

    Args:
        user_id (str): The customer ID number who is requesting
        query (str): The customer's details change request

    Returns:
        str: A message confirming the support request has been logged
    """
    print(f"--- Tool: customer_support_tool called for Customer: {user_id}, Query: {query}  ---")
    
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{ACTION_TABLE_ID}"
        
        rows_to_insert = [{
            "customer_id": user_id,
            "order_number": "N/A",  # No order number required for general support
            "query": query,
            "action_type": "customer_support"
        }]
        
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if not errors:
            print("Successfully added customer support request to BigQuery")
        else:
            print(f"BigQuery insert errors: {errors}")
            
    except Exception as e:
        print(f"BigQuery error: {e}")
    
    return "Your details change request has been successfully submitted. You will receive a confirmation email with updated details within 24 hours."       

