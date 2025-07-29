from google.adk.agents.llm_agent import LlmAgent
from workflow.mcp.delivery_tools import delivery_tools
from workflow.utils.config import GEMINI_MODEL 

# Insert values into action table with in big query
action_agent = LlmAgent(
    name="ActionAgent",
    model=GEMINI_MODEL,
    instruction="""
You are responsible for logging actions related to delivery risk analysis and customer communication.

You will be provided with:
{case_card_summary}

Use the function `action_update_database(order_id, customer_id, customer_name, message, summary)` to update the action log in BigQuery.

- `message` should contain the email content sent to the customer present in case card.
- `summary` should have everything in entire summary/case_Card but email.Each part except summary

Make sure the function is called after generating the message.

""",
    tools=[delivery_tools],
    description="Update action database",
)
