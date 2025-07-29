import asyncio
from google.adk.agents.llm_agent import LlmAgent
from workflow.mcp.delivery_tools import delivery_tools
from workflow.utils.config import GEMINI_MODEL 
from workflow.utils.config import PROJECT_ID,DATASET_ID


TABLE_ID="action_update"
action_table_sql_agent = LlmAgent(
    model='gemini-2.5-flash',
    name='sql_assistant',
    instruction=f"""
You are an expert SQL analyst working with the `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` table.

You can generate and execute both SELECT and UPDATE SQL queries using the `query_action_tool`.

You have permission to update any column, including `rescheduled`, `updated_at`, `customer_name`, `message`, and `summary`.
You can just work or show the columns mentioned above, and you can only update {TABLE_ID} table nothing else.

For all UPDATE queries:
- Always include a WHERE clause using `DATA_ID = <order_id>`.
- When updating the rescheduled and`updated_at` field, use `DATETIME(CURRENT_TIMESTAMP())` instead of `CURRENT_TIMESTAMP()` to avoid type mismatch (DATETIME vs TIMESTAMP).
- Ensure proper SQL formatting.
- Execute queries using `query_action_tool`.
- Summarize the outcome in a human-readable format.

For SELECT queries:
- Format results nicely in a table or list.
- Also use `query_action_tool` to run the query.
""",
    tools=[delivery_tools],
    output_key="action_table_results"
)
