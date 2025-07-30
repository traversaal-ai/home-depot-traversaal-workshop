
import os, sys

# Add architecture/ (parent of 'workflow') to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))



import logging
import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)

for logger_name in ['__main__', 'server', 'google', 'vertexai', 'httpx', 'httpcore', 'mcp', 'bigquery']:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)
    logger.disabled = True
    logger.propagate = False

logging.disable(logging.CRITICAL)

# Set environment variables to suppress other logs
os.environ['PYTHONWARNINGS'] = 'ignore'
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '3'


from mcp.server.fastmcp import FastMCP
from loguru import logger
from typing import Any, Dict, List
from google.cloud import bigquery
import requests


from workflow.tools.order_information_tool import (
    query_data_tool,
    fetch_customer_info,
    fetch_delivery_info,
    delivery_item_info,
    fetch_customer_history,
    
)
from workflow.tools.action_update_tool import action_update_database
from workflow.tools.weather_tool import get_weather_forecast
from workflow.tools.streetview_tool import street_view_

from workflow.tools.query_action_tool import query_action_tool

from workflow.mcp.mcp_server import mcp



if __name__ == "__main__":
    print("Starting BigQuery Delivery MCP server...")
    logger.info("BigQuery Delivery MCP server ready for queries...")
    mcp.run(transport="stdio")

    

    


