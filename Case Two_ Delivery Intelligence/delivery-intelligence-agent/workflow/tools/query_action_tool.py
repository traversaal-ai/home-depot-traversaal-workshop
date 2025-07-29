from workflow.mcp.mcp_server import mcp
from loguru import logger
from typing import Any, Dict, List
from google.cloud import bigquery
import os
from workflow.utils.config import PROJECT_ID,DATASET_ID

TABLE_ID="action_update"
FULL_TABLE_NAME = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
bq_client = bigquery.Client(project=PROJECT_ID)

@mcp.tool()
def query_action_tool(sql: str) -> str:
    """
    Execute SELECT or UPDATE SQL queries on the BigQuery action_update table.
    Allows full access to all columns including 'rescheduled' and 'updated_at'.
    """
    logger.info(f"Executing SQL query: {sql}")
    try:
        query_job = bq_client.query(sql)
        results = query_job.result()

        if sql.strip().lower().startswith("select"):
            rows = [dict(row) for row in results]
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
                    result_text += " | ".join(str(v) for v in row.values()) + "\n"
                return result_text.strip()

        elif sql.strip().lower().startswith("update"):
            return "Update successful."

        else:
            return "Only SELECT and UPDATE queries are allowed."

    except Exception as e:
        logger.error(f"BigQuery SQL Error: {str(e)}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_action_table_info() -> str:
    """Get schema information for the walmart sales table."""
    logger.info("Getting BigQuery table schema information")
    try:
        table = bq_client.get_table(FULL_TABLE_NAME)
        
        schema_info = f"Table: {FULL_TABLE_NAME}\n"
        schema_info += f"Total Rows: {table.num_rows:,}\n"
        schema_info += "Columns:\n"
        
        for field in table.schema:
            schema_info += f"  - {field.name}: {field.field_type}\n"
        
        return schema_info
        
    except Exception as e:
        logger.error(f"Table Info Error: {str(e)}")
        return f"Error: {str(e)}"
