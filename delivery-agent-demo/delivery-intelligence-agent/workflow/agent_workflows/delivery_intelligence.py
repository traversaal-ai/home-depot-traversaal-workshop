#parallel agents
from workflow.agents.customer_information import customer_info_agent
from workflow.agents.customer_history import customer_history_agent
from workflow.agents.order_information import order_info_agent
#sequential agents
from workflow.agents.weather import weather_agent
from workflow.agents.street_view import streetview_agent
from workflow.agents.risk import risk_analyzer_agent
from workflow.agents.email import email_agent
from workflow.agents.case_card import case_card_agent
from workflow.agents.action import action_agent



from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent
# Parallel Research Agent
parallel_research_agent = ParallelAgent(
    name="CustomerDeliveryResearchAgent",
    sub_agents=[customer_info_agent, customer_history_agent,order_info_agent],
    description="Fetches customer data and past delivery history in parallel."
)

# Sequential Pipeline Agent
sequential_pipeline_agent = SequentialAgent(
    name="DeliveryIntelligencePipeline",
    sub_agents=[parallel_research_agent,
                weather_agent,
                streetview_agent,
                risk_analyzer_agent,
                email_agent,
                case_card_agent,
                action_agent],
    
    description="Fetches all customer delivery context and synthesizes a risk-focused case card and performs actions."
)

delivery_intelligence_agent = sequential_pipeline_agent

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from workflow.utils.config import APP_NAME
session_service = InMemorySessionService()

delivery_intelligence_runner = Runner(
    agent=delivery_intelligence_agent,
    app_name=APP_NAME,
    session_service=session_service
)
