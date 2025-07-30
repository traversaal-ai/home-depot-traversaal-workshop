# Exercise 1: Data Collection Pipeline

This exercise demonstrates building an orchestrated data collection pipeline using ADK agents.

## Contents

- **1_Data_For_Intelligence.ipynb** - Interactive notebook for the exercise
- **data_for_intelligence.py** - Standalone Python implementation

## What You'll Build

A data orchestration pipeline that:
1. Fetches order data from BigQuery
2. Retrieves customer information in parallel
3. Collects product details
4. Assembles everything into structured JSON output

## Key Patterns

- Sequential agent orchestration
- Parallel agent execution
- Custom tool creation for sub-agents
- Data passing between agents using `output_key`

## Output

The pipeline produces `collected_order_data.json` containing all delivery information needed for risk assessment.