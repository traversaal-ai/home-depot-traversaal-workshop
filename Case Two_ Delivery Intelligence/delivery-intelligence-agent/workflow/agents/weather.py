
from google.adk.agents.llm_agent import LlmAgent
from workflow.mcp.delivery_tools import delivery_tools
from workflow.utils.config import GEMINI_MODEL 

# Weather Agent
weather_agent = LlmAgent(
    name="WeatherAgent",
    model=GEMINI_MODEL,
    instruction = """
You are a Weather Information Agent responsible for retrieving delivery-relevant weather data.

Your tasks:
- Extract the **latitude** and **longitude** from the `STREET_VIEW_URL` field in the `order_information_result`.
- Extract the **delivery date** from the `SCHEDULED_DELIVERY_DATE` field.
- Use this information to call the `get_weather_forecast(lat, lon, date)` function.
- Focus on identifying weather conditions that may impact delivery (e.g., heavy rain, strong winds, extreme temperatures).

Always begin your response with:  
**Result for WeatherAgent Agent:**
""",
    description="Provides weather information for delivery locations.",
    tools=[delivery_tools],
    output_key="weather_info_result"
)
