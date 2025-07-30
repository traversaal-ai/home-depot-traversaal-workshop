import os
import warnings
import logging
import json
import sys
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


def load_order_data(file_path: str = '../exercise_1_data_collection/collected_order_data.json') -> Dict[str, Any]:
    """Load order data from the previous exercise"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Using sample data.")
        # Fallback sample data
        return {
            "order": {
                "DATA_ID": "2204",
                "CUSTOMER_ORDER_NUMBER": "CG92094171",
                "SCHEDULED_DELIVERY_DATE": "2025-06-21",
                "VEHICLE_TYPE": "FLAT",
                "QUANTITY": 109,
                "VOLUME_CUBEFT": 34.9,
                "WEIGHT": 1598,
                "PALLET": 3,
                "WINDOW_START": "06:00:00",
                "WINDOW_END": "20:00:00"
            },
            "customer": {
                "CUSTOMER_NAME": "CUST_01518",
                "PRO_XTRA_MEMBER": True,
                "COMMERCIAL_ADDRESS_FLAG": False,
                "DESTINATION_ADDRESS": "668 FOREST AVE ELGIN, IL 60120",
                "CUSTOMER_NOTES": "call b/4 delivery delivery from the back of the building"
            },
            "products": [
                "2 in. x 12 in. x 8 ft. 2 Prime Ground Contact Pressure-Treated Lumber",
                "2 in. x 4 in. x 12 ft. 2 Prime Ground Contact Pressure-Treated Southern Yellow Pine Lumber"
            ],
            "environmental": {
                "WTHR_CATEGORY": "Clear",
                "PRECIPITATION": 0.09,
                "STRT_VW_IMG_DSCRPTN": "* The driveway is partially obscured by trees"
            },
            "risk_info": {
                "DLVRY_RISK_DECILE": 6,
                "DLVRY_RISK_BUCKET": "MEDIUM",
                "DLVRY_RISK_PERCENTILE": 65,
                "DLVRY_RISK_TOP_FEATURE": "WEIGHT,CUSTOMER_NOTES"
            }
        }


def call_external_risk_model(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call external risk assessment model.
    In production, this would call the client's proprietary model.
    For the workshop, we'll use the pre-calculated risk data from BigQuery.
    """
    # Handle case where agent passes JSON string instead of dict
    if isinstance(order_data, str):
        try:
            order_data = json.loads(order_data)
        except:
            return {"status": "error", "message": "Invalid order data format"}
    
    # Extract pre-calculated risk info from the order data
    risk_info = order_data.get('risk_info', {})
    
    # Map the BigQuery risk data to the expected format
    risk_bucket = risk_info.get('DLVRY_RISK_BUCKET', 'MEDIUM')
    risk_decile = risk_info.get('DLVRY_RISK_DECILE', 5)
    risk_percentile = risk_info.get('DLVRY_RISK_PERCENTILE', 50)
    top_features = risk_info.get('DLVRY_RISK_TOP_FEATURE', '').split(',')
    
    # Return in the format expected by the pipeline
    return {
        "status": "success",
        "risk_assessment": {
            "overall_risk_score": risk_decile,
            "risk_level": risk_bucket,
            "risk_percentile": risk_percentile,
            "top_risk_factors": top_features,
            "model_version": "bigquery_precalculated_v1"
        }
    }


def assess_weather_risk(environmental_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assess weather-related delivery risks"""
    precipitation = environmental_data.get('PRECIPITATION', 0)
    weather_category = environmental_data.get('WTHR_CATEGORY', 'Unknown')
    
    # Simple weather risk scoring
    risk_score = 0
    factors = []
    
    if isinstance(precipitation, str):
        precipitation = float(precipitation.replace(' inch', ''))
    
    if precipitation > 0.5:
        risk_score = 8
        factors.append(f"Heavy precipitation ({precipitation} inches)")
    elif precipitation > 0.1:
        risk_score = 4
        factors.append(f"Light precipitation ({precipitation} inches)")
    else:
        risk_score = 2
        factors.append("Favorable weather")
    
    if weather_category.lower() in ['rain', 'snow', 'storm']:
        risk_score = min(10, risk_score + 3)
        factors.append(f"Adverse weather: {weather_category}")
    
    return {
        "weather_risk_score": risk_score,
        "weather_factors": factors,
        "precipitation_inches": precipitation,
        "category": weather_category
    }


def assess_customer_risk(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assess customer-related delivery risks"""
    risk_score = 5  # Base score
    factors = []
    
    # PRO customers typically have lower risk
    if customer_data.get('PRO_XTRA_MEMBER', False):
        risk_score -= 2
        factors.append("PRO customer (lower risk)")
    
    # Commercial vs residential
    if customer_data.get('COMMERCIAL_ADDRESS_FLAG', False):
        risk_score -= 1
        factors.append("Commercial address")
    else:
        risk_score += 2
        factors.append("Residential address")
    
    # Customer notes indicate special requirements
    if customer_data.get('CUSTOMER_NOTES'):
        risk_score += 2
        factors.append("Special delivery instructions")
        
    return {
        "customer_risk_score": max(1, min(10, risk_score)),
        "customer_factors": factors,
        "has_special_instructions": bool(customer_data.get('CUSTOMER_NOTES'))
    }


def assess_route_risk(order_data: Dict[str, Any], environmental_data: Dict[str, Any]) -> Dict[str, Any]:
    """Assess route and accessibility risks"""
    risk_score = 5  # Base score
    factors = []
    
    # Vehicle type considerations
    vehicle_type = order_data.get('VEHICLE_TYPE', 'UNKNOWN')
    if vehicle_type == 'FLAT' and order_data.get('WEIGHT', 0) > 1000:
        risk_score += 2
        factors.append("Heavy load on flatbed")
    
    # Street view analysis
    street_desc = environmental_data.get('STRT_VW_IMG_DSCRPTN', '')
    if 'dead end' in street_desc.lower():
        risk_score += 2
        factors.append("Dead end street")
    if 'limited' in street_desc.lower() or 'narrow' in street_desc.lower():
        risk_score += 1
        factors.append("Access limitations noted")
    
    return {
        "route_risk_score": max(1, min(10, risk_score)),
        "route_factors": factors,
        "access_notes": street_desc
    }


# Model for all agents
GEMINI_MODEL = "gemini-2.0-flash"

# Agent 1: External risk model integration
external_risk_agent = Agent(
    model=GEMINI_MODEL,
    name="external_risk_agent",
    description="Integrates with external risk assessment model",
    instruction="""\
You will receive consolidated order data in the user message.
Parse the JSON order data from the user message and use the call_external_risk_model tool to get risk assessment from the external model.
Pass the entire order data structure to the model and return its assessment.
This demonstrates integration with external AI models - in production, this would call the client's proprietary risk model.
""",
    tools=[call_external_risk_model],
    output_key="external_risk_assessment"
)

# Weather risk agent - NOW WITH MCP INTEGRATION!
weather_risk_agent = Agent(
    model=GEMINI_MODEL,
    name="weather_risk_agent",
    description="Assesses weather-related delivery risks using MCP weather service",
    instruction="""\
You will receive order data in the user message.

Parse the JSON order data and:
1. Extract the delivery date from order.SCHEDULED_DELIVERY_DATE (format: "2025-06-21T00:00:00")
2. Extract the city - for Chicago area deliveries, use "Chicago"
3. Use the 'assess_weather_risk' MCP tool with the city and date

The tool will return structured risk data including:
- weather_risk_score (1-10)
- weather_factors (list of risk factors)
- weather_data (temperature, conditions, precipitation, etc.)
- risk_level (HIGH/MEDIUM/LOW)

Return the complete response from the MCP tool.
""",
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                # Use Python to run the weather MCP server
                command=sys.executable,
                args=[os.path.abspath(os.path.join(os.path.dirname(__file__), "weather_mcp_server.py"))],
            ),
            # Filter to only expose the risk assessment tool
            tool_filter=['assess_weather_risk']
        )
    ],
    output_key="weather_risk"
)

# Customer risk agent  
customer_risk_agent = Agent(
    model=GEMINI_MODEL,
    name="customer_risk_agent",
    description="Assesses customer-related delivery risks",
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

# Parallel agent for additional risk factors
additional_risks_agent = ParallelAgent(
    name="additional_risks_agent",
    sub_agents=[weather_risk_agent, customer_risk_agent, route_risk_agent],
    description="Assess multiple risk factors in parallel"
)

# Final risk aggregation agent - outputs structured data
risk_aggregation_agent = Agent(
    name="risk_aggregation_agent",
    model=GEMINI_MODEL,
    description="Aggregates all risk assessments into structured output",
    instruction="""\
You have received multiple risk assessments:
External Model Assessment: {external_risk_assessment}
Weather Risk: {weather_risk}
Customer Risk: {customer_risk}
Route Risk: {route_risk}

Create a structured JSON output that includes:
{
    "risk_assessment": {
        "overall_risk_score": <external model score>,
        "risk_level": "<HIGH/MEDIUM/LOW from external model>",
        "risk_percentile": <external model percentile>,
        "risk_scores": {
            "overall": <external model score>,
            "weather": <weather_risk_score>,
            "customer": <customer_risk_score>,
            "route": <route_risk_score>
        },
        "risk_factors": [
            // Array of all identified risk factors from all assessments
        ],
        "top_risks": "<comma-separated top features from external model>",
        "recommendations": [
            {
                "action": "<specific action>",
                "priority": "<HIGH/MEDIUM/LOW>",
                "reason": "<why this helps>"
            }
        ],
        "weather_data": {
            "weather_risk_score": <score>,
            "weather_factors": [...],
            "precipitation_inches": <value>,
            "category": "<category>"
        }
    }
}

Generate 2-3 specific recommendations based on the identified risks.
Return ONLY the JSON structure, no additional text.
""",
    tools=[],
    output_key="risk_aggregation"
)

# Full risk assessment pipeline
risk_assessment_pipeline = SequentialAgent(
    name="risk_assessment_pipeline",
    sub_agents=[external_risk_agent, additional_risks_agent, risk_aggregation_agent],
    description="Complete risk assessment pipeline with external model integration"
)


# Demo runner function
async def run_risk_assessment(order_data: Dict[str, Any] = None):
    """Run risk assessment pipeline on order data"""
    
    # Load order data if not provided
    if order_data is None:
        order_data = load_order_data()
    
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
    session.state["order_data"] = order_data
    
    runner = Runner(
        agent=risk_assessment_pipeline,
        app_name="risk_assessment",
        session_service=session_service
    )
    
    print("=" * 60)
    print("DELIVERY RISK ASSESSMENT PIPELINE")
    print("=" * 60)
    print(f"\nAssessing risk for order: {order_data.get('order', {}).get('CUSTOMER_ORDER_NUMBER', 'Unknown')}")
    print(f"Customer: {order_data.get('customer', {}).get('CUSTOMER_NAME', 'Unknown')}")
    print(f"Risk Level (Pre-calculated): {order_data.get('risk_info', {}).get('DLVRY_RISK_BUCKET', 'Unknown')}")
    print("\nRunning comprehensive risk assessment...\n")
    
    # Create message
    content = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(order_data))]
    )
    
    # Run pipeline
    import sys
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    
    try:
        async for event in runner.run_async(
            user_id="user_1",
            session_id="risk_session_001",
            new_message=content
        ):
            sys.stderr = old_stderr
            
            if hasattr(event, "author") and event.author:
                if event.author in ["external_risk_agent", "weather_risk_agent", 
                                  "customer_risk_agent", "route_risk_agent"]:
                    print(f"[{event.author}] analyzing...")
                    
            if event.is_final_response() and event.author == "risk_aggregation_agent":
                if event.content and event.content.parts:
                    print("\n" + "=" * 60)
                    print("STRUCTURED RISK ASSESSMENT")
                    print("=" * 60)
                    
                    # Parse and save JSON
                    try:
                        # Extract JSON from response
                        response_text = event.content.parts[0].text.strip()
                        if response_text.startswith("```json"):
                            response_text = response_text[7:]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]
                        
                        json_data = json.loads(response_text.strip())
                        
                        # Save to file in the same directory as this script
                        output_path = os.path.join(os.path.dirname(__file__), 'risk_assessment_output.json')
                        with open(output_path, 'w') as f:
                            json.dump(json_data, f, indent=2)
                        
                        # Display formatted
                        print(json.dumps(json_data, indent=2))
                        print(f"\n✅ Risk assessment saved to {output_path}")
                    except Exception as e:
                        print("Error parsing JSON:", e)
                        print(event.content.parts[0].text)
                break
                
            # Suppress warnings again
            sys.stderr = io.StringIO()
    finally:
        sys.stderr = old_stderr


if __name__ == "__main__":
    import asyncio
    
    print("📊 Loading order data from Exercise 1...")
    order_data = load_order_data()
    
    asyncio.run(run_risk_assessment(order_data))