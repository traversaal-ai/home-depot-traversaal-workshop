# Secure SQL Assistant with Google ADK and Cloud
A multi-agent system using Google ADK, Vertex AI, and BigQuery to evaluate, execute, and mask SQL queries with security and privacy in mind.

## Features
- Judge Agent: Uses an extensive rule-based SQL injection detector to block harmful prompts.
- SQL Agent: Generates and executes SQL queries against a Walmart sales dataset using a secure MCP toolset and BigQuery backend.
- Masking Agent: Detects and anonymizes Personally Identifiable Information (PII) using Google Cloud DLP.

## Getting Started
### Set Data in BigQuery Through UI

**Step 1: Download from Hugging Face**
- Go to Hugging Face: [Walmart Sales Dataset](https://huggingface.co/datasets/large-traversaal/Walmart-sales/tree/main)
- Click on the **"Files and versions"** tab
- Download the `train.csv` file and save it to your computer

**Step 2: Upload to BigQuery**
- Go to [BigQuery Console](https://console.cloud.google.com/bigquery)
- Select your project
- Click **"Create Dataset"**
- Set a Dataset ID (e.g., `walmart_sales`) and create it
- Click the newly created dataset and then click **"Create Table"**
- Choose **"Upload"** as the source
- Select your downloaded `train.csv` file
- Name your table (e.g., `sales_table`)
- Click **"Create Table"**

### Enable API
Enable `Google Cloud DLP` API on Google Cloud [Link](https://cloud.google.com/sensitive-data-protection/docs/reference/rest).

### Install Dependencies in your Google Cloud Workbench
for python 3.10 or above
- git clone "https://github.com/traversaal-ai/home-depot-traversaal-workshop.git"
- cd "home-depot-traversaal-workshop"
- cd "Case One: Connecting ADK to GCP"
```python
pip install -r requirements.txt
```

### Update the files
Go into `test_client.py` and update with your own key:
```python
os.environ["GOOGLE_CLOUD_PROJECT"] = "<PROJECT_ID>"

PROJECT_ID = "<PROJECT_ID>"
DATASET_ID = "<DATASET_NAME>" # walmart_sales
TABLE_ID = "<DATASET_TABLE>" # sales_table

```

Now go into `test_server.py` and update with your own Google Cloud details:
```python
os.environ["GOOGLE_CLOUD_PROJECT"] = "<PROJECT_ID>"

PROJECT_ID = "<PROJECT_ID>"
DATASET_ID = "<DATASET_NAME>" # walmart_sales
TABLE_ID = "<DATASET_TABLE>" # sales_table
```

### Run the Client
```python
python test_client.py
```
You will be prompted to enter a natural language query (Try, "What is the total sales for Dept 1 in Store 1?").

## Core Components
Security Evaluation:
- Uses pattern matching and decoding to detect SQL injection, XSS, obfuscated code, and more.
- Implemented via evaluate_prompt() in utils.py.

SQL Execution
- Uses MCPToolset and a query_data tool to securely run SQL queries on BigQuery 

Data Masking
- Uses Google DLP to redact sensitive information such as names, phone numbers, and credit card data

## Architecture Overview
![a2a_mcp](https://github.com/user-attachments/assets/9d796fdd-30fe-446c-a7b3-c6a1e83e329a)


## File Structure
```bash
├── test_client.py        # Main orchestration: security → SQL → masking
├── test_server.py        # MCP server exposing SQL tools to the agent
├── utils.py              # Security evaluator and DLP masking logic
├── requirements.txt      # All required dependencies
└── README.md             # You are here
```
