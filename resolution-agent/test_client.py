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
from utils import get_customer_context, order_tables_detail, anchor_tables_detail, return_damaged_item_tool, delivery_method_change_tool, pickup_person_change_tool, apply_coupon_tool, customer_support_tool
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

warnings.filterwarnings("ignore")
# Set the root logger to only show ERROR (hide INFO/WARNING)
logging.basicConfig(level=logging.ERROR)

# PROJECT_ID = "traversaal-research"
# LOCATION_ID = "us-central1"

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = LOCATION_ID


APP_NAME = "call_center_app"
# USER_ID = "MVLYDG3GVZDQX8LX1B" # Kathy Willis # Hammer - 16oz Steel Claw status: delivered
USER_ID = "CCTAN90TXULCA5TXPB" # Dana Johnson # Ceiling Fan - 52-inch with Remote status: Pending # Delivery method: Store
SESSION_ID = f"session_{uuid.uuid4().hex}"
AGENT_MODEL = "gemini-2.5-flash"
USE_MEMORY = False  # Set to True or False

# Initialize client and model
client = QdrantClient(path="./qdrant_db")
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
text_embeddings_size = 768  # Update based on your model's output size

# Get current date in simple format
current_date = datetime.now().strftime("%B %d, %Y")  # January 15, 2024

user_context = get_customer_context(USER_ID)

# Memory setup
if USE_MEMORY:
    m0_client = MemoryClient(api_key="MEM0_API_KEY")
    try:
        all_memories = m0_client.get_all(user_id=USER_ID)
        memory_context = "\n".join([f"- {m['memory']}" for m in all_memories]) if all_memories else "No previous context."
        memory_context = f"{memory_context}"
        print(memory_context)
    except:
        memory_context = "No memory available."
else:
    m0_client = None
    memory_context = "No memory available."

    
SYSTEM_PROMPT = f"""You are a polite, empathetic Home Depot Return and Support Assistant. Always start with a warm greeting.

COMMON REQUEST PATTERNS:
- Returns/damaged items → query_data to get order details → get_policy_rag → offer recommend alternatives from Anchor table or return
- Delivery method change → query_data to get order details → get_policy_rag (if status="Pending")
- Order pickup person name change → query_data to get order details (if status="Pending")
- Apply Coupon → query_data to get order details → get_policy_rag (if status="Pending")
- Order details → query_data to get order details
- Customer details change request → get_policy_rag → respond based on policy


ADDITIONAL GUIDANCE:
- To get order details, Make sql query using only customer id and execute using query_data. Never ask for order id or customer id. Always get order details by yourself using only customer id.
- If request is valid, delegate action to action_agent after confirmation from user request. ALWAYS use the customer's unique ID: {USER_ID}
- When you check the policy, explain policy clearly.
- Summarize resolution and ask if they need anything else.
- If the customer return/damaged items, check order details, check policy and if policy allow, offer recommend alternatives from Anchor table or return.
- If the customer prefer recommended item, reason about the price difference between purchased item and recommended item and update action_agent in query.
- If the customer ask to change delivery method name, check order details, check policy and allow to change if status is pending.
- If the customer ask to change pickup person name, check order details and allow to change name if status is pending.
- If the customer ask to apply coupon, get order details, get policy, and act based on policy only if customer has not used more than two coupons or 1 coupon and 1 promotional credit in the past thirty days. 
- Must get coupon number from customer. Also this change is only applicable if status is pending. You can apply maximum of equal not greater than 15% promotion credit after one coupon however the maximum number of coupons (inclusive of promotional credit, coupons and promotional credits are considered the same) that can be applied in 30 days is two.
- if the customer ask to change customer details, get policy, get new information and change

### ORDER DATABASE SCHEMA:
{order_tables_detail}

### ANCHOR DATABASE SCHEMA:
{anchor_tables_detail}

### CUSTOMER INFORMATION:
{user_context}

#### PAST MEMORY CONTEXT:
{memory_context}"""

print(f"system prompt:\n {SYSTEM_PROMPT}")

############################################### Print Session

async def print_session_memory(session_service, app_name, user_id, session_id):
    """Convert session to messages format and print."""
    try:
        session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        
        messages = []
        
        for event in session.events:
            if hasattr(event, 'content') and event.content:
                role = getattr(event.content, 'role', 'unknown')
                # Convert "model" to "assistant"
                if role == 'model':
                    role = 'assistant'
                    
                if hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            messages.append({
                                "role": role,
                                "content": part.text
                            })
        
        # print(f"\n🧠 Messages ({len(messages)}):")
        # for msg in messages:
        #     print(f"Role: {msg['role']}, Content: {msg['content']}")
        
        if USE_MEMORY and m0_client:
            m0_client.add(messages, user_id=USER_ID)
            
    except Exception as e:
        print(f"🧠 Error: {e}")


############################################### Qdrant RAG Retrieval Functions FOR MAIN AGENT  Rag Tool 'get_policy_rag'

def search_user_requests(query, model, client, policy_filter=None, k=10):
    """
    Search user requests with optional policy filter.
    
    Args:
        query (str): The search query
        model: The sentence transformer model
        client: Qdrant client
        policy_filter (str): Filter by policy_applied field
        k (int): Number of results to return
    """
    query_embedding = model.encode(query, show_progress_bar=False).tolist()
    
    query_filter = None
    if policy_filter:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="policy_applied",
                    match=models.MatchValue(value=policy_filter)
                )
            ]
        )

    results = client.query_points(
        collection_name="user_requests",
        query=query_embedding,
        query_filter=query_filter,
        limit=k,
        with_payload=True,
    ).points

    return results


def parse_search_results(results):
    """Parse Qdrant search results into a clean format."""
    parsed_results = []
    
    for result in results:
        parsed_results.append({
            'score': result.score,
            'user_request': result.payload['user_request'],
            'customer_id': result.payload['customer_id'],
            'policy_applied': result.payload['policy_applied'],
            'policy_details': result.payload['policy_details'],  # Added this
            'action_taken': result.payload['action_taken'],
            'summary': result.payload['summary']
        })
    return parsed_results

########################################## Policy Rag Tool for MAIN Agent

def get_policy_rag(user_request: str) -> str:
    """
    Retrieves policy information using RAG.
    
    Args:
        user_request (str): The user's policy question
        
    Returns:
        str: Policy information
    """
    print(f"--- Tool: get_policy_rag called for: {user_request} ---")

    try:
        # Search for similar user requests
        results = search_user_requests(user_request, model, client, k=3)
        
        if not results:
            return f"No policy found for: {user_request}"
        
        # Parse results
        parsed = parse_search_results(results)
        
        # Format response
        response_parts = []
        for i, result in enumerate(parsed, 1):
            response_parts.append(
                f"Match {i} (Score: {result['score']:.3f}):\n"
                f"Similar Request: {result['user_request']}\n"
                f"Policy Applied: {result['policy_applied']}\n"
                f"Action Taken: {result['action_taken']}\n"
                f"Summary: {result['summary']}\n"
            )
        
        response = "\n".join(response_parts)
        print(f"Response retrieved from RAG:\n{response}")
        
        return response
        
    except Exception as e:
        return f"Error retrieving policy: {str(e)}"



######################################### Session and Runner
async def setup_session_and_runner(agent):
    session_service = InMemorySessionService()
    artifacts_service = InMemoryArtifactService()

    session = await session_service.create_session(
        state={}, app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )
    
    print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        artifact_service=artifacts_service,
        session_service=session_service,
    )
    
    print(f"Runner created for agent '{runner.agent.name}'.")
    
    return runner, session, USER_ID, SESSION_ID, session_service

# ########################################## Async Interaction with Agent

async def call_agent_async(query: str, runner, session, user_id, session_id):
    """Sends a query to the agent and prints the final response."""
    
    # Prepare the user's message in ADK format
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    # Execute the agent and process events
    events = runner.run_async(
        session_id=session.id,
        user_id=session.user_id,
        new_message=content
    )
        
    response = ""
    print("\n📋 Agent Response:")
    
    async for event in events:
        if hasattr(event, 'content') and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    print(f"🔧 Executing: {part.function_call.name}({part.function_call.args})")
                elif hasattr(part, 'text') and part.text:
                    response = part.text
                    print(f"📊 Result: {response}")
        
        # # Check if this is the final response
        # if hasattr(event, 'is_final_response') and event.is_final_response():
        #     if event.content and event.content.parts:
        #         final_text = event.content.parts[0].text if event.content.parts[0].text else response
        #         print(f"✅ Final Response: {final_text}")
        #     break

# ######################################### Main Conversation Function

async def run_conversation():
    orders_tools = None
    
    try:
        ####################### SUB AGENT
        action_agent = None
        
        action_agent = LlmAgent(
            model=AGENT_MODEL, # If you would like to experiment with other models
            name="action_agent",
            instruction=f"""You are a Action Agent, Your only task is to execute the action using the corresponding tool based on given information and immediately transfer to call_center_agent. ALWAYS use the customer's unique ID: {USER_ID}""",
            description="Handles actions and provide using the tool execution outcome.", # Crucial for delegation
            tools=[return_damaged_item_tool, delivery_method_change_tool, pickup_person_change_tool, apply_coupon_tool, customer_support_tool],
        )
        
        ###################### MAIN AGENT
        orders_tools = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='python',
                    args=["./test_server.py"]
                )
            )
        )
        
        agent = LlmAgent(
            model=AGENT_MODEL,
            name='call_center_agent',
            description="Engages with customers and provides Home Depot return policies for various item categories.",
            instruction=SYSTEM_PROMPT,
            tools=[
                get_policy_rag, # Policy Rag
                orders_tools # Order Information MCP
            ],
            sub_agents=[
                action_agent
            ]
        )
        
        # STEP 2:
        
        print(f"\033[1m\n📊 Welcome to the Home Depot Call Center Agent \033[0m")
        
        print("Type your question (e.g., 'Can I return a power drill?') or type 'exit' to quit.\n")
        
        runner, session, user_id, session_id, session_service = await setup_session_and_runner(agent)
        
        while True:
            user_input = input("\nYou: ")
            if user_input.strip().lower() in ["exit", "quit"]:
                print("👋 Goodbye! Thanks for using the Home Depot Call Center Agent.")
                break

            await call_agent_async(user_input, runner, session, user_id, session_id)
        
        await print_session_memory(session_service, APP_NAME, user_id, session_id)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if orders_tools:
            await orders_tools.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_conversation())
    except Exception as e:
        print(f"An error occurred: {e}")

