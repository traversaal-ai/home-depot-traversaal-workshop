import logging
import warnings
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.CRITICAL)
logging.getLogger().setLevel(logging.CRITICAL)
logging.getLogger("google").setLevel(logging.CRITICAL)
logging.getLogger("vertexai").setLevel(logging.CRITICAL)
logging.getLogger("httpx").setLevel(logging.CRITICAL)
logging.getLogger("httpcore").setLevel(logging.CRITICAL)

for logger_name in ['__main__', 'server', 'google', 'vertexai', 'httpx', 'httpcore']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)
    logging.getLogger(logger_name).disabled = True

    
    
import asyncio
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
import os
from google.adk.tools.function_tool import FunctionTool
import uuid
from google.adk.tools import FunctionTool
from datetime import datetime
from workflow.services.check_actions import check_order_action
from typing import Optional
import vertexai

from workflow.agent_workflows.delivery_intelligence import delivery_intelligence_runner,session_service
from workflow.agent_workflows.query_action_agent import query_action_table,session_service_action_agent



from workflow.utils.config import APP_NAME

import uuid
USER_ID = f"user_{ str(uuid.uuid4())}"
SESSION_ID = f"session_{str(uuid.uuid4())}"


print(f"Runner created for agent '{delivery_intelligence_runner.agent.name}'.")

# Async function that creates session and runs the agent
async def run_parallel_agent(query:str):
    # Create session asynchronously
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
    
    print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")
    
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    # Use async for loop with run_async
    async for event in delivery_intelligence_runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
        print()
        print('-'*15)
        if event.is_final_response():
            if event.content and event.content.parts:
                
                print(f" Response: {event.content.parts[0].text}")
                

async def run_action_table_agent(order_id: int):
    """
    Run the action table agent in a loop until user presses Enter or types 'quit'.
    """
    while True:
        print("If you want to query or update a record, enter your query. Otherwise, press Enter to exit.")
        user_query = input(f"Enter query/update for order_id {order_id} (or press Enter to return): ").strip()
        if not user_query or user_query.lower() == 'quit':
            break

        full_query = f"{user_query} order_id: {order_id}"

        session = await session_service_action_agent.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
        )
        print(f"[Session created] App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

        content = types.Content(role='user', parts=[types.Part(text=full_query)])

        async for event in query_action_table.run_async(
            user_id=USER_ID, session_id=SESSION_ID, new_message=content
        ):
            print('-' * 15)
            if event.is_final_response() and event.content and event.content.parts:
                print(f"Response: {event.content.parts[0].text}")

                
async def main():
    """Main function to handle user interaction"""
    print(" Home Depot Delivery Intelligence System")
    print("Enter 'q' to quit the program\n")
    
    while True:
        # customer_id_choice = input("Customer ID: ").strip()
        order_id_choice = input("Order ID (or 'q' to quit): ").strip()
        
        # Check if user wants to quit
        if order_id_choice.lower() == 'q':
            print("Exiting the system. Goodbye!")
            break
            
        if order_id_choice:
            results = check_order_action(order_id_choice)
            if results == "No results found":
                await run_parallel_agent(f"order_id:{order_id_choice}")
            else:
                await run_action_table_agent(order_id_choice)
        else:
            print("Invalid option. Please enter an Order ID or 'q' to quit.")



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Goodbye!")
    except Exception as e:
        print(f"An error occurred: {e}")