# Exercise 3: Product Intelligence & Priority Scoring

This exercise builds intelligent product analysis and delivery prioritization.

## Contents

- **3_Product_Intelligence.ipynb** - Interactive notebook for the exercise
- **product_intelligence.py** - Product analysis implementation
- **product_intelligence_output.json** - Sample output

## What You'll Build

A product intelligence system that:
1. Analyzes product characteristics from SKU descriptions
2. Detects weather-sensitive items
3. Checks vehicle-destination compatibility
4. Calculates priority scores (0-100)
5. Generates intelligent insights

## Learning Outcomes

By completing this exercise, you will be able to:
- Build AI agents that analyze product characteristics from SKU descriptions
- Implement weather sensitivity detection for products like lumber and drywall
- Validate vehicle-destination compatibility using intelligent matching algorithms
- Design and calculate priority scoring systems (0-100 scale) based on multiple factors
- Generate actionable insights that combine data from multiple previous pipeline stages

## Data Integration

This exercise uses the output from previous exercises:
- Loads order data from Exercise 1 (`collected_order_data.json`)
- Loads risk assessment from Exercise 2 (`risk_assessment_output.json`)
- Combines both to generate intelligent product insights