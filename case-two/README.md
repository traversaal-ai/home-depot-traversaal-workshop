# Delivery Intelligence Agent Workshop - Google ADK

## Project Overview

This project demonstrates using Google's Agent Development Kit (ADK) to solve a real-world business problem for Home Depot's delivery operations.

## Business Problem

Home Depot experiences significant delivery failures that could be prevented with better intelligence and risk assessment. General Office Associates (GOAs) need actionable insights to:

-   Identify high-risk deliveries before dispatch
-   Provide specific instructions to drivers
-   Reduce avoidable delivery failures
-   Improve customer satisfaction

## Solution Architecture

We're building a Delivery Route Intelligence system using Google ADK that:

1. **Data Collection Pipeline** - Orchestrates multiple agents to gather comprehensive delivery data
2. **Risk Assessment Engine** - Integrates external AI models to assess delivery risks
3. **Actionable Intelligence** - Generates specific recommendations and instructions

## Workshop Structure

The workshop is organized into progressive exercises, each building on the previous:

### Exercise Folders

1. **exercise_0_getting_started/** ✅

    - Introduction to Google ADK concepts
    - Basic agent creation and tool usage
    - Sessions and runners explained

2. **exercise_1_data_collection/** ✅

    - Data orchestration pipeline
    - Sequential → Parallel → Sequential agent pattern
    - Custom BigQuery tools for sub-agents
    - Outputs structured JSON

3. **exercise_2_risk_assessment/** ✅

    - External AI model integration
    - Multi-factor risk analysis using real data from Exercise 1
    - MCP (Model Context Protocol) for weather service integration
    - Risk aggregation and recommendations
    - Outputs structured JSON for downstream use

4. **exercise_3_product_intelligence/** ✅

    - Product characteristic analysis
    - Weather sensitivity detection
    - Vehicle-destination compatibility
    - Priority scoring system (0-100)

5. **exercise_4_communication_generation/** ✅

    - Policy-compliant message generation
    - Customer and carrier communications
    - Alternative solution suggestions
    - Compliance checking

6. **exercise_5_final_integration/** ✅
    - Complete end-to-end pipeline
    - Case card generation
    - Business value demonstration
    - Full system integration

### Documentation (docs/)

-   **REQUIREMENTS_TRACKER.md** - Client requirements and implementation status
-   **SYSTEM_UNDERSTANDING.md** - System architecture documentation
-   **implementation_plan.md** - Technical implementation details
-   **sample_case_output.json/md** - Example outputs

## Key Technical Patterns

1. **Agent Orchestration**

    - Sequential agents for ordered operations
    - Parallel agents for concurrent data fetching
    - Data passing via `output_key`

2. **External Model Integration**

    - Simulating proprietary risk models with Gemini
    - Easily swappable for production models
    - Maintaining specific output formats

3. **Tool Development**

    - Custom function tools for sub-agents
    - Generic, reusable tool design
    - Error handling and fallbacks

4. **MCP (Model Context Protocol) Integration**
    - Using MCPToolset to connect to external services
    - Creating custom MCP servers for specific needs
    - Abstracting external APIs behind standard protocol

## Project Status

-   [x] Exercise 0: Getting Started with ADK
-   [x] Exercise 1: Data Collection Pipeline
-   [x] Exercise 2: Risk Assessment with External Models
-   [x] Exercise 3: Product Intelligence & Priority Scoring
-   [x] Exercise 4: Communication Generation
-   [x] Exercise 5: Final Integration - Complete System

## Recent Updates

### Completed Components

1. **Product Intelligence Pipeline** (product_intelligence.py)

    - Weather-sensitive product detection
    - Vehicle-destination compatibility checking
    - Priority scoring algorithm (0-100 scale)
    - Intelligent insights generation

2. **Communication Generation** (communication_generation.py)

    - Policy-compliant message generation
    - Customer and carrier communications
    - Alternative solution suggestions
    - Compliance checking with auto-correction

3. **All Pipelines Now Output JSON**
    - data_for_intelligence.py → collected_order_data.json
    - risk_assessment.py → risk_assessment_output.json
    - product_intelligence.py → product_intelligence_output.json
    - communication_generation.py → communication_output.json

### Recent Fixes

#### Context Variable Error (Fixed)

-   **Issue**: `KeyError: 'Context variable not found: order_data'`
-   **Solution**: Set session state BEFORE creating Runner

#### Type Annotation Issues (Fixed)

-   **Issue**: ADK doesn't handle `Dict[str, Any] = None` properly
-   **Solution**: Use `Optional[Dict[str, Any]] = None` for optional parameters

## Complete System Vision

The Delivery Intelligence Agent system will provide comprehensive delivery optimization by:

### Core Capabilities (Planned)

1. **Product Intelligence**

    - Summarize product information from SKU descriptions
    - Assess delivery characteristics (vehicle suitability, equipment needs)
    - Identify weather-sensitive products (e.g., drywall on wet days)
    - Flag product-environment mismatches

2. **Delivery-Address Matching**

    - Detect vehicle-destination mismatches
    - Identify oversized orders for residential addresses
    - Analyze street view data for accessibility issues
    - Consider business hours and delivery windows

3. **Smart Communication**

    - Draft customer messages based on risk factors
    - Determine preferred contact modes
    - Ensure policy compliance
    - Provide delivery status updates

4. **Alternative Solutions**
    - Suggest alternative delivery options
    - Recommend carrier changes when needed
    - Propose schedule adjustments
    - Offer equipment recommendations

### Data Sources

-   **BigQuery Tables** - Production dataset with delivery data including:
    -   `delivery_orders` - Core delivery details (weight, volume, vehicle type, risk scores)
    -   `delivery_notes` - Customer notes and historical patterns
    -   `delivery_products` - Product SKUs and descriptions
    -   All data includes weather conditions, street view descriptions, and business hours

## Workshop Complete! 🎉

All exercises have been completed. The workshop demonstrates a complete delivery intelligence system that:

1. **Collects** comprehensive delivery data
2. **Assesses** risks using AI models
3. **Analyzes** products for special requirements
4. **Generates** policy-compliant communications
5. **Produces** actionable case cards for GOAs

The system is ready for testing and demonstration!

## Getting Started

1. **Navigate to an exercise folder:**

    ```bash
    cd exercise_0_getting_started
    ```

2. **Open the notebook:**

    ```bash
    jupyter notebook 0_Getting_Started.ipynb
    ```

3. **For standalone scripts, use the virtual environment:**
    ```bash
    source ../venv/bin/activate
    python script_name.py
    ```

## Development Environment

-   **Platform**: Google Cloud (Vertex AI)
-   **Project**: traversaal-research
-   **Region**: us-central1
-   **Framework**: Google ADK with Gemini models
-   **Data**: BigQuery tables with Home Depot delivery data

## Key Learnings

1. **Built-in tools cannot be used in sub-agents** - Must create custom function tools
2. **Session state timing is critical** - Set state before creating runners
3. **Warning suppression** improves workshop readability
4. **Mock data** enables consistent demonstrations

## For Future Development

When continuing this project:

1. Check that virtual environment is activated
2. Ensure Google Cloud credentials are set
3. Review the latest notebook outputs for context
4. The business goal is reducing delivery failures through intelligence

## Workshop Philosophy

-   Start simple, build complexity progressively
-   Explain concepts before implementation
-   Show production considerations
-   Provide working code with clear patterns
-   Focus on solving real business problems
