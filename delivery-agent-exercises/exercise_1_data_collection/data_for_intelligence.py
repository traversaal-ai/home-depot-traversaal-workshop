import os
import warnings
import asyncio
import json
from google.cloud import bigquery
import google.auth
import sys
import logging
from typing import Dict, Any, Optional

# Suppress ALL warnings
warnings.filterwarnings("ignore")
warnings.simplefilter("ignore")
logging.getLogger().setLevel(logging.ERROR)

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "traversaal-research"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

from google.adk.agents import Agent, ParallelAgent, SequentialAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

# Initialize BigQuery client
credentials, project = google.auth.default()
bq_client = bigquery.Client(credentials=credentials, project=project)

# Configuration
DATASET_ID = "delivery_intelligence"
PROJECT_ID = "traversaal-research"

# Generic BigQuery function tool
def execute_query(query: str) -> dict:
    """Execute a BigQuery SQL query and return results"""
    try:
        result = bq_client.query(query).result()
        rows = []
        for row in result:
            rows.append(dict(row))
        return {"status": "success", "data": rows}
    except Exception as e:
        return {"status": "error", "error": str(e)}

GEMINI_MODEL = "gemini-2.0-flash"

# First agent - gets order data for a specific order
order_fetcher_agent = Agent(
    model=GEMINI_MODEL,
    name="order_fetcher_agent",
    description="Fetches order data for a specific order number",
    instruction=f"""\
        You will receive an order number in the user message.
        Use the execute_query tool to run this SQL query:
        
        ```sql
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.delivery_orders`
        WHERE CUSTOMER_ORDER_NUMBER = '<ORDER_NUMBER>'
        ```
        
        Replace <ORDER_NUMBER> with the actual order number provided.
        Return the order data found.
        """,
    tools=[execute_query],
    output_key="order_data"
)

# Customer notes agent
customer_notes_agent = Agent(
    model=GEMINI_MODEL,
    name="customer_notes_agent", 
    description="Fetches customer notes and summaries",
    instruction=f"""\
        You will receive order information in {{order_data}}.
        Extract the DATA_ID value from that data.
        
        Use the execute_query tool to run this SQL query:
        
        ```sql
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.delivery_notes`
        WHERE DATA_ID = <DATA_ID>
        ```
        
        Replace <DATA_ID> with the actual DATA_ID value.
        Return the notes data found.
        """,
    tools=[execute_query],
    output_key="notes_data"
)

# Products agent
products_agent = Agent(
    model=GEMINI_MODEL,
    name="products_agent",
    description="Fetches product information for the order",
    instruction=f"""\
        You will receive order information in {{order_data}}.
        Extract the DATA_ID value from that data.
        
        Use the execute_query tool to run this SQL query:
        
        ```sql
        SELECT *
        FROM `{PROJECT_ID}.{DATASET_ID}.delivery_products`
        WHERE DATA_ID = <DATA_ID>
        ```
        
        Replace <DATA_ID> with the actual DATA_ID value.
        Return all products associated with this order.
        """,
    tools=[execute_query],
    output_key="products_data"
)

# Parallel agent to fetch notes and products simultaneously
parallel_data_agent = ParallelAgent(
    name="parallel_data_agent",
    sub_agents=[customer_notes_agent, products_agent],
    description="Fetch customer notes and products in parallel"
)

# Final agent that assembles the structured data
data_assembler_agent = Agent(
    name="data_assembler_agent",
    model=GEMINI_MODEL,
    description="Assembles all collected data into structured format",
    instruction="""\
You have data from the previous agents:
Order Data: {{order_data}}
Notes Data: {{notes_data}}  
Products Data: {{products_data}}

Create a structured JSON output combining all data in this format:
{{
    "order": {{
        "DATA_ID": <from order data>,
        "CUSTOMER_ORDER_NUMBER": <from order data>,
        "WORK_ORDER_NUMBER": <from order data>,
        "SCHEDULED_DELIVERY_DATE": <from order data>,
        "VEHICLE_TYPE": <from order data>,
        "QUANTITY": <from order data>,
        "VOLUME_CUBEFT": <from order data>,
        "WEIGHT": <from order data>,
        "PALLET": <from order data>,
        "SERVICE_TYPE": <from order data>,
        "WINDOW_START": <from order data>,
        "WINDOW_END": <from order data>
    }},
    "customer": {{
        "CUSTOMER_NAME": <from order data>,
        "PRO_XTRA_MEMBER": <from order data>,
        "MANAGED_ACCOUNT": <from order data>,
        "COMMERCIAL_ADDRESS_FLAG": <from order data>,
        "DESTINATION_ADDRESS": <from order data>,
        "BUSINESS_HOURS": <from order data>,
        "CUSTOMER_NOTES": <from notes data>,
        "CUSTOMER_NOTES_LLM_SUMMARY": <from notes data>
    }},
    "products": [<list of SKU_DESCRIPTION from products data>],
    "environmental": {{
        "WTHR_CATEGORY": <from order data>,
        "PRECIPITATION": <from order data>,
        "STRT_VW_IMG_DSCRPTN": <from order data>
    }},
    "risk_info": {{
        "DLVRY_RISK_DECILE": <from order data>,
        "DLVRY_RISK_BUCKET": <from order data>,
        "DLVRY_RISK_PERCENTILE": <from order data>,
        "DLVRY_RISK_TOP_FEATURE": <from order data>
    }}
}}

Return ONLY the JSON structure, no additional text.
""",
    tools=[],
    output_key="structured_data"
)

# Full pipeline
data_collection_pipeline = SequentialAgent(
    name="data_collection_pipeline",
    sub_agents=[order_fetcher_agent, parallel_data_agent, data_assembler_agent],
    description="Complete data collection pipeline"
)

async def run_data_collection(order_number: str):
    """Run the data collection pipeline for a specific order"""
    # Setup
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="data_collection",
        user_id="user_1",
        session_id="data_session_001"
    )
    
    runner = Runner(
        agent=data_collection_pipeline,
        app_name="data_collection",
        session_service=session_service
    )
    
    print("=" * 60)
    print("DATA COLLECTION PIPELINE")
    print("=" * 60)
    print(f"\nCollecting data for order: {order_number}")
    print("\nRunning data collection pipeline...\n")
    
    # Create message with order number
    content = types.Content(
        role="user",
        parts=[types.Part(text=order_number)]
    )
    
    # Run pipeline
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    
    try:
        async for event in runner.run_async(
            user_id="user_1",
            session_id="data_session_001",
            new_message=content
        ):
            # Restore stderr temporarily to print progress
            sys.stderr = old_stderr
            
            if hasattr(event, "author") and event.author:
                if event.author in ["order_fetcher_agent", "customer_notes_agent", 
                                  "products_agent", "data_assembler_agent"]:
                    print(f"[{event.author}] processing...")
                    
            if event.is_final_response() and event.author == "data_assembler_agent":
                if event.content and event.content.parts:
                    print("\n" + "=" * 60)
                    print("DATA COLLECTION COMPLETE")
                    print("=" * 60)
                    
                    # Parse and save the structured data
                    try:
                        data_text = event.content.parts[0].text.strip()
                        # Remove markdown if present
                        if data_text.startswith("```json"):
                            data_text = data_text[7:]
                        if data_text.endswith("```"):
                            data_text = data_text[:-3]
                        
                        structured_data = json.loads(data_text.strip())
                        
                        # Save to file
                        with open('collected_order_data.json', 'w') as f:
                            json.dump(structured_data, f, indent=2)
                        
                        # Display summary
                        print(f"\nOrder: {structured_data['order']['CUSTOMER_ORDER_NUMBER']}")
                        print(f"Customer: {structured_data['customer']['CUSTOMER_NAME']}")
                        print(f"Delivery Date: {structured_data['order']['SCHEDULED_DELIVERY_DATE']}")
                        print(f"Products: {len(structured_data['products'])} items")
                        print(f"Risk Level: {structured_data['risk_info']['DLVRY_RISK_BUCKET']}")
                        
                        print("\n✅ Data saved to collected_order_data.json")
                        
                        return structured_data
                        
                    except Exception as e:
                        print(f"Error parsing data: {e}")
                        print("Raw response:", event.content.parts[0].text)
                break
                
            # Suppress warnings again
            sys.stderr = io.StringIO()
    finally:
        sys.stderr = old_stderr

if __name__ == "__main__":
    # Default order for testing - can be changed
    ORDER_NUMBER = "CG92094171"
    
    print(f"🔍 Running data collection for order: {ORDER_NUMBER}")
    print("(You can change the ORDER_NUMBER variable to test different orders)")
    print()
    
    asyncio.run(run_data_collection(ORDER_NUMBER))