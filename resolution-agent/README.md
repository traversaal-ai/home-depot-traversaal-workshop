# Home Depot Resolution Agent

This repository provides an end-to-end workflow to build and test an AI-powered **Home Depot Resolution Agent**.  
It processes transcripts, builds a **RAG (Retrieval Augmented Generation)** database using Qdrant, and enables interactive testing of the assistant.


## Steps to Run

### **Step 1: Install Requirements**
Create a virtual environment and install dependencies:

```bash
pip install -r requirements.txt
```

## Step 2: Generate JSON from Transcripts
Run the llm-as-judge.py script to analyze transcripts and create structured JSON files in the data/ folder:
```bash
python llm-as-judge.py
```

## Step 3: Split JSON into Flat Structure
Run the json_split.py script to flatten the JSON output from Step 2:
```bash
python json_split.py
```

## Step 4: Build RAG Vector Database
Open rag.ipynb notebook to:
- Generate embeddings
- Create a Qdrant vector database (qdrant_db)
- Populate it with flattened JSON data

IMPORTANT: After building the database, shut down the Jupyter kernel to free resources.

If you already have a qdrant_db folder, you can skip Steps 2, 3, and 4.

## Step 5: Configure Environment
Set environment variables and project IDs in create.py.

## Step 6: Run Test Client
Run the interactive test client:
```bash
python test_client.py
```

## Key Files
test_client.py
This script initializes:
- Vertex AI and Qdrant-based RAG
- Session memory and sub-agents
- Multi-step reasoning pipeline for customer support

Key features:
- Retrieves order details using MCP toolset
- Uses RAG for policy retrieval
- Delegates actions (returns, delivery changes, coupon application) to a sub-agent
- Supports interactive Q&A in the console
