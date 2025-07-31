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
from utils import evaluate_prompt, mask_sensitive_data, safety_settings, get_customer_context, order_tables_detail, anchor_tables_detail
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
import json
import random

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.ERROR)

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "traversaal-research"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

APP_NAME = "call_center_app"
AGENT_MODEL = "gemini-2.5-flash"
USE_MEMORY = False

# Customer IDs to test
CUSTOMER_IDS = [
    "MVLYDG3GVZDQX8LX1B",  # Kathy Willis - Hammer
    "IH9FPX5VI75SS6ZJ6V",  # Zachary Ashley - Dishwasher
    "5FUF61RKON3HI1PS3T",  # Joseph Krause - Dishwasher
    "D73N9S9R350YGMRIRG",  # Becky Howard - Power Drill
    "AMMQJ2I0WTM94Z3KYR"   # Kayla Hansen - Power Drill
]

# Initialize client and model
client = QdrantClient(path="./qdrant_db")
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)
text_embeddings_size = 768

current_date = datetime.now().strftime("%B %d, %Y")

# Memory setup
if USE_MEMORY:
    m0_client = MemoryClient(api_key="m0-1C2ma9BUxVA5Y9AHGAKcXJBWWmCnWP34WBAWVglz")
    memory_context = "Memory enabled"
else:
    m0_client = None
    memory_context = "No memory available."

def get_system_prompt(user_id):
    user_context = get_customer_context(user_id)
    
    if USE_MEMORY and m0_client:
        try:
            all_memories = m0_client.get_all(user_id=user_id)
            memory_ctx = "\n".join([f"- {m['memory']}" for m in all_memories]) if all_memories else "No previous context."
        except:
            memory_ctx = "No memory available."
    else:
        memory_ctx = "No memory available."

    return f"""You are a polite, empathetic Home Depot Return and Support Assistant. Always start with a warm greeting.

WORKFLOW:
1. For ANY customer request, FIRST call `get_policy_rag` tool with their request
2. Based on policy results, reason and decide the appropriate action tool to call but in the case of return give both options, offer recommend alternatives from Anchor table or return.

ACTION REASONING:
- **query_data**: Use when you need order/purchase details (query Order table using customer_id only)
- **action_agent**: Use when policy allows an action (returns, delivery changes, etc.) and customer confirms

COMMON REQUEST PATTERNS:
- Returns/damaged items → query_data → get_policy_rag → offer recommend alternatives from Anchor table or return
- Order details → query_data
- Delivery changes → query_data → get_policy_rag (if status="Pending")
- General support → get_policy_rag → respond based on policy

ADDITIONAL GUIDANCE:
- If request is valid, delegate action to action_agent after confirmation from user request
- Delivery changes only allowed for Pending orders
- Always explain policy clearly before taking action
- If policy invalid/expired, apologize and offer alternatives
- Summarize resolution and ask if they need anything else
- If the customer prefer recommended item, reason about the price difference between purchased item and recommended item and update action_agent in query

### ORDER DATABASE SCHEMA:
{order_tables_detail}

### ANCHOR DATABASE SCHEMA:
{anchor_tables_detail}

### CUSTOMER INFORMATION:
{user_context}

#### PAST MEMORY CONTEXT:
{memory_ctx}"""

############################################### Qdrant RAG Retrieval Functions

def search_user_requests(query, model, client, policy_filter=None, k=10):
    """Search user requests with optional policy filter."""
    query_embedding = model.encode(query, show_progress_bar=False).tolist()
    
    results = client.query_points(
        collection_name="user_requests",
        query=query_embedding,
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
            'policy_details': result.payload['policy_details'],
            'action_taken': result.payload['action_taken'],
            'summary': result.payload['summary']
        })
    return parsed_results

# ######################################## Mock Functions for Sub Agents

def action_tool(user_id: str, order_id: str, query: str) -> str:
    """Processes the action for a customer's request."""
    print(f"--- Tool: action_tool called for User: {user_id}, Order: {order_id}, Query: {query}  ---")
    
    try:
        client = bigquery.Client()
        table_id = "traversaal-research.home_depot_policy.action_tab"
        
        rows_to_insert = [{
            "customer_id": user_id,
            "order_number": order_id,
            "query": query
        }]
        
        errors = client.insert_rows_json(table_id, rows_to_insert)
        
        if not errors:
            print("Successfully added to BigQuery")
        else:
            print(f"BigQuery insert errors: {errors}")
            
    except Exception as e:
        print(f"BigQuery error: {e}")
    
    return "The action process has been successfully initiated. You can expect a confirmation email shortly with further details."

def get_policy_rag(user_request: str) -> str:
    """Retrieves policy information using RAG."""
    print(f"--- Tool: get_policy_rag called for: {user_request} ---")

    try:
        results = search_user_requests(user_request, model, client, k=3)
        
        if not results:
            return f"No policy found for: {user_request}"
        
        parsed = parse_search_results(results)
        
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

############################################### Customer Agent

class CustomerAgent:
    def __init__(self):
        self.agent = LlmAgent(
            model="gemini-2.5-flash",
            name="customer_agent",
            instruction="""You are a Home Depot customer calling support. Generate realistic scenarios:
            
            SCENARIOS TO SIMULATE:
            - Return requests (damaged, wrong item, changed mind)
            - Delivery issues (late, missed, wrong address)
            - Order changes (pickup method, cancellation)
            - Product inquiries
            - Warranty/policy questions
            
            BEHAVIOR:
            - Start with your specific issue
            - Be natural and conversational
            - Provide details when asked
            - Make decisions when given options
            - Ask follow-up questions
            - End when satisfied or resolved
            
            Keep responses concise and realistic."""
        )
        
        self.scenarios = [
            "I received a damaged {product} and need to return it",
            "I want to return my {product} - I changed my mind",
            "My order is late and I need to know when it will arrive",
            "I need to change my delivery from store pickup to home delivery",
            "The {product} I received is the wrong model",
            "I want to cancel my pending order",
            "Can I get a refund for my {product}?",
            "My delivery was missed and I need to reschedule"
        ]

    async def generate_scenario(self, customer_id: str, customer_data: dict) -> str:
        """Generate initial customer request"""
        scenario = random.choice(self.scenarios)
        product = customer_data.get('sku_name', 'item')
        return scenario.format(product=product)

    async def respond(self, message: str, context: str = "") -> str:
        """Generate customer response"""
        prompt = f"Context: {context}\nSupport Agent: {message}\nCustomer Response:"
        
        content = types.Content(role='user', parts=[types.Part(text=prompt)])
        
        # Create a simple session for the customer agent
        try:
            session_service = InMemorySessionService()
            artifacts_service = InMemoryArtifactService()
            
            session = await session_service.create_session(
                state={}, 
                app_name="customer_app", 
                user_id="customer_user", 
                session_id=f"customer_session_{uuid.uuid4().hex}"
            )
            
            runner = Runner(
                app_name="customer_app",
                agent=self.agent,
                artifact_service=artifacts_service,
                session_service=session_service,
            )
            
            events = runner.run_async(
                session_id=session.id,
                user_id=session.user_id,
                new_message=content
            )
            
            response = ""
            async for event in events:
                if hasattr(event, 'content') and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response = part.text
            
            return response or "I understand."
            
        except Exception as e:
            print(f"Error in customer response: {e}")
            return "I understand."

############################################### Scenario Runner

class ScenarioRunner:
    def __init__(self, customer_agent):
        self.customer_agent = customer_agent
        self.conversations = []

    async def create_support_agent(self, customer_id: str):
        """Create support agent for specific customer"""
        orders_tools = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='python',
                    args=["./test_server.py"]
                )
            )
        )
        
        action_agent = LlmAgent(
            model=AGENT_MODEL,
            name="action_agent",
            instruction="You are a Action Agent, Your only task is to execute the action immediately using the corresponding tool based on given information and transfer to call_center_agent.",
            description="Handles actions and provide using the tool execution outcome.",
            tools=[action_tool],
        )
        
        support_agent = LlmAgent(
            model=AGENT_MODEL,
            name='call_center_agent',
            description="Engages with customers and provides Home Depot return policies for various item categories.",
            instruction=get_system_prompt(customer_id),
            tools=[get_policy_rag, orders_tools],
            sub_agents=[action_agent]
        )
        
        session_service = InMemorySessionService()
        artifacts_service = InMemoryArtifactService()
        
        session = await session_service.create_session(
            state={}, 
            app_name=APP_NAME, 
            user_id=customer_id, 
            session_id=f"session_{uuid.uuid4().hex}"
        )
        
        runner = Runner(
            app_name=APP_NAME,
            agent=support_agent,
            artifact_service=artifacts_service,
            session_service=session_service,
        )
        
        return runner, session, orders_tools

    async def run_scenario(self, customer_id: str, max_turns: int = 8):
        """Run a complete customer scenario"""
        print(f"\n🎭 Starting scenario for customer {customer_id}")
        
        # Mock customer data (you can enhance this with real data)
        customer_data = {
            "customer_id": customer_id,
            "sku_name": "Power Drill" if "drill" in customer_id.lower() else "Hammer"
        }
        
        conversation = {
            "customer_id": customer_id,
            "timestamp": datetime.now().isoformat(),
            "messages": []
        }
        
        orders_tools = None
        
        try:
            # Create support agent for this customer
            support_runner, support_session, orders_tools = await self.create_support_agent(customer_id)
            
            # Generate initial customer request
            initial_request = await self.customer_agent.generate_scenario(customer_id, customer_data)
            conversation["messages"].append({
                "role": "customer",
                "content": initial_request,
                "timestamp": datetime.now().isoformat()
            })
            
            print(f"Customer: {initial_request}")
            
            current_message = initial_request
            
            for turn in range(max_turns):
                # Support agent responds
                try:
                    support_response = await self.call_support_agent(
                        current_message, support_runner, support_session
                    )
                    conversation["messages"].append({
                        "role": "support",
                        "content": support_response,
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"Support: {support_response}")
                    
                    # Check if conversation should end
                    if any(phrase in support_response.lower() for phrase in 
                          ["anything else", "is there anything", "thank you for", "goodbye"]):
                        # Customer final response
                        final_response = "Thank you for your help!"
                        conversation["messages"].append({
                            "role": "customer", 
                            "content": final_response,
                            "timestamp": datetime.now().isoformat()
                        })
                        print(f"Customer: {final_response}")
                        break
                    
                    # Customer responds
                    context = f"I am customer {customer_id} with issue: {initial_request}"
                    customer_response = await self.customer_agent.respond(support_response, context)
                    conversation["messages"].append({
                        "role": "customer",
                        "content": customer_response,
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"Customer: {customer_response}")
                    
                    current_message = customer_response
                    
                except Exception as e:
                    print(f"Error in turn {turn}: {e}")
                    break
            
            conversation["total_turns"] = len(conversation["messages"])
            self.conversations.append(conversation)
            print(f"✅ Scenario completed for {customer_id}")
            
        except Exception as e:
            print(f"❌ Error in scenario for {customer_id}: {e}")
        finally:
            if orders_tools:
                await orders_tools.close()

    async def call_support_agent(self, message: str, runner, session) -> str:
        """Call the support agent"""
        content = types.Content(role='user', parts=[types.Part(text=message)])
        
        events = runner.run_async(
            session_id=session.id,
            user_id=session.user_id,
            new_message=content
        )
        
        response = ""
        async for event in events:
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        response = part.text
        
        return response or "I understand your request."

    def save_conversations(self, filename: str = "customer_scenarios.json"):
        """Save all conversations to JSON"""
        with open(filename, 'w') as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_conversations": len(self.conversations),
                "conversations": self.conversations
            }, f, indent=2)
        print(f"💾 Saved {len(self.conversations)} conversations to {filename}")

############################################### Main Functions

async def run_scenarios():
    """Run multiple customer scenarios"""
    try:
        print(f"\033[1m\n🎭 Starting Customer Scenario Generation \033[0m")
        
        # Initialize customer agent and scenario runner
        customer_agent = CustomerAgent()
        scenario_runner = ScenarioRunner(customer_agent)
        
        # Run scenarios for each customer
        for customer_id in CUSTOMER_IDS:
            await scenario_runner.run_scenario(customer_id)
            await asyncio.sleep(2)  # Brief pause between scenarios
        
        # Save all conversations
        scenario_runner.save_conversations()
        
        print(f"\n🎉 Generated {len(scenario_runner.conversations)} scenarios successfully!")
        
    except Exception as e:
        print(f"❌ Error running scenarios: {e}")
        import traceback
        traceback.print_exc()

async def run_conversation():
    """Original interactive conversation function"""
    orders_tools = None
    
    try:
        USER_ID = "MVLYDG3GVZDQX8LX1B"  # Default user for interactive mode
        SESSION_ID = f"session_{uuid.uuid4().hex}"
        
        action_agent = LlmAgent(
            model=AGENT_MODEL,
            name="action_agent",
            instruction="You are a Action Agent, Your only task is to execute the action immediately using the corresponding tool based on given information and transfer to call_center_agent.",
            description="Handles actions and provide using the tool execution outcome.",
            tools=[action_tool],
        )
        
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
            instruction=get_system_prompt(USER_ID),
            tools=[get_policy_rag, orders_tools],
            sub_agents=[action_agent]
        )
        
        print(f"\033[1m\n📊 Welcome to the Home Depot Call Center Agent \033[0m")
        print("Type your question or type 'exit' to quit.\n")
        
        session_service = InMemorySessionService()
        artifacts_service = InMemoryArtifactService()

        session = await session_service.create_session(
            state={}, app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
        
        runner = Runner(
            app_name=APP_NAME,
            agent=agent,
            artifact_service=artifacts_service,
            session_service=session_service,
        )
        
        while True:
            user_input = input("\nYou: ")
            if user_input.strip().lower() in ["exit", "quit"]:
                print("👋 Goodbye! Thanks for using the Home Depot Call Center Agent.")
                break

            content = types.Content(role='user', parts=[types.Part(text=user_input)])
            
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
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if orders_tools:
            await orders_tools.close()

if __name__ == "__main__":
    try:
        # Choose mode
        mode = input("Choose mode: (1) Interactive conversation (2) Generate scenarios: ")
        
        if mode == "1":
            asyncio.run(run_conversation())
        else:
            asyncio.run(run_scenarios())
            
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()