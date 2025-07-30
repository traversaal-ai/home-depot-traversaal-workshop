import asyncio
from google.adk.agents.llm_agent import LlmAgent
from workflow.mcp.delivery_tools import delivery_tools
from workflow.utils.config import GEMINI_MODEL 


customer_history_agent = LlmAgent(
    name="GetCustomerDeliveryHistory",
    model=GEMINI_MODEL,
    instruction="""You are an AI assistant that analyzes a customer's past delivery history to surface risks format it clearly with proper mention of user previous delivery history.Extract order_id pass it to the tool. Always start with "Result for GetCustomerDeliveryHistory Agent":""",
    description="Fetches previous deliveries and failed attempts.and mention order numbers",
    tools=[delivery_tools],
    output_key="customer_history_result"
)






