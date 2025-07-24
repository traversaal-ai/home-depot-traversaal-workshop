# Secure SQL Assistant with Google ADK and Cloud
A multi-agent system using Google ADK, Vertex AI, and BigQuery to evaluate, execute, and mask SQL queries with security and privacy in mind.

## Features
- Security Evaluation Agent: Uses an extensive rule-based SQL injection detector to block harmful prompts.
- SQL Agent: Generates and executes SQL queries against a Walmart sales dataset using a secure MCP toolset and BigQuery backend.
- Masking Agent: Detects and anonymizes Personally Identifiable Information (PII) using Google Cloud DLP.
- End-to-End Workflow: All agents run sequentially in isolated sessions with error handling and real-time logging.

## Getting Started
### Install Dependencies
```python
pip install -r requirements.txt
```
