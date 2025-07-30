import os
import warnings
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

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

# Communication templates (from policy)
TEMPLATES = {
    "standard_confirmation": "Hello {customer_name}, your Home Depot delivery #{order_number} is scheduled for {date}. {instructions}. Reply YES to confirm or CALL 1-800-HOME-DEPOT for changes.",
    "access_confirmation": "Home Depot delivery #{order_number} scheduled for {date} requires special access to {location}. Please confirm: {access_need}. Reply with instructions or call {phone}.",
    "weather_contingency": "Your Home Depot delivery #{order_number} may be affected by {weather} on {date}. Your {product_type} requires dry conditions. Reply 1 for next clear day, 2 to proceed, or 3 to call us.",
    "pro_notification": "PRO DELIVERY: Order #{order_number} scheduled {date}. {details}. Direct line: 1-800-PRODEPOT (5AM-9PM). Reply CONFIRM or call for priority changes.",
    "carrier_alert": "DELIVERY ALERT #{order_number}: {date} to {address}. Weight: {weight}lbs, {equipment_req}. Customer notes: {notes}. Risk: {risk_level}. Issues? Call dispatch: {dispatch_phone}"
}

# Support numbers
SUPPORT_NUMBERS = {
    "standard": "1-800-HOME-DEPOT",
    "pro": "1-800-PRODEPOT",
    "dispatch": "1-800-DISPATCH",
    "priority": "1-800-PRIORITY"
}


def check_policy_compliance(message: str, message_type: str) -> Dict[str, Any]:
    """Check if message complies with company policy"""
    compliance = {
        "compliant": True,
        "issues": [],
        "suggestions": []
    }
    
    # Check required elements
    if "#" not in message:
        compliance["compliant"] = False
        compliance["issues"].append("Missing order number reference")
        
    # Check prohibited content
    prohibited_terms = ["driver name", "guarantee", "promise", "definitely", "100%", "competitor"]
    for term in prohibited_terms:
        if term.lower() in message.lower():
            compliance["compliant"] = False
            compliance["issues"].append(f"Contains prohibited term: {term}")
            
    # Check message length
    if len(message) > 160:
        compliance["suggestions"].append("Consider shortening message for SMS (currently {} chars)".format(len(message)))
        
    # Check for support contact
    if not any(num in message for num in SUPPORT_NUMBERS.values()):
        compliance["suggestions"].append("Consider adding support contact information")
        
    return compliance


def generate_alternative_dates(original_date: str, weather_forecast: Optional[Dict[str, Any]] = None) -> List[str]:
    """Generate alternative delivery dates based on constraints"""
    try:
        # Parse original date
        date_obj = datetime.strptime(original_date, "%Y-%m-%d")
    except:
        # Fallback if date parsing fails
        date_obj = datetime.now()
        
    alternatives = []
    
    # Generate 3 alternative dates within 7 days
    for i in range(1, 8):
        alt_date = date_obj + timedelta(days=i)
        # Skip weekends for standard deliveries
        if alt_date.weekday() < 5:  # Monday = 0, Friday = 4
            alternatives.append(alt_date.strftime("%Y-%m-%d"))
            if len(alternatives) >= 3:
                break
                
    return alternatives


def format_customer_message(
    template_key: str,
    order_data: Dict[str, Any],
    risk_data: Dict[str, Any],
    product_data: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """Format customer message using templates"""
    
    template = TEMPLATES.get(template_key, TEMPLATES["standard_confirmation"])
    
    # Extract common fields
    order = order_data.get("order", {})
    customer = order_data.get("customer", {})
    
    # Build format dictionary
    format_dict = {
        "customer_name": customer.get("CUSTOMER_NAME", "Valued Customer"),
        "order_number": order.get("CUSTOMER_ORDER_NUMBER", ""),
        "date": order.get("SCHEDULED_DELIVERY_DATE", ""),
        "phone": SUPPORT_NUMBERS["pro"] if customer.get("PRO_XTRA_MEMBER") else SUPPORT_NUMBERS["standard"],
        **kwargs  # Allow additional custom fields
    }
    
    # Format message
    try:
        message = template.format(**format_dict)
    except KeyError as e:
        # Return safe fallback if template formatting fails
        message = f"Home Depot delivery #{format_dict['order_number']} update. Please call {format_dict['phone']} for details."
        
    return message


def generate_carrier_instructions(
    order_data: Dict[str, Any],
    risk_data: Dict[str, Any],
    product_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate specific instructions for carrier"""
    
    order = order_data.get("order", {})
    customer = order_data.get("customer", {})
    environmental = order_data.get("environmental", {})
    risk_assessment = risk_data.get("risk_assessment", {})
    
    instructions = {
        "priority": "STANDARD",
        "equipment_needed": [],
        "access_notes": [],
        "risk_mitigation": [],
        "contact_protocol": []
    }
    
    # Set priority based on risk and customer type
    if risk_assessment.get("risk_level") == "HIGH":
        instructions["priority"] = "HIGH"
    elif customer.get("PRO_XTRA_MEMBER"):
        instructions["priority"] = "PRO"
        
    # Equipment requirements based on weight
    weight = order.get("WEIGHT", 0)
    if weight > 3000:
        instructions["equipment_needed"].append("Heavy lift equipment required")
    if weight > 1500:
        instructions["equipment_needed"].append("2-person team recommended")
        
    # Access notes from street view
    street_desc = environmental.get("STRT_VW_IMG_DSCRPTN", "")
    if "limited" in street_desc.lower():
        instructions["access_notes"].append("Limited access - plan route carefully")
    if "dead end" in street_desc.lower():
        instructions["access_notes"].append("Dead end street - ensure turnaround space")
        
    # Customer special instructions
    if customer.get("CUSTOMER_NOTES"):
        instructions["access_notes"].append(f"Customer request: {customer['CUSTOMER_NOTES']}")
        
    # Risk mitigation
    for risk in risk_assessment.get("risk_factors", []):
        if "weather" in risk.lower():
            instructions["risk_mitigation"].append("Monitor weather conditions")
        elif "heavy" in risk.lower():
            instructions["risk_mitigation"].append("Confirm equipment before departure")
            
    # Contact protocol
    if risk_assessment.get("risk_level") == "HIGH":
        instructions["contact_protocol"].append("Call customer 1 hour before arrival")
    if customer.get("CUSTOMER_NOTES") and "call" in customer.get("CUSTOMER_NOTES", "").lower():
        instructions["contact_protocol"].append("Customer requests call before delivery")
        
    return instructions


def suggest_alternatives(
    order_data: Dict[str, Any],
    risk_data: Dict[str, Any],
    product_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Suggest alternative delivery solutions"""
    
    alternatives = []
    risk_assessment = risk_data.get("risk_assessment", {})
    order = order_data.get("order", {})
    
    # Date change alternatives
    if risk_assessment.get("risk_level") in ["HIGH", "MEDIUM"]:
        alt_dates = generate_alternative_dates(order.get("SCHEDULED_DELIVERY_DATE", ""))
        alternatives.append({
            "type": "reschedule",
            "description": "Reschedule to lower-risk date",
            "options": alt_dates,
            "approval_required": False
        })
        
    # Split delivery for large orders
    if order.get("WEIGHT", 0) > 3000 or order.get("QUANTITY", 0) > 100:
        alternatives.append({
            "type": "split_delivery",
            "description": "Split into multiple smaller deliveries",
            "options": ["2 deliveries", "3 deliveries"],
            "approval_required": False
        })
        
    # Hold for pickup
    if risk_assessment.get("risk_level") == "HIGH":
        alternatives.append({
            "type": "hold_pickup",
            "description": "Hold at store for customer pickup",
            "options": ["Will Call desk", "PRO desk pickup"],
            "approval_required": False
        })
        
    # Vehicle upgrade
    vehicle_issues = any("vehicle" in str(f).lower() for f in risk_assessment.get("risk_factors", []))
    if vehicle_issues:
        alternatives.append({
            "type": "vehicle_change",
            "description": "Upgrade to more suitable vehicle",
            "options": ["Box truck", "Smaller vehicle"],
            "approval_required": True
        })
        
    return alternatives


# Agent definitions

# Policy compliance checker agent
policy_checker_agent = Agent(
    model=GEMINI_MODEL,
    name="policy_checker_agent",
    description="Checks messages for policy compliance",
    instruction="""\
You receive draft messages and check them against company policy.

Use the check_policy_compliance tool on each message.

If non-compliant, suggest corrections that maintain the message intent while following policy.

Return compliance status and any revised messages.
""",
    tools=[check_policy_compliance],
    output_key="policy_compliance"
)

# Customer message generator agent
customer_message_agent = Agent(
    model=GEMINI_MODEL,
    name="customer_message_agent",
    description="Generates customer communications",
    instruction="""\
You receive comprehensive delivery data including order, risk, and product information.

Based on the risk level and customer type, generate appropriate customer messages:

1. For HIGH risk deliveries:
   - Use weather_contingency or access_confirmation templates
   - Include specific challenges and alternatives
   - Add priority support number

2. For PRO customers:
   - Use pro_notification template
   - Include extended support hours
   - Offer direct coordination options

3. For standard deliveries:
   - Use standard_confirmation template
   - Include special instructions if any
   - Keep message concise

Use the format_customer_message tool with appropriate template and data.

Generate 1-2 messages maximum, focusing on the most critical communication needs.

Return messages in JSON format:
{
    "customer_messages": [
        {
            "type": "primary|followup",
            "template_used": "<template_key>",
            "message": "<formatted message>",
            "send_timing": "immediate|1_day_before|morning_of"
        }
    ]
}
""",
    tools=[format_customer_message],
    output_key="customer_messages"
)

# Carrier instruction agent
carrier_instruction_agent = Agent(
    model=GEMINI_MODEL,
    name="carrier_instruction_agent",
    description="Generates carrier-specific delivery instructions",
    instruction="""\
You receive delivery data and risk assessments.

Use the generate_carrier_instructions tool to create detailed carrier guidance.

Focus on:
1. Equipment requirements based on weight/volume
2. Access challenges from street view data
3. Customer special requests
4. Risk mitigation steps

Also create a brief carrier message using the carrier_alert template via format_customer_message.

Return in JSON format:
{
    "carrier_communication": {
        "alert_message": "<formatted carrier alert>",
        "detailed_instructions": <output from generate_carrier_instructions tool>,
        "dispatch_priority": "STANDARD|HIGH|URGENT"
    }
}
""",
    tools=[generate_carrier_instructions, format_customer_message],
    output_key="carrier_communication"
)

# Alternative solution agent
alternative_solution_agent = Agent(
    model=GEMINI_MODEL,
    name="alternative_solution_agent",
    description="Suggests alternative delivery solutions",
    instruction="""\
You receive delivery data and risk assessments.

Use the suggest_alternatives tool to generate delivery alternatives.

Prioritize alternatives by:
1. Ease of implementation (no approval needed first)
2. Risk reduction potential
3. Customer convenience

For each alternative, provide clear benefits and implementation steps.

Return in JSON format:
{
    "alternative_solutions": <output from suggest_alternatives tool>,
    "recommended_action": {
        "primary_recommendation": "<best alternative>",
        "reason": "<why this is best>",
        "implementation": "<how to implement>"
    }
}
""",
    tools=[suggest_alternatives, generate_alternative_dates],
    output_key="alternative_solutions"
)

# Final communication assembler agent
communication_assembler_agent = Agent(
    model=GEMINI_MODEL,
    name="communication_assembler_agent",
    description="Assembles all communications into final output",
    instruction="""\
You receive all generated communications and compile them into a structured output.

Review all inputs:
- {customer_messages}
- {carrier_communication}
- {alternative_solutions}
- {policy_compliance}

Create a final JSON structure that includes:

{
    "communications": {
        "order_number": "<from order data>",
        "risk_level": "<from risk assessment>",
        "customer_messages": <from customer_message_agent>,
        "carrier_instructions": <from carrier_instruction_agent>,
        "alternatives": <from alternative_solution_agent>,
        "compliance_check": <from policy_checker_agent if any issues>,
        "action_summary": {
            "immediate_actions": [<list actions to take now>],
            "scheduled_actions": [<list actions for later>],
            "contingency_plans": [<backup options if needed>]
        }
    }
}

Return ONLY the JSON structure.
""",
    tools=[],
    output_key="final_communications"
)

# Parallel generation of communications
communication_generators = ParallelAgent(
    name="communication_generators",
    sub_agents=[customer_message_agent, carrier_instruction_agent, alternative_solution_agent],
    description="Generate all communication types in parallel"
)

# Sequential pipeline
communication_pipeline = SequentialAgent(
    name="communication_pipeline",
    sub_agents=[communication_generators, policy_checker_agent, communication_assembler_agent],
    description="Complete communication generation pipeline"
)


# Demo runner function
async def run_communication_generation(
    order_data: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    product_intelligence: Dict[str, Any]
):
    """Run communication generation pipeline"""
    
    # Setup
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="communication_generation",
        user_id="user_1",
        session_id="comm_session_001"
    )
    
    # Prepare combined data
    combined_data = {
        "order_data": order_data,
        "risk_assessment": risk_assessment,
        "product_intelligence": product_intelligence
    }
    
    runner = Runner(
        agent=communication_pipeline,
        app_name="communication_generation",
        session_service=session_service
    )
    
    print("=" * 60)
    print("COMMUNICATION GENERATION PIPELINE")
    print("=" * 60)
    print(f"\nGenerating communications for order: {order_data.get('order', {}).get('CUSTOMER_ORDER_NUMBER', 'Unknown')}")
    print(f"Risk Level: {risk_assessment.get('risk_assessment', {}).get('risk_level', 'Unknown')}")
    print(f"Customer Type: {'PRO' if order_data.get('customer', {}).get('PRO_XTRA_MEMBER') else 'Standard'}")
    print("\nGenerating messages...\n")
    
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
            session_id="comm_session_001",
            new_message=content
        ):
            sys.stderr = old_stderr
            
            if hasattr(event, "author") and event.author:
                if event.author in ["customer_message_agent", "carrier_instruction_agent", 
                                  "alternative_solution_agent", "policy_checker_agent"]:
                    print(f"[{event.author}] generating...")
                    
            if event.is_final_response() and event.author == "communication_assembler_agent":
                if event.content and event.content.parts:
                    print("\n" + "=" * 60)
                    print("COMMUNICATION OUTPUT")
                    print("=" * 60)
                    
                    # Parse and save JSON
                    try:
                        response_text = event.content.parts[0].text.strip()
                        if response_text.startswith("```json"):
                            response_text = response_text[7:]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]
                        
                        json_data = json.loads(response_text.strip())
                        
                        # Save to file
                        with open('communication_output.json', 'w') as f:
                            json.dump(json_data, f, indent=2)
                        
                        # Display formatted
                        print(json.dumps(json_data, indent=2))
                        print("\n✅ Communications saved to communication_output.json")
                    except Exception as e:
                        print("Error parsing JSON:", e)
                        print(event.content.parts[0].text)
                break
                
            sys.stderr = io.StringIO()
    finally:
        sys.stderr = old_stderr


if __name__ == "__main__":
    import asyncio
    
    print("📊 Loading data from previous exercises...")
    
    # Load test data from previous pipelines
    try:
        # Load order data from Exercise 1
        with open('../exercise_1_data_collection/collected_order_data.json', 'r') as f:
            order_data = json.load(f)
    except:
        print("Warning: collected_order_data.json not found. Using fallback data.")
        # Fallback to mock data
        order_data = {
            "order": {
                "CUSTOMER_ORDER_NUMBER": "CG92094171",
                "SCHEDULED_DELIVERY_DATE": "2025-06-21",
                "WEIGHT": 1598,
                "VEHICLE_TYPE": "FLAT"
            },
            "customer": {
                "CUSTOMER_NAME": "CUST_01518",
                "PRO_XTRA_MEMBER": True,
                "DESTINATION_ADDRESS": "668 FOREST AVE ELGIN, IL 60120",
                "CUSTOMER_NOTES": "call b/4 delivery delivery from the back of the building"
            },
            "environmental": {
                "WTHR_CATEGORY": "Clear",
                "PRECIPITATION": 0.09,
                "STRT_VW_IMG_DSCRPTN": "* The driveway is partially obscured by trees"
            }
        }
    
    try:
        # Load risk assessment from Exercise 2
        with open('../exercise_2_risk_assessment/risk_assessment_output.json', 'r') as f:
            risk_assessment = json.load(f)
    except:
        print("Warning: risk_assessment_output.json not found. Using fallback data.")
        # Fallback
        risk_assessment = {
            "risk_assessment": {
                "risk_level": "MEDIUM",
                "overall_risk_score": 7,
                "risk_factors": ["Heavy load", "Special instructions"],
                "recommendations": [
                    {
                        "action": "Schedule early morning delivery",
                        "priority": "HIGH",
                        "reason": "Avoid residential traffic"
                    }
                ]
            }
        }
    
    try:
        # Load product intelligence from Exercise 3
        with open('../exercise_3_product_intelligence/product_intelligence_output.json', 'r') as f:
            product_intelligence = json.load(f)
    except:
        print("Warning: product_intelligence_output.json not found. Using fallback data.")
        # Fallback
        product_intelligence = {
            "priority_scoring": {
                "priority_score": 65,
                "priority_level": "MEDIUM"
            },
            "product_analysis": {
                "weather_sensitive": True,
                "weather_concerns": ["lumber - protect from rain"],
                "handling_requirements": ["Heavy lifting equipment"]
            },
            "vehicle_compatibility": {
                "vehicle_appropriate": True,
                "issues": [],
                "recommendations": []
            }
        }
    
    print(f"\n🔍 Generating communications for order: {order_data['order']['CUSTOMER_ORDER_NUMBER']}")
    print(f"Risk Level: {risk_assessment['risk_assessment']['risk_level']}")
    print(f"Priority Score: {product_intelligence.get('priority_scoring', {}).get('priority_score', 'N/A')}")
    
    asyncio.run(run_communication_generation(order_data, risk_assessment, product_intelligence))