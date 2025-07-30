from workflow.mcp.mcp_server import mcp
from loguru import logger

from typing import Any, Dict, List
from google.cloud import bigquery
import os
from workflow.utils.config import PROJECT_ID,DATASET_ID


bq_client = bigquery.Client(project=PROJECT_ID)
   
@mcp.tool()
def action_update_database(order_id: str, customer_id: str, customer_name: str, message: str, summary: str) -> str:
    """
    Professional production-ready database insert using parameterized queries.
    Handles ANY string content safely - no escaping issues ever.
    """
    logger.info(f"Permorming Action: Updating case card in action_table for order_id: {order_id}")
    from datetime import datetime, timedelta
    from google.cloud import bigquery
    
    
    try:
        # Initialize BigQuery client
        client = bigquery.Client()
        
        # Timestamps
        current_time = datetime.now()
        updated_at = current_time.strftime('%Y-%m-%d %H:%M:%S')
        reschedule_at = (current_time + timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Parameterized query - 100% safe, handles any content
        query = f"""
        INSERT INTO `{PROJECT_ID}.{DATASET_ID}.action_update` (
          DATA_ID,
          CUSTOMER_ID,
          CUSTOMER_NAME,
          MESSAGE,
          UPDATED_AT,
          RESCHEDULED,
          SUMMARY
        )
        VALUES (
          @order_id,
          @customer_id,
          @customer_name,
          @message,
          @updated_at,
          @reschedule,
          @summary
        )
        """
        
        # Parameters - BigQuery handles ALL escaping automatically
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("order_id", "INT64", int(order_id)),
                bigquery.ScalarQueryParameter("customer_id", "INT64", int(customer_id)),
                bigquery.ScalarQueryParameter("customer_name", "STRING", str(customer_name or "")),
                bigquery.ScalarQueryParameter("message", "STRING", str(message or "")),
                bigquery.ScalarQueryParameter("updated_at", "STRING", updated_at),
                bigquery.ScalarQueryParameter("reschedule", "STRING", reschedule_at),
                bigquery.ScalarQueryParameter("summary", "STRING", str(summary or "")),
            ]
        )
        
        # Execute
        query_job = client.query(query, job_config=job_config)
        query_job.result()  # Wait for completion
        
        return f"SUCCESS: Record inserted for order {order_id}"
        
    except Exception as e:
        return f"ERROR: {str(e)}"
