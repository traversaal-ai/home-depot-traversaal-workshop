"""
End-to-End Delivery Intelligence Pipeline
=========================================

This script demonstrates the complete delivery intelligence system,
running all components in sequence to produce actionable case cards
for General Office Associates (GOAs).

Pipeline Flow:
1. Data Collection → collected_order_data.json
2. Risk Assessment → risk_assessment_output.json  
3. Product Intelligence → product_intelligence_output.json
4. Communication Generation → communication_output.json
5. Final Case Card → delivery_case_card.json
"""

import os
import sys
import warnings
import logging
import json
import asyncio
from typing import Dict, Any
from datetime import datetime

# Suppress warnings
warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)

# Add parent directories to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'exercise_1_data_collection'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'exercise_2_risk_assessment'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'exercise_3_product_intelligence'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'exercise_4_communication_generation'))

# Environment setup
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "traversaal-research"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

from google.adk.agents import Agent, SequentialAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

# Import pipeline components
from data_for_intelligence import run_data_collection
from risk_assessment import run_risk_assessment
from product_intelligence import run_product_intelligence
from communication_generation import run_communication_generation

# Model for final agent
GEMINI_MODEL = "gemini-2.0-flash"

# ============================================
# 🎯 CHANGE THIS ORDER NUMBER TO TEST DIFFERENT CASES
# ============================================
ORDER_NUMBER = "CG92094171"  # Default order with lumber products
# ORDER_NUMBER = "CG92730950"  # Alternative order - composite deck board with special instructions
# ORDER_NUMBER = "CG92956860"  # Another alternative order


def generate_case_card(
    order_data: Dict[str, Any],
    risk_assessment: Dict[str, Any],
    product_intelligence: Dict[str, Any],
    communications: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate final case card combining all intelligence.
    
    Args:
        order_data: Order data from exercise 1
        risk_assessment: Risk assessment from exercise 2
        product_intelligence: Product intelligence from exercise 3
        communications: Communications from exercise 4
    
    Returns:
        Dict[str, Any]: Complete case card for GOAs
    """
    
    print("\n🔧 DEBUG: generate_case_card tool called!")
    print(f"Order data keys: {list(order_data.keys())}")
    print(f"Risk assessment keys: {list(risk_assessment.keys())}")
    print(f"Product intelligence keys: {list(product_intelligence.keys())}")
    print(f"Communications keys: {list(communications.keys())}")
    
    order = order_data.get("order", {})
    customer = order_data.get("customer", {})
    risk = risk_assessment.get("risk_assessment", {})
    product = product_intelligence.get("priority_scoring", {})
    comms = communications.get("communications", {})
    
    # Build comprehensive case card
    case_card = {
        "case_id": f"CASE_{order.get('CUSTOMER_ORDER_NUMBER', 'UNKNOWN')}_{datetime.now().strftime('%Y%m%d')}",
        "generated_at": datetime.now().isoformat(),
        "priority_score": product.get("priority_score", 0),
        "risk_level": risk.get("risk_level", "UNKNOWN"),
        
        "delivery_summary": {
            "order_number": order.get("CUSTOMER_ORDER_NUMBER"),
            "customer_name": customer.get("CUSTOMER_NAME"),
            "customer_type": "PRO" if customer.get("PRO_XTRA_MEMBER") else "Standard",
            "delivery_date": order.get("SCHEDULED_DELIVERY_DATE"),
            "delivery_window": f"{order.get('WINDOW_START', '')} - {order.get('WINDOW_END', '')}",
            "destination": customer.get("DESTINATION_ADDRESS"),
            "vehicle_type": order.get("VEHICLE_TYPE"),
            "weight": f"{order.get('WEIGHT', 0)} lbs",
            "special_instructions": customer.get("CUSTOMER_NOTES", "None"),
            "products": order_data.get("products", [])
        },
        
        "risk_analysis": {
            "overall_score": risk.get("overall_risk_score"),
            "risk_scores": risk.get("risk_scores", {}),
            "top_risk_factors": risk.get("risk_factors", [])[:5],
            "weather_impact": risk.get("weather_data", {})
        },
        
        "product_analysis": product_intelligence.get("product_analysis", {}),
        
        "required_actions": {
            "immediate": comms.get("action_summary", {}).get("immediate_actions", []),
            "scheduled": comms.get("action_summary", {}).get("scheduled_actions", []),
            "contingency": comms.get("action_summary", {}).get("contingency_plans", [])
        },
        
        "ready_to_send_messages": {
            "customer": [msg.get("message", "") for msg in comms.get("customer_messages", [])],
            "carrier": comms.get("carrier_instructions", {}).get("alert_message", "")
        },
        
        "alternative_solutions": [
            {
                "option": alt.get("description", alt.get("solution", "")),
                "benefit": alt.get("benefit", ""),
                "approval_needed": alt.get("approval_required", False)
            }
            for alt in comms.get("alternatives", [])[:3]
        ],
        
        "goa_quick_actions": [
            f"📱 Send customer message: {comms.get('customer_messages', [{}])[0].get('send_timing', 'immediate')}",
            f"🚚 Alert carrier: Priority {comms.get('carrier_instructions', {}).get('dispatch_priority', 'STANDARD')}",
            f"⚠️ Monitor: {risk.get('top_risks', 'Standard delivery')}"
        ]
    }
    
    return case_card


# Case card generator agent
case_card_agent = Agent(
    model=GEMINI_MODEL,
    name="case_card_agent",
    description="Generates final delivery case card for GOAs",
    instruction="""\
You are a case card generator agent. You MUST call the generate_case_card tool.

You will receive a JSON with four keys:
- order_data
- risk_assessment  
- product_intelligence
- communications

Call the generate_case_card tool with these four values as parameters.

The tool returns a JSON case card like:
{
  "case_id": "CASE_...",
  "generated_at": "...",
  "priority_score": ...,
  "risk_level": "...",
  "delivery_summary": {...},
  "risk_analysis": {...},
  "product_analysis": {...},
  "required_actions": {...},
  "ready_to_send_messages": {...},
  "alternative_solutions": [...],
  "goa_quick_actions": [...]
}

Return ONLY what the generate_case_card tool returns. Do not wrap it in any other structure.
""",
    tools=[generate_case_card],
    output_key="delivery_case_card"
)


async def run_complete_pipeline(order_number: str):
    """Run the complete delivery intelligence pipeline"""
    
    print("=" * 80)
    print("DELIVERY INTELLIGENCE PIPELINE - COMPLETE SYSTEM")
    print("=" * 80)
    print("\nThis demonstrates the full end-to-end system that helps prevent")
    print("delivery failures by providing actionable intelligence to GOAs.\n")
    
    print(f"🎯 Selected Order: {order_number}")
    print("-" * 80)
    
    # Step 1: Data Collection
    print("\n📊 STEP 1: Collecting delivery data from BigQuery...")
    order_data = await run_data_collection(order_number)
    
    if not order_data:
        print("❌ Failed to collect order data")
        return
        
    print(f"✅ Collected data for order: {order_data.get('order', {}).get('CUSTOMER_ORDER_NUMBER', 'Unknown')}")
    
    # Step 2: Risk Assessment
    print("\n🔍 STEP 2: Assessing delivery risks...")
    await run_risk_assessment(order_data)
    
    # Read the output file directly
    risk_assessment_path = os.path.join(os.path.dirname(__file__), '..', 'exercise_2_risk_assessment', 'risk_assessment_output.json')
    try:
        with open(risk_assessment_path, 'r') as f:
            risk_assessment_result = json.load(f)
        print(f"✅ Risk level: {risk_assessment_result.get('risk_assessment', {}).get('risk_level', 'Unknown')}")
    except FileNotFoundError:
        print(f"❌ Risk assessment output file not found at {risk_assessment_path}")
        return
    
    # Step 3: Product Intelligence
    print("\n📦 STEP 3: Analyzing products and priority...")
    await run_product_intelligence(order_data, risk_assessment_result)
    
    # Read the output file directly
    product_intelligence_path = os.path.join(os.path.dirname(__file__), '..', 'exercise_3_product_intelligence', 'product_intelligence_output.json')
    try:
        with open(product_intelligence_path, 'r') as f:
            product_result = json.load(f)
        print(f"✅ Priority score: {product_result['priority_scoring']['priority_score']}")
    except FileNotFoundError:
        print(f"❌ Product intelligence output file not found at {product_intelligence_path}")
        return
    
    # Step 4: Communication Generation
    print("\n💬 STEP 4: Generating communications...")
    await run_communication_generation(order_data, risk_assessment_result, product_result)
    
    # Read the output file directly
    communication_path = os.path.join(os.path.dirname(__file__), '..', 'exercise_4_communication_generation', 'communication_output.json')
    try:
        with open(communication_path, 'r') as f:
            comm_result = json.load(f)
        print("✅ Communications generated")
    except FileNotFoundError:
        print(f"❌ Communication output file not found at {communication_path}")
        return
    
    # Step 5: Generate Final Case Card
    print("\n📋 STEP 5: Creating delivery case card...")
    
    # Setup for case card generation
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="case_card_generation",
        user_id="user_1",
        session_id="case_session_001"
    )
    
    runner = Runner(
        agent=case_card_agent,
        app_name="case_card_generation",
        session_service=session_service
    )
    
    # Prepare data for case card
    case_data = {
        "order_data": order_data,
        "risk_assessment": risk_assessment_result,
        "product_intelligence": product_result,
        "communications": comm_result
    }
    
    # Create message
    content = types.Content(
        role="user",
        parts=[types.Part(text=json.dumps(case_data))]
    )
    
    # Run case card generation
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    
    try:
        async for event in runner.run_async(
            user_id="user_1",
            session_id="case_session_001",
            new_message=content
        ):
            sys.stderr = old_stderr
            
            if event.is_final_response() and event.author == "case_card_agent":
                if event.content and event.content.parts:
                    response_text = event.content.parts[0].text.strip()
                    
                    # Debug: Show what the agent returned
                    print("\n🔍 DEBUG: Agent response (full):")
                    print(response_text)
                    print("\n🔍 DEBUG: Agent response length:", len(response_text))
                    
                    try:
                        # Remove markdown if present
                        if response_text.startswith("```json"):
                            response_text = response_text[7:]
                        if response_text.endswith("```"):
                            response_text = response_text[:-3]
                            
                        # Parse case card
                        parsed_data = json.loads(response_text.strip())
                        
                        # Handle wrapped response
                        if 'generate_case_card_response' in parsed_data:
                            case_card = parsed_data['generate_case_card_response']
                        else:
                            case_card = parsed_data
                        
                        # Debug: Show parsed structure
                        print("\n🔍 DEBUG: Parsed case card keys:", list(case_card.keys()))
                        
                        # Save to file
                        with open('delivery_case_card.json', 'w') as f:
                            json.dump(case_card, f, indent=2)
                        
                        # Display summary
                        print("\n" + "=" * 80)
                        print("DELIVERY CASE CARD GENERATED")
                        print("=" * 80)
                        
                        print(f"\n📌 Case ID: {case_card.get('case_id', 'Unknown')}")
                        print(f"⚡ Priority Score: {case_card.get('priority_score', 0)}/100")
                        print(f"⚠️  Risk Level: {case_card.get('risk_level', 'Unknown')}")
                        
                        print("\n🎯 Quick Actions for GOA:")
                        for action in case_card.get('goa_quick_actions', []):
                            print(f"   {action}")
                        
                        print("\n📱 Ready-to-Send Customer Message:")
                        customer_msgs = case_card.get('ready_to_send_messages', {}).get('customer', [])
                        if customer_msgs:
                            print(f"   \"{customer_msgs[0][:100]}...\"")
                        
                        print("\n💡 Top Alternative Solutions:")
                        for i, alt in enumerate(case_card.get('alternative_solutions', [])[:2], 1):
                            # Handle different alternative solution formats
                            option = alt.get('option') or alt.get('description', 'Unknown solution')
                            print(f"   {i}. {option}")
                        
                        print("\n✅ Complete case card saved to: delivery_case_card.json")
                        print("\n🎉 Pipeline completed successfully!")
                        
                        return case_card
                        
                    except Exception as e:
                        print(f"Error generating case card: {e}")
                        print(event.content.parts[0].text)
                break
                
            sys.stderr = io.StringIO()
    finally:
        sys.stderr = old_stderr




if __name__ == "__main__":
    import asyncio
    
    print("🚀 DELIVERY INTELLIGENCE PIPELINE")
    print("================================")
    print("\nThis system demonstrates how AI agents can work together to")
    print("prevent delivery failures and improve customer satisfaction.\n")
    
    # For testing, use the default order directly
    order_number = ORDER_NUMBER
    print(f"Using order: {order_number}")
    
    # Run the complete pipeline
    case_card = asyncio.run(run_complete_pipeline(order_number))