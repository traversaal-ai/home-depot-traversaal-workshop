from mcp.server.fastmcp import FastMCP
from google.cloud import bigquery
import os
from workflow.utils.config import PROJECT_ID,DATASET_ID

bq_client = bigquery.Client(project=PROJECT_ID)

import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich import box
import json

console = Console()

def query_data(sql: str) -> str:
    try:
        query_job = bq_client.query(sql)
        results = query_job.result()
        rows = [dict(row) for row in results]

        if not rows:
          
            return "No results found"

        # Format and display results in human-readable style
        for i, row in enumerate(rows):
            info = ""
            for key, value in row.items():
                info += f"[bold]{key.replace('_', ' ').title()}[/bold]: {value}\n"

            console.print(Panel(info.strip(), title=f"📝 Record Already Exist, Order Has been Processed before", style="green", box=box.ROUNDED))

        return json.dumps(rows[0] if len(rows) == 1 else rows, default=str)

    except Exception as e:
        console.print(Panel(f" Error: {str(e)}", style="bold red", expand=False))
        return f"Error: {str(e)}"

    
def check_order_action(order_id:str)->str:
    query=f"""SELECT * FROM  `{PROJECT_ID}.{DATASET_ID}.action_update`
    WHERE DATA_ID={order_id}"""
    
    return query_data(query)


    