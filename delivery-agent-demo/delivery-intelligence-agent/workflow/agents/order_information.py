from google.adk.agents.llm_agent import LlmAgent
from workflow.mcp.delivery_tools import delivery_tools
from workflow.utils.config import GEMINI_MODEL 

order_info_agent = LlmAgent(
    name="GetOrderInfo",
    model=GEMINI_MODEL,
        instruction="""You are an AI assistant that fetches and presents detailed order information from the database. 

    Your job is to:
    - Extract the `order_id` from the user query.
    - Call the `fetch_delivery_info` tool to retrieve all relevant information.
    - Format the final response as a structured report with clear **labels (column names)** and their **corresponding values**.
    - If any field is missing or NULL, mention "Not Available".

    use delivery_item_info and fetch_delivery_info for complete information

    Only respond with the formatted result.
    Always start with 'Result for GetOrderInfo Agent' """,
    description="Fetches order details.",
    tools=[delivery_tools],
    output_key="order_information_result"
)
