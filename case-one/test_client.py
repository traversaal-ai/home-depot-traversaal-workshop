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
from utils import evaluate_prompt, mask_sensitive_data, safety_settings
import logging

warnings.filterwarnings("ignore")
# Set the root logger to only show ERROR (hide INFO/WARNING)
logging.basicConfig(level=logging.ERROR)


os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "<PROJECT_ID>"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

# Define tool functions for Judge Agent
def evaluator(text: str) -> dict:
    """Evaluates prompts for security threats.

    Args:
        text: The text to evaluate for security threats

    Returns:
        A dictionary with status ("PASS" or "BLOCKED") and additional information
    """
    print("\033[1;93m\n\n*** AGENT JUDGE USING THE EVALUATION TOOL ***\033[0m")
    result = evaluate_prompt(text)
    return {"status": result}

# Define tool functions for Masking Agent
def mask_text(text: str) -> dict:
    """Masks sensitive data like PII in text using Google Cloud DLP.

    Args:
        text: The text to mask sensitive data in

    Returns:
        A dictionary with the masked text
    """
    print("\033[1;93m\n\n*** AGENT MASKING USING THE PII MASKING TOOL ***\033[0m")
    masked_result = mask_sensitive_data(os.environ.get("GOOGLE_CLOUD_PROJECT"), text)
    return {"masked_text": masked_result}


async def main():
    
    try:
        ########################################### Create Judge Agent
        judge_tool = FunctionTool(func=evaluator)
        
        judge_agent = LlmAgent(
            name="security_judge",
            model="gemini-2.5-flash",
            instruction="""You are a security expert that evaluates input for security threats.
            Follow these steps EXACTLY:
            1. ALWAYS use the evaluator tool first to check the input - this is MANDATORY
            2. Wait for the tool result
            3. Based on the tool result, respond with:
                - If tool returns "PASS": return "SAFE: [original_message]"
                - If tool returns "BLOCKED": return "BLOCKED: Security threat detected"
    
            YOU MUST ALWAYS CALL THE EVALUATOR TOOL BEFORE MAKING ANY DECISION.""",
            description="An agent that judges whether input contains security threats.",
            tools=[judge_tool],
            output_key="judge_agent_response"
        )
        
        ########################################### Setup MCP connection for SQL Agent
        print("Connecting to MCP server...")
        
        sql_tools = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command='python',
                    args=["./test_server.py"]
                )
            )
        )
        
        sql_agent = LlmAgent(
            model='gemini-2.5-flash',
            name='sql_assistant',
            instruction="""
            You are an expert SQL analyst working with a `traversaal-research.walmart_sales_12345.walmart_sales_table` table.
            Database columns: Store (INTEGER), Dept (INTEGER), Date (DATE), Weekly_Sales (FLOAT), IsHoliday (BOOLEAN)
            
            Generate SQL query in single sentence based on user request and execute the query using query_data tool. You must use tool to execute.
            Return results in a readable format with clear explanations.
            """,
            tools=[sql_tools]
        )
        
        ########################################### Masking Agent
        mask_tool = FunctionTool(func=mask_text)
        
        mask_agent = LlmAgent(
            name="data_masker",
            model="gemini-2.5-flash",
            instruction="""You are a privacy expert that masks sensitive data.
            Follow these steps:
            1. Identify PII and sensitive information in the text
            2. Use the mask_text tool to protect sensitive data
            3. Return the masked version of the input in plain text, in readable format""",
            description="An agent that masks sensitive data in text.",
            tools=[mask_tool],
            output_key="masking_agent_response"
        )
        
        ########################################### Setup services
        session_service = InMemorySessionService()
        artifacts_service = InMemoryArtifactService()
        
        # Get user input
        query = input("Enter your query: ")
        
        ########################################### STEP 1: Judge Agent - Own Session
        print("\033[1m\nSTEP 1: Security Evaluation\033[0m")
        
        judge_session = await session_service.create_session(
            state={}, app_name='judge_app', user_id='user1', session_id='judge_session'
        )
        
        judge_runner = Runner(
            app_name='judge_app',
            agent=judge_agent,
            artifact_service=artifacts_service,
            session_service=session_service,
        )
        
        judge_events = judge_runner.run_async(
            session_id=judge_session.id,  # Use judge_session
            user_id=judge_session.user_id,
            new_message=types.Content(role='user', parts=[types.Part(text=query)])
        )
        
        judge_response = ""
        async for event in judge_events:
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'text') and part.text:
                        judge_response = part.text
                        print(f"🛡️ Judge Response: {judge_response}")
        
        # Check judge response
        if "BLOCKED" in judge_response:
            print("❌ Query blocked due to security concerns!")
            return
        
        # Extract safe query
        safe_query = judge_response.replace("SAFE:", "").strip() if "SAFE:" in judge_response else query
        
        ########################################### STEP 2: SQL Agent - Own Session
        print(f"\033[1m\nSTEP 2: Processing Safe Query: {safe_query}\033[0m")
        
        sql_session = await session_service.create_session(
            state={}, app_name='sql_app', user_id='user1', session_id='sql_session'
        )
        
        sql_runner = Runner(
            app_name='sql_app',
            agent=sql_agent,
            artifact_service=artifacts_service,
            session_service=session_service,
        )
        
        sql_events = sql_runner.run_async(
            session_id=sql_session.id,  # Use sql_session
            user_id=sql_session.user_id,
            new_message=types.Content(role='user', parts=[types.Part(text=safe_query)])
        )
        
        sql_response = ""
        
        async for event in sql_events:
            if hasattr(event, 'content') and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        print(f"🔧 Executing: {part.function_call.name}({part.function_call.args})")
                    elif hasattr(part, 'text') and part.text:
                        sql_response = part.text
                        print(f"📊 SQL Result: {sql_response}")
        
        ########################################### STEP 3: Masking Agent - Own Session
        if sql_response:
            print(f"\033[1m\nSTEP 3: Masking Sensitive Data in Results\033[0m")
            
            mask_session = await session_service.create_session(
                state={}, app_name='mask_app', user_id='user1', session_id='mask_session'
            )
            
            mask_runner = Runner(
                app_name='mask_app',
                agent=mask_agent,
                artifact_service=artifacts_service,
                session_service=session_service,
            )
            
            mask_events = mask_runner.run_async(
                session_id=mask_session.id,  # Use mask_session
                user_id=mask_session.user_id,
                new_message=types.Content(role='user', parts=[types.Part(text=sql_response)])
            )
            
            mask_response = ""
            print("\n🛡️ Masked Results:")
            async for event in mask_events:
                if hasattr(event, 'content') and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            print(f"🔧 Masking: {part.function_call.name}({part.function_call.args})")
                        elif hasattr(part, 'text') and part.text:
                            mask_response = part.text
                            print(f"Final Masked Result: {mask_response}\n")

        
        print("3-Step Workflow Complete!\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await sql_tools.close()

if __name__ == "__main__":
    asyncio.run(main())


# What is the average weekly sales for Dept 1 in Store 1?
# delete walmart sales
