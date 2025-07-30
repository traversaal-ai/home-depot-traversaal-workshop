from loguru import logger
from typing import Any, Dict, List
from google.cloud import bigquery
import os
from workflow.utils.config import PROJECT_ID,DATASET_ID
from workflow.mcp.mcp_server import mcp



# Initialize BigQuery client
bq_client = bigquery.Client(project=PROJECT_ID)

def query_data(sql: str) -> str:
    """Helper function to execute SQL queries on BigQuery."""
    try:
        query_job = bq_client.query(sql)
        results = query_job.result()
        
        rows = []
        for row in results:
            rows.append(dict(row))
        
        if not rows:
            return "No results found"
        
        if len(rows) == 1 and len(rows[0]) == 1:
            return str(list(rows[0].values())[0])
        else:
            result_text = ""
            for i, row in enumerate(rows):
                if i == 0:
                    headers = list(row.keys())
                    result_text += " | ".join(headers) + "\n"
                    result_text += "-" * len(" | ".join(headers)) + "\n"
                
                values = [str(v) for v in row.values()]
                result_text += " | ".join(values) + "\n"
            
            return result_text.strip()
            
    except Exception as e:
        logger.error(f"BigQuery SQL Error: {str(e)}")
        return f"Error: {str(e)}"

@mcp.tool()
def query_data_tool(sql: str) -> str:
    """Execute SQL queries on the BigQuery delivery database."""
    return query_data(sql)

@mcp.tool()
def fetch_customer_info(order_id: int) -> str:
    """Fetch customer information including personal details and addresses."""
    logger.info(f"Fetching customer info")
    
    query = f"""
    SELECT 
        c.*
    FROM `{PROJECT_ID}.{DATASET_ID}.deliveries` d
    JOIN `{PROJECT_ID}.{DATASET_ID}.customers` c
    ON d.customer_id = c.customer_id
    WHERE d.DATA_ID = {order_id}
    LIMIT 1
    """

    return query_data(query)


@mcp.tool()
def fetch_delivery_info(order_id: int) -> str:
    """Fetches order information."""
    logger.info(f"Fetching order info for order_id: {order_id}")
    
    query = f"""
    SELECT 
        d.* EXCEPT (DLVRY_RISK_DECILE, DLVRY_RISK_PERCENTILE, DLVRY_RISK_BUCKET, WEATHER_ID, UNATTENDED_FLAG),
        a.*
    FROM `{PROJECT_ID}.{DATASET_ID}.deliveries` d
    JOIN `{PROJECT_ID}.{DATASET_ID}.addresses` a
        ON d.address_id = a.address_id
    WHERE d.DATA_ID = {order_id}
    """

    return query_data(query)



@mcp.tool()
def delivery_item_info(order_id: int) -> str:
    """Fetch delivery items information."""
    logger.info(f"Fetching items for order_id: {order_id}")
    
    query = f"""
    SELECT 
        p.*
    FROM `{PROJECT_ID}.{DATASET_ID}.delivery_products` d
    JOIN `{PROJECT_ID}.{DATASET_ID}.products` p
        ON d.PRODUCT_ID = p.PRODUCT_ID
    WHERE d.DATA_ID = {order_id}
    """

    return query_data(query)

@mcp.tool()
def fetch_customer_history(order_id: int) -> str:
    """Fetch all past orders, deliveries, and delivery attempts for a customer."""
    logger.info(f"Fetching customer history for order_id: {order_id}")
    
    query = f"""
    SELECT d2.*
    FROM (
        SELECT customer_id
        FROM `{PROJECT_ID}.{DATASET_ID}.deliveries`
        WHERE DATA_ID = {order_id}
    ) AS t1
    JOIN `{PROJECT_ID}.{DATASET_ID}.deliveries` d2
        ON t1.customer_id = d2.customer_id
        WHERE DATA_ID !={order_id}

    """



    return query_data(query)




 



