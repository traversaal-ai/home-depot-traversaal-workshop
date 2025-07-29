# Exercise 2: Risk Assessment with External Models

This exercise shows how to integrate external AI models and assess delivery risks using real data from Exercise 1.

## Data Pipeline Integration

**Important**: This exercise builds on Exercise 1's output:
- **Input**: Reads `../exercise_1_data_collection/collected_order_data.json`
- **Output**: Produces `risk_assessment_output.json`

If you haven't run Exercise 1 yet, the script will use fallback data.

## Contents

- **2_Risk_Assessment.ipynb** - Interactive notebook for the exercise
- **risk_assessment.py** - Complete risk assessment implementation with MCP
- **weather_mcp_server.py** - MCP server providing weather risk assessment
- **risk_assessment_output.json** - Generated output

## What You'll Build

A risk assessment pipeline that:
1. Loads real order data from Exercise 1
2. Calls external AI models (using pre-calculated BigQuery risk scores)
3. Performs multi-factor risk analysis (weather, customer, route)
4. Uses MCP to integrate weather service
5. Aggregates risks into actionable insights

## Key Patterns

- External model integration
- Model Context Protocol (MCP) usage
- Parallel risk assessment
- Structured JSON output for downstream use

## MCP Integration

This exercise introduces MCP (Model Context Protocol) for connecting to external services like weather APIs in a standardized way.