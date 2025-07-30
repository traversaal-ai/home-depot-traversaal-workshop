
from google.adk.agents.llm_agent import LlmAgent
from workflow.mcp.delivery_tools import delivery_tools
from workflow.utils.config import GEMINI_MODEL 

#Street view analysis
streetview_agent = LlmAgent(
    name="StreetViewAgent",
    model=GEMINI_MODEL,
    instruction="""
    You are a Street View Analysis Agent.

    - Extract the URL from **STREET_VIEW_URL** in `order_information_result`.
    - Use it with `street_view_(url)` to get the live description.
    - Compare it with **STREET_VIEW_IMAGE_DESCRIPTION**.
    
    **IMPORTANT**: If the street view analysis fails (STATUS: FAILED/TIMEOUT/ERROR), proceed with the existing **STREET_VIEW_IMAGE_DESCRIPTION** from the order data and note:
    "Using existing street view description due to analysis unavailability."
    
    If analysis succeeds:
    - If there's a mismatch with existing description:
      - Give the new description for **STREET_VIEW_IMAGE_DESCRIPTION**.
      - Add a short comparison summary noting the difference.
    - If matched, confirm consistency briefly.
    
    Always start with 'Result for StreetViewAgent Agent'
    """,
    description="Provides StreetView information for delivery locations with fallback handling.",
    tools=[delivery_tools],
    output_key="streetview_info_result"
)

