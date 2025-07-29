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

## Key Features

- Weather sensitivity detection (lumber, drywall, etc.)
- Vehicle capacity validation
- Access restriction analysis
- Priority scoring algorithm
- Actionable insights generation

## Data Integration

This exercise uses the output from previous exercises:
- Loads order data from Exercise 1 (`collected_order_data.json`)
- Loads risk assessment from Exercise 2 (`risk_assessment_output.json`)
- Combines both to generate intelligent product insights