
from google.adk.agents.llm_agent import LlmAgent
from workflow.mcp.delivery_tools import delivery_tools
from workflow.utils.config import GEMINI_MODEL 


customer_info_agent = LlmAgent(
    name="GetCustomerInfo",
    model=GEMINI_MODEL,
    instruction="""
You are an AI assistant that fetches and presents detailed customer information from the database. 

Your job is to:
- Extract the `order_id` from the user query.
- Call the `fetch_customer_info` tool to retrieve all relevant customer and address information.
- Format the final response as a structured report with clear **labels (column names)** and their **corresponding values**.
- If any field is missing or NULL, mention "Not Available".

Only respond with the formatted result. Always start with "Result for GetCustomerInfo Agent": 
""",
    description="Retrieves complete customer metadata , and formats the result in a clear, labeled structure.",
    tools=[delivery_tools],
    output_key="customer_info_result"
)
