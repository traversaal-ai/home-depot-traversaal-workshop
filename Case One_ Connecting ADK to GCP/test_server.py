from mcp.server.fastmcp import FastMCP
from loguru import logger
from typing import Any, Dict, List
from google.cloud import bigquery
import os

# Setup BigQuery credentials
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "<PROJECT_ID>"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

# BigQuery configuration
PROJECT_ID = "<PROJECT_ID>"
DATASET_ID = "<DATASET_NAME>"
TABLE_ID = "<DATASET_TABLE>"
FULL_TABLE_NAME = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

mcp = FastMCP("walmart-sales-hub")

# Initialize BigQuery client
bq_client = bigquery.Client(project=PROJECT_ID)

@mcp.tool()
def query_data(sql: str) -> str:
    """Execute SQL queries on the BigQuery walmart sales database."""
    logger.info(f"Executing BigQuery SQL query: {sql}")
    try:
        # Execute query
        query_job = bq_client.query(sql)
        results = query_job.result()
        
        # Convert results to list of dictionaries
        rows = []
        for row in results:
            rows.append(dict(row))
        
        if not rows:
            return "No results found"
        
        # Format results nicely
        if len(rows) == 1 and len(rows[0]) == 1:
            # Single value result
            return str(list(rows[0].values())[0])
        else:
            # Multiple rows/columns - format as readable text
            result_text = ""
            for i, row in enumerate(rows):
                if i == 0:
                    # Add headers
                    headers = list(row.keys())
                    result_text += " | ".join(headers) + "\n"
                    result_text += "-" * len(" | ".join(headers)) + "\n"
                
                # Add row data
                values = [str(v) for v in row.values()]
                result_text += " | ".join(values) + "\n"
            
            return result_text.strip()
            
    except Exception as e:
        logger.error(f"BigQuery SQL Error: {str(e)}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_table_info() -> str:
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

@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone"""
    return f"Hello, {name}! Ready to query Walmart sales data in BigQuery."

if __name__ == "__main__":
    print("Starting BigQuery MCP server...")
    logger.info("BigQuery MCP server ready for queries...")
    mcp.run(transport="stdio")
