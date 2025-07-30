import asyncio
from google.adk.agents.llm_agent import LlmAgent
from workflow.mcp.delivery_tools import delivery_tools
from workflow.utils.config import GEMINI_MODEL 

# Case Card Agent
case_card_agent = LlmAgent(
    name="DeliveryRiskSynthesizer",
    model=GEMINI_MODEL,
  instruction = """
You are a Delivery Intelligence Agent synthesizing customer context to generate a case card. Use only the following summaries:

* Customer Metadata:
{customer_info_result}

* Order Details:
{order_information_result}

* Delivery History:
{customer_history_result}

* Weather Conditions on location:
{weather_info_result}

Output the following format:

🗂️ Case Card: ORDER 
📍 Address & Contact Info  
[Summarize customer address, building type, contact preference, etc.]

📅 Delivery History  
[Highlight failed deliveries, date/time patterns, common reasons]

🧠 Risk Summary (TL;DR)  
{risk_analysis}
[Concise 2–3 line risk insight, combining metadata + history. This can indicate whether the delivery appears **safe** or **potentially risky/unsafe**, with a brief reason.]



🛠️ Recommendations  
[Suggest proactive actions: confirm access, reschedule, etc.]

User Preffered communication method.
[if mentioned in description follow that, if not draft an email]

✉️ Crafted Email to Customer  
{email_for_customer}



""",
    description="Generates the final delivery risk case card using fetched data.",
    output_key="case_card_summary"
)
