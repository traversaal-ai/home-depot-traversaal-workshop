# Secure SQL Assistant with Google ADK and Cloud
A multi-agent system using Google ADK, Vertex AI, and BigQuery to evaluate, execute, and mask SQL queries with security and privacy in mind.

## Features
- Judge Agent: Uses an extensive rule-based SQL injection detector to block harmful prompts.
- SQL Agent: Generates and executes SQL queries against a Walmart sales dataset using a secure MCP toolset and BigQuery backend.
- Masking Agent: Detects and anonymizes Personally Identifiable Information (PII) using Google Cloud DLP.

## Getting Started
### Install Dependencies
```python
pip install -r requirements.txt
```
### Set Environment Variables
Replace `<PROJECT_ID>`, `<DATASET_NAME>`, and `<DATASET_TABLE>` in the files with your actual Google Cloud values.

#### Run the Client
```python
python test_client.py
```
You will be prompted to enter a natural language query (Try, "What is the average weekly sales for Dept 1 in Store 1?").

## Core Components
Security Evaluation:
- Uses pattern matching and decoding to detect SQL injection, XSS, obfuscated code, and more.
- Implemented via evaluate_prompt() in utils.py.

SQL Execution
- Uses MCPToolset and a query_data tool to securely run SQL queries on BigQuery 

Data Masking
- Uses Google DLP to redact sensitive information such as names, phone numbers, and credit card data

## File Structure
```bash
├── test_client.py        # Main orchestration: security → SQL → masking
├── test_server.py        # MCP server exposing SQL tools to the agent
├── utils.py              # Security evaluator and DLP masking logic
├── requirements.txt      # All required dependencies
└── README.md             # You are here
```
