import os
import warnings
import logging
import json
from typing import Dict, Any
import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud import aiplatform
import google.auth

# Suppress warnings
warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)

# Environment setup
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "traversaal-research"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

from google.adk.agents import Agent, SequentialAgent, ParallelAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Initialize Vertex AI
credentials, project = google.auth.default()
vertexai.init(project=project, location="us-central1")

# Mock data from the first pipeline (joined order, customer, and product data)
MOCK_ORDER_DATA = {
    "order": {
        "DATA_ID": "2204",
        "MARKET": "CHICAGO",
        "SCHEDULED_DELIVERY_DATE": "2025-06-21",
        "DELIVERY_CREATE_DATE": "2025-06-19",
        "VEHICLE_TYPE": "FLAT",
        "CUSTOMER_ORDER_NUMBER": "CG92094171",
        "WORK_ORDER_NUMBER": "143763024",
        "SPECIAL_ORDER": False,
        "SERVICE_TYPE": "Outside Delivery",
        "WINDOW_START": "06:00:00",
        "WINDOW_END": "20:00:00",
        "QUANTITY": 109,
        "VOLUME_CUBEFT": 34.9,
        "WEIGHT": 1598,
        "PALLET": 3,
    },
    "customer": {
        "CUSTOMER_NAME": "CUST_01518",
        "PRO_XTRA_MEMBER": True,
        "MANAGED_ACCOUNT": True,
        "DESTINATION_ADDRESS": "668 FOREST AVE ELGIN, IL 60120",
        "COMMERCIAL_ADDRESS_FLAG": False,
        "BUSINESS_HOURS": "no timing available",
        "CUSTOMER_NOTES": "call b/4 delivery delivery from the back of the building",
    },
    "products": [
        "2 in. x 12 in. x 8 ft. 2 Prime Ground Contact Pressure-Treated Lumber",
        "2 in. x 4 in. x 12 ft. 2 Prime Ground Contact Pressure-Treated Southern Yellow Pine Lumber",
        "2 in. x 8 in. x 8 ft. 2 Prime Ground Contact Pressure-Treated Southern Yellow Pine Lumber",
        "4 in. x 4 in. x 8 ft. 2 Ground Contact Pressure-Treated Southern Yellow Pine Timber",
        "42 in. x 2 in. Pressure-Treated Southern Yellow Pine Wood Beveled 1-End Baluster",
        "5/4 in. x 6 in. x 10 ft. Standard Ground Contact Pressure-Treated Southern Yellow Pine Decking Board",
        "9 x 3 in. Tan Star Flat Head Wood Deck Screw (25 lbs. / 1543-Pieces)"
    ],
    "environmental": {
        "WTHR_CATEGORY": "Clear",
        "PRECIPITATION": 0.09,
        "STRT_VW_IMG_DSCRPTN": "* The driveway is partially obscured by trees, potentially limiting visibility.\n* Parking space is limited to street parking.\n* There is visible dead end"
    }
}


def call_external_risk_model(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call external risk assessment model (Claude via Vertex AI).
    In production, this would call the client's proprietary model.
    
    Args:
        order_data: Complete order information
        
    Returns:
        Risk assessment in the client's format
    """
    try:
        # For demo purposes, we'll use Gemini to simulate the external model
        model = GenerativeModel("gemini-1.5-flash")
        
        # Prepare the risk assessment prompt
        prompt = f"""
You are a delivery risk assessment model. Analyze the following Home Depot delivery order and provide a risk assessment.

Order Data:
{json.dumps(order_data, indent=2)}

Analyze the risk factors including:
- Order size and weight (heavy/bulky items increase risk)
- Customer notes and special instructions
- Address accessibility (parking, driveways, visibility)
- Weather conditions
- PRO customer status and delivery window requirements
- Product types (lumber and heavy materials are higher risk)

Return ONLY a JSON response in this exact format:
{{
    "DLVRY_RISK_DECILE": <integer 1-10, where 10 is highest risk>,
    "DLVRY_RISK_BUCKET": "<HIGH|MEDIUM|LOW>",
    "DLVRY_RISK_PERCENTILE": <integer 0-100>,
    "DLVRY_RISK_TOP_FEATURE": "<comma-separated list of top risk factors>"
}}

Base your assessment on:
- DECILE 8-10 = HIGH risk (top 30%)
- DECILE 4-7 = MEDIUM risk (middle 40%)  
- DECILE 1-3 = LOW risk (bottom 30%)
"""
        
        # Call the model
        response = model.generate_content(prompt)
        
        # Extract JSON from response
        response_text = response.text.strip()
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
            
        # Parse the JSON response
        result = json.loads(response_text.strip())
        result["status"] = "success"
        result["model_used"] = "gemini-1.5-flash (simulating external model)"
        
        return result
        
    except Exception as e:
        # Return a reasonable fallback assessment based on the data
        weight = order_data.get("order", {}).get("WEIGHT", 0)
        has_notes = bool(order_data.get("customer", {}).get("CUSTOMER_NOTES"))
        
        # Simple heuristic for fallback
        if weight > 2000 or has_notes:
            decile = 7
            bucket = "MEDIUM"
            percentile = 65
        else:
            decile = 4
            bucket = "MEDIUM"
            percentile = 35
            
        return {
            "status": "success",
            "model_used": "fallback_heuristic",
            "DLVRY_RISK_DECILE": decile,
            "DLVRY_RISK_BUCKET": bucket,
            "DLVRY_RISK_PERCENTILE": percentile,
            "DLVRY_RISK_TOP_FEATURE": "WEIGHT,CUSTOMER_NOTES"
        }


# Tool for customer-specific risk assessment
def assess_customer_risk(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assess delivery risk based on customer factors"""
    risk_score = 0
    factors = []
    
    # PRO customers typically have better receiving capabilities
    if customer_data.get("PRO_XTRA_MEMBER"):
        risk_score -= 2
        factors.append("PRO customer (lower risk)")
    
    # Special delivery instructions increase complexity
    if customer_data.get("CUSTOMER_NOTES"):
        risk_score += 3
        factors.append("Special delivery instructions")
        
    # Commercial addresses usually have better access
    if customer_data.get("COMMERCIAL_ADDRESS_FLAG"):
        risk_score -= 1
        factors.append("Commercial address")
    else:
        risk_score += 1
        factors.append("Residential address")
    
    # Normalize score to 1-10
    risk_score = max(1, min(10, risk_score + 5))
    
    return {
        "customer_risk_score": risk_score,
        "customer_factors": factors,
        "is_pro": customer_data.get("PRO_XTRA_MEMBER", False),
        "has_special_instructions": bool(customer_data.get("CUSTOMER_NOTES"))
    }


# Tool for route/access risk assessment  
def assess_route_risk(order_data: Dict[str, Any], environmental_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assess delivery risk based on route and access factors"""
    risk_score = 0
    factors = []
    
    # Heavy orders are harder to deliver
    weight = order_data.get("WEIGHT", 0)
    if weight > 3000:
        risk_score += 4
        factors.append("Very heavy load (>3000 lbs)")
    elif weight > 1500:
        risk_score += 2
        factors.append("Heavy load (>1500 lbs)")
    
    # Street view description analysis
    street_desc = environmental_data.get("STRT_VW_IMG_DSCRPTN", "")
    if "limited" in street_desc.lower() or "narrow" in street_desc.lower():
        risk_score += 3
        factors.append("Access limitations noted")
    if "dead end" in street_desc.lower():
        risk_score += 1
        factors.append("Dead end street")
        
    # Vehicle type
    if order_data.get("VEHICLE_TYPE") == "FLAT":
        risk_score += 1
        factors.append("Requires flatbed truck")
    
    # Normalize score to 1-10
    risk_score = max(1, min(10, risk_score + 3))
    
    return {
        "route_risk_score": risk_score,
        "route_factors": factors,
        "weight": weight,
        "vehicle_type": order_data.get("VEHICLE_TYPE")
    }


# Model for agents
GEMINI_MODEL = "gemini-2.0-flash"

# Create the main risk assessment agent that calls external model
external_risk_agent = Agent(
    model=GEMINI_MODEL,
    name="external_risk_agent",
    description="Calls external risk assessment model",
    instruction="""\
You will receive consolidated order data in the user message.

Parse the JSON order data from the user message and use the call_external_risk_model tool to get risk assessment from the external model.

Pass the entire order data structure to the model and return its assessment.

This demonstrates integration with external AI models - in production, this would call the client's proprietary risk model.
""",
    tools=[call_external_risk_model],
    output_key="external_risk_assessment"
)

# Weather risk agent - NOW USES MCP WEATHER SERVICE
weather_risk_agent = Agent(
    model=GEMINI_MODEL,
    name="weather_risk_agent", 
    description="Assesses weather-related delivery risks using real weather data",
    instruction="""\
You will receive order data in the user message.

Parse the JSON order data and:
1. Extract the delivery date from order.SCHEDULED_DELIVERY_DATE
2. Extract the city from either order.MARKET or parse it from customer.DESTINATION_ADDRESS
3. Use the 'assess_weather_risk' tool from the MCP weather service to get real weather risk assessment

The MCP tool will return a structured risk assessment with:
- weather_risk_score (1-10)
- weather_factors (list of risk factors)
- risk_level (HIGH/MEDIUM/LOW)
- actual weather data

Return this assessment data.
""",
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command=os.path.abspath("/home/usman/code/traversaal/di-agent/weather_mcp_server.py"),
                args=[],
            ),
            tool_filter=['assess_weather_risk']  # Only use the risk assessment tool
        )
    ],
    output_key="weather_risk"
)

# Customer risk agent
customer_risk_agent = Agent(
    model=GEMINI_MODEL,
    name="customer_risk_agent",
    description="Assesses customer-specific delivery risks",
    instruction="""\
You will receive order data in the user message.

Parse the JSON order data, extract the customer data and use the assess_customer_risk tool to evaluate customer-related delivery risks.

Consider PRO status, special instructions, and address type.
""",
    tools=[assess_customer_risk],
    output_key="customer_risk"
)

# Route risk agent
route_risk_agent = Agent(
    model=GEMINI_MODEL,
    name="route_risk_agent",
    description="Assesses route and accessibility risks",
    instruction="""\
You will receive order data in the user message.

Parse the JSON order data, extract order and environmental data, then use the assess_route_risk tool to evaluate route-related delivery risks.

Consider load weight, vehicle requirements, and street accessibility.
""",
    tools=[assess_route_risk],
    output_key="route_risk"
)

# Parallel execution of additional risk assessments
additional_risks_agent = ParallelAgent(
    name="additional_risks_agent",
    sub_agents=[weather_risk_agent, customer_risk_agent, route_risk_agent],
    description="Assess multiple risk factors in parallel"
)

# Final risk aggregation agent
risk_aggregation_agent = Agent(
    name="risk_aggregation_agent",
    model=GEMINI_MODEL,
    description="Aggregates all risk assessments into final recommendation",
    instruction="""\
You have received multiple risk assessments:

External Model Assessment: {external_risk_assessment}
Weather Risk: {weather_risk}
Customer Risk: {customer_risk}
Route Risk: {route_risk}

Create a comprehensive risk report that:

1. **Overall Risk Summary**
   - Show the external model's assessment (DECILE, BUCKET, PERCENTILE)
   - List the top risk features identified

2. **Detailed Risk Factors**
   - Weather conditions and impact (NOTE if using real-time data vs simulated)
   - Customer-specific considerations
   - Route and accessibility challenges

3. **Recommendations**
   - Specific actions to mitigate identified risks
   - Priority level for each recommendation

4. **Risk Score Comparison**
   - Compare external model assessment with our factor analysis
   - Highlight any discrepancies or additional insights

Format the report clearly with sections and bullet points.
""",
    tools=[]
)

# Full risk assessment pipeline
risk_assessment_pipeline = SequentialAgent(
    name="risk_assessment_pipeline",
    sub_agents=[external_risk_agent, additional_risks_agent, risk_aggregation_agent],
    description="Complete risk assessment pipeline with external model integration and real weather data"
)


# Demo runner function
async def run_risk_assessment():
    # Setup
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="risk_assessment",
        user_id="user_1",
        session_id="risk_session_001"
    )
    
    # Add order data to session state BEFORE creating runner
    session = await session_service.get_session(
        app_name="risk_assessment",
        user_id="user_1", 
        session_id="risk_session_001"
    )
    session.state["order_data"] = MOCK_ORDER_DATA
    
    runner = Runner(
        agent=risk_assessment_pipeline,
        app_name="risk_assessment",
        session_service=session_service
    )
    
    print("=" * 60)
    print("DELIVERY RISK ASSESSMENT PIPELINE (with MCP Weather)")
    print("=" * 60)
    print("\nOrder Details:")
    print(f"- Order Number: {MOCK_ORDER_DATA['order']['CUSTOMER_ORDER_NUMBER']}")
    print(f"- Customer: {MOCK_ORDER_DATA['customer']['CUSTOMER_NAME']}")
    print(f"- Weight: {MOCK_ORDER_DATA['order']['WEIGHT']} lbs")
    print(f"- Address: {MOCK_ORDER_DATA['customer']['DESTINATION_ADDRESS']}")
    print(f"- Delivery Date: {MOCK_ORDER_DATA['order']['SCHEDULED_DELIVERY_DATE']}")
    print("\nRunning risk assessment with real weather data...\n")
    
    # Create message with order data
    content = types.Content(
        role="user",
        parts=[types.Part(text=f"Assess delivery risk for order: {json.dumps(MOCK_ORDER_DATA)}")]
    )
    
    # Temporarily redirect stderr to suppress runtime warnings
    import sys
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    
    try:
        # Run the pipeline
        async for event in runner.run_async(
            user_id="user_1",
            session_id="risk_session_001",
            new_message=content
        ):
            # Restore stderr briefly for our print statements
            sys.stderr = old_stderr
            
            if hasattr(event, "author") and event.author:
                if event.author in ["external_risk_agent", "weather_risk_agent", 
                                  "customer_risk_agent", "route_risk_agent"]:
                    print(f"[{event.author}] analyzing...")
                    if event.author == "weather_risk_agent":
                        print("  → Connecting to MCP weather service...")
                    
            if event.is_final_response() and event.author == "risk_aggregation_agent":
                if event.content and event.content.parts:
                    print("\n" + "=" * 60)
                    print("RISK ASSESSMENT REPORT")
                    print("=" * 60)
                    print(event.content.parts[0].text)
                break
                
            # Suppress warnings again
            sys.stderr = io.StringIO()
    finally:
        # Always restore stderr
        sys.stderr = old_stderr


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_risk_assessment())