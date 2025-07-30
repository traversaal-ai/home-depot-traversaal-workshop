import os
import warnings
import logging
import json
from typing import Dict, Any, List

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

# Model for all agents
GEMINI_MODEL = "gemini-2.0-flash"


def load_order_data(file_path: str = '../exercise_1_data_collection/collected_order_data.json') -> Dict[str, Any]:
    """Load order data from Exercise 1"""
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


def load_risk_assessment(file_path: str = '../exercise_2_risk_assessment/risk_assessment_output.json') -> Dict[str, Any]:
    """Load risk assessment from Exercise 2"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Using sample data.")
        # Fallback sample data
        return {
            "risk_assessment": {
                "overall_risk_score": 6,
                "risk_level": "MEDIUM",
                "risk_percentile": 65,
                "risk_scores": {
                    "overall": 6,
                    "weather": 2,
                    "customer": 5,
                    "route": 5
                },
                "risk_factors": [
                    "Heavy load on flatbed",
                    "Special delivery instructions",
                    "Residential address"
                ],
                "top_risks": "WEIGHT,CUSTOMER_NOTES",
                "recommendations": [
                    {
                        "action": "Schedule early morning delivery",
                        "priority": "HIGH",
                        "reason": "Avoid residential traffic"
                    }
                ]
            }
        }

# Weather-sensitive products database (in production, this would be in BigQuery)
WEATHER_SENSITIVE_PRODUCTS = {
    "drywall": {"rain_sensitive": True, "temp_sensitive": False, "humidity_sensitive": True},
    "cement": {"rain_sensitive": True, "temp_sensitive": True, "humidity_sensitive": False},
    "paint": {"rain_sensitive": False, "temp_sensitive": True, "humidity_sensitive": True},
    "lumber": {"rain_sensitive": True, "temp_sensitive": False, "humidity_sensitive": True},
    "insulation": {"rain_sensitive": True, "temp_sensitive": False, "humidity_sensitive": True},
    "shingles": {"rain_sensitive": False, "temp_sensitive": True, "humidity_sensitive": False},
}

# Vehicle capacity limits
VEHICLE_LIMITS = {
    "FLAT": {"max_weight": 5000, "max_volume": 500, "max_pallets": 8, "suitable_for": ["residential", "commercial"]},
    "BOX": {"max_weight": 3000, "max_volume": 300, "max_pallets": 6, "suitable_for": ["residential", "commercial"]},
    "SMALL": {"max_weight": 1500, "max_volume": 150, "max_pallets": 2, "suitable_for": ["residential"]},
}


def analyze_product_characteristics(products: List[str]) -> Dict[str, Any]:
    """Analyze product list for delivery characteristics"""
    analysis = {
        "total_products": len(products),
        "weather_sensitive": False,
        "weather_concerns": [],
        "handling_requirements": [],
        "product_categories": [],
        "bulk_items": False
    }
    
    for product in products:
        product_lower = product.lower()
        
        # Check weather sensitivity
        for sensitive_item, conditions in WEATHER_SENSITIVE_PRODUCTS.items():
            if sensitive_item in product_lower:
                analysis["weather_sensitive"] = True
                if conditions["rain_sensitive"]:
                    analysis["weather_concerns"].append(f"{sensitive_item} - protect from rain")
                if conditions["temp_sensitive"]:
                    analysis["weather_concerns"].append(f"{sensitive_item} - temperature sensitive")
                    
        # Identify handling requirements
        if "heavy" in product_lower or "timber" in product_lower or "lumber" in product_lower:
            analysis["handling_requirements"].append("Heavy lifting equipment")
            analysis["bulk_items"] = True
            
        if "fragile" in product_lower or "glass" in product_lower:
            analysis["handling_requirements"].append("Fragile handling")
            
        # Categorize products
        if "lumber" in product_lower or "wood" in product_lower:
            analysis["product_categories"].append("Lumber")
        elif "paint" in product_lower or "primer" in product_lower:
            analysis["product_categories"].append("Paint/Coatings")
        elif "concrete" in product_lower or "cement" in product_lower:
            analysis["product_categories"].append("Masonry")
            
    # Remove duplicates
    analysis["weather_concerns"] = list(set(analysis["weather_concerns"]))
    analysis["handling_requirements"] = list(set(analysis["handling_requirements"]))
    analysis["product_categories"] = list(set(analysis["product_categories"]))
    
    return analysis


def check_vehicle_compatibility(order_data: Dict[str, Any], customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Check if vehicle is appropriate for order and destination"""
    
    vehicle_type = order_data.get("VEHICLE_TYPE", "UNKNOWN")
    weight = order_data.get("WEIGHT", 0)
    volume = order_data.get("VOLUME_CUBEFT", 0)
    pallets = order_data.get("PALLET", 0)
    address_type = "commercial" if customer_data.get("COMMERCIAL_ADDRESS_FLAG", False) else "residential"
    
    compatibility = {
        "vehicle_appropriate": True,
        "issues": [],
        "recommendations": []
    }
    
    if vehicle_type in VEHICLE_LIMITS:
        limits = VEHICLE_LIMITS[vehicle_type]
        
        # Check weight limits
        if weight > limits["max_weight"]:
            compatibility["vehicle_appropriate"] = False
            compatibility["issues"].append(f"Weight ({weight} lbs) exceeds {vehicle_type} capacity ({limits['max_weight']} lbs)")
            compatibility["recommendations"].append("Consider larger vehicle or split delivery")
            
        # Check volume limits
        if volume > limits["max_volume"]:
            compatibility["vehicle_appropriate"] = False
            compatibility["issues"].append(f"Volume ({volume} cu ft) exceeds {vehicle_type} capacity")
            
        # Check pallet limits
        if pallets > limits["max_pallets"]:
            compatibility["vehicle_appropriate"] = False
            compatibility["issues"].append(f"Pallet count ({pallets}) exceeds {vehicle_type} capacity")
            
        # Check destination suitability
        if address_type == "residential" and vehicle_type == "FLAT":
            # Flat trucks can be problematic for residential
            if weight > 3000:  # Heavy flat truck delivery to residential
                compatibility["issues"].append("Large flatbed truck may have difficulty accessing residential area")
                compatibility["recommendations"].append("Consider smaller vehicle or verify access route")
                
    return compatibility


def calculate_priority_score(
    order_value: float,
    risk_level: str,
    is_pro_customer: bool,
    has_special_instructions: bool,
    weather_sensitive: bool,
    vehicle_issues: bool
) -> Dict[str, Any]:
    """Calculate priority score for the delivery case"""
    
    # Base score components
    value_score = min(30, order_value / 100)  # Max 30 points based on value
    
    risk_score_map = {"HIGH": 30, "MEDIUM": 20, "LOW": 10}
    risk_score = risk_score_map.get(risk_level, 15)
    
    # Bonus factors
    pro_bonus = 15 if is_pro_customer else 0
    instruction_bonus = 10 if has_special_instructions else 0
    weather_bonus = 10 if weather_sensitive else 0
    vehicle_bonus = 5 if vehicle_issues else 0
    
    # Calculate total
    total_score = value_score + risk_score + pro_bonus + instruction_bonus + weather_bonus + vehicle_bonus
    
    # Normalize to 0-100
    priority_score = min(100, int(total_score))
    
    return {
        "priority_score": priority_score,
        "score_breakdown": {
            "value_component": round(value_score),
            "risk_component": risk_score,
            "pro_customer_bonus": pro_bonus,
            "special_instructions_bonus": instruction_bonus,
            "weather_sensitivity_bonus": weather_bonus,
            "vehicle_mismatch_bonus": vehicle_bonus
        },
        "priority_level": "HIGH" if priority_score >= 70 else "MEDIUM" if priority_score >= 40 else "LOW"
    }


# Agent definitions

# Product analyzer agent
product_analyzer_agent = Agent(
    model=GEMINI_MODEL,
    name="product_analyzer_agent",
    description="Analyzes product descriptions for delivery characteristics",
    instruction="""\
You will receive order data. Extract order_data['products'] and use analyze_product_characteristics.

IMPORTANT: Return the EXACT JSON output from the tool, like this example:
{"total_products": 5, "weather_sensitive": true, "weather_concerns": ["lumber - protect from rain"], "handling_requirements": ["Heavy lifting equipment"], "product_categories": ["Lumber"], "bulk_items": true}

Do NOT add any text before or after the JSON.
""",
    tools=[analyze_product_characteristics],
    output_key="product_analysis"
)

# Vehicle compatibility agent
vehicle_matcher_agent = Agent(
    model=GEMINI_MODEL,
    name="vehicle_matcher_agent",
    description="Checks vehicle-destination compatibility",
    instruction="""\
You will receive order data. Extract the order information from order_data['order'] and customer information from order_data['customer'].
Use the check_vehicle_compatibility tool with these two arguments.

IMPORTANT: Return the EXACT JSON output from the tool, like this example:
{"vehicle_appropriate": true, "issues": [], "recommendations": []}

Do NOT add any text before or after the JSON.
""",
    tools=[check_vehicle_compatibility],
    output_key="vehicle_compatibility"
)

# Priority scoring agent
priority_scorer_agent = Agent(
    model=GEMINI_MODEL,
    name="priority_scorer_agent",
    description="Calculates delivery priority score",
    instruction="""\
You have access to data from previous agents and the original data:
- Product analysis in {product_analysis}
- Vehicle compatibility in {vehicle_compatibility}
- Original order_data and risk_assessment from user message

Extract the following values from the data:
- order_value: use order_data['order']['WEIGHT'] * 0.1 as a proxy (or QUANTITY * 10)
- risk_level: from risk_assessment['risk_assessment']['risk_level']
- is_pro_customer: from order_data['customer']['PRO_XTRA_MEMBER']
- has_special_instructions: true if order_data['customer']['CUSTOMER_NOTES'] is not empty
- weather_sensitive: from {product_analysis}['weather_sensitive']
- vehicle_issues: true if {vehicle_compatibility}['vehicle_appropriate'] is false

Call the calculate_priority_score tool with these parameters.

The tool will return a JSON response with this structure:
{
    "priority_score": <number>,
    "score_breakdown": {...},
    "priority_level": "<HIGH/MEDIUM/LOW>"
}

IMPORTANT: Return ONLY the JSON response from the calculate_priority_score tool.
Do NOT return the input parameters or add any text.
""",
    tools=[calculate_priority_score],
    output_key="priority_scoring"
)

# Insight generator agent
insight_generator_agent = Agent(
    model=GEMINI_MODEL,
    name="insight_generator_agent",
    description="Generates intelligent insights from all analyses",
    instruction="""\
Based on all the analyses provided, generate intelligent insights:

{product_analysis}
{vehicle_compatibility}
{priority_scoring}

Create a JSON structure with:
{
    "intelligent_insights": {
        "product_insights": "<summary of product analysis findings>",
        "delivery_complexity": "<assessment of delivery difficulty>",
        "key_challenges": [<list of main challenges>],
        "success_factors": [<factors that will help delivery succeed>],
        "equipment_needed": [<specific equipment requirements>]
    }
}

Focus on actionable insights that help GOAs make better decisions.
Return ONLY the JSON structure.
""",
    tools=[],
    output_key="delivery_insights"
)

# Parallel analysis of products and vehicles
analysis_agent = ParallelAgent(
    name="analysis_agent",
    sub_agents=[product_analyzer_agent, vehicle_matcher_agent],
    description="Analyze products and vehicle compatibility in parallel"
)

# Sequential pipeline
product_intelligence_pipeline = SequentialAgent(
    name="product_intelligence_pipeline",
    sub_agents=[analysis_agent, priority_scorer_agent, insight_generator_agent],
    description="Complete product intelligence and priority scoring pipeline"
)


# Demo runner function
async def run_product_intelligence(order_data: Dict[str, Any], risk_assessment: Dict[str, Any]):
    """Run product intelligence pipeline on order data"""
    
    # Setup
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="product_intelligence",
        user_id="user_1",
        session_id="prod_session_001"
    )
    
    # Prepare combined data
    combined_data = {
        "order_data": order_data,
        "risk_assessment": risk_assessment
    }
    
    runner = Runner(
        agent=product_intelligence_pipeline,
        app_name="product_intelligence",
        session_service=session_service
    )
    
    print("=" * 60)
    print("PRODUCT INTELLIGENCE PIPELINE")
    print("=" * 60)
    print(f"\nAnalyzing order: {order_data.get('order', {}).get('CUSTOMER_ORDER_NUMBER', 'Unknown')}")
    print(f"Products: {len(order_data.get('products', []))} items")
    print(f"Vehicle: {order_data.get('order', {}).get('VEHICLE_TYPE', 'Unknown')}")
    print("\nRunning analysis...\n")
    
    # Create message
    content = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(combined_data))]
    )
    
    # Run pipeline
    import sys
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    
    try:
        async for event in runner.run_async(
            user_id="user_1",
            session_id="prod_session_001",
            new_message=content
        ):
            sys.stderr = old_stderr
            
            if hasattr(event, "author") and event.author:
                if event.author in ["product_analyzer_agent", "vehicle_matcher_agent", 
                                  "priority_scorer_agent"]:
                    print(f"[{event.author}] processing...")
                    
            if event.is_final_response() and event.author == "insight_generator_agent":
                if event.content and event.content.parts:
                    print("\n" + "=" * 60)
                    print("PRODUCT INTELLIGENCE OUTPUT")
                    print("=" * 60)
                    
                    # Get all outputs from session state
                    session = await session_service.get_session(
                        app_name="product_intelligence",
                        user_id="user_1",
                        session_id="prod_session_001"
                    )
                    
                    # Try to parse insights JSON
                    try:
                        insights = json.loads(event.content.parts[0].text)
                    except:
                        # If parsing fails, create structure from text
                        insights = {
                            "intelligent_insights": {
                                "raw_output": event.content.parts[0].text
                            }
                        }
                    
                    # Helper to parse agent outputs
                    def parse_agent_output(output):
                        if isinstance(output, dict):
                            return output
                        if isinstance(output, str):
                            # Try to extract JSON from the string
                            import re
                            # Look for JSON pattern
                            json_match = re.search(r'\{.*\}', output, re.DOTALL)
                            if json_match:
                                try:
                                    return json.loads(json_match.group())
                                except:
                                    pass
                        return {}
                    
                    # Get outputs from session state
                    product_analysis = parse_agent_output(session.state.get("product_analysis", {}))
                    vehicle_compatibility = parse_agent_output(session.state.get("vehicle_compatibility", {}))
                    priority_scoring = parse_agent_output(session.state.get("priority_scoring", {}))
                    
                    # Combine all outputs
                    final_output = {
                        "product_analysis": product_analysis,
                        "vehicle_compatibility": vehicle_compatibility,
                        "priority_scoring": priority_scoring,
                        "delivery_insights": insights
                    }
                    
                    # Save to file
                    with open('product_intelligence_output.json', 'w') as f:
                        json.dump(final_output, f, indent=2)
                    
                    print(json.dumps(final_output, indent=2))
                    print("\n✅ Product intelligence saved to product_intelligence_output.json")
                break
                
            sys.stderr = io.StringIO()
    finally:
        sys.stderr = old_stderr


if __name__ == "__main__":
    import asyncio
    
    print("📊 Loading data from previous exercises...")
    
    # Load order data from Exercise 1
    order_data = load_order_data()
    
    # Load risk assessment from Exercise 2
    risk_assessment = load_risk_assessment()
    
    print(f"\n🔍 Analyzing order: {order_data['order']['CUSTOMER_ORDER_NUMBER']}")
    print(f"Risk Level: {risk_assessment['risk_assessment']['risk_level']}")
    
    asyncio.run(run_product_intelligence(order_data, risk_assessment))