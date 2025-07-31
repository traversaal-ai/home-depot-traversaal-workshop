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

## Learning Outcomes

By completing this exercise, you will be able to:
- Build orchestrated data collection pipelines using multiple ADK agents
- Implement sequential agent workflows for step-by-step data processing
- Execute agents in parallel to optimize data fetching from multiple sources
- Create custom tools that enable sub-agents to perform specialized tasks
- Pass data between agents using the `output_key` pattern for seamless integration

## Output

The pipeline produces `collected_order_data.json` containing all delivery information needed for risk assessment.