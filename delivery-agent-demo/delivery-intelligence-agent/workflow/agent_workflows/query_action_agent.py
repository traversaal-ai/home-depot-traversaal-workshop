from workflow.agents.query_action_table import action_table_sql_agent

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from workflow.utils.config import APP_NAME

session_service_action_agent = InMemorySessionService()

query_action_table = Runner(
    agent=action_table_sql_agent,
    app_name=APP_NAME,
    session_service=session_service_action_agent
)
