# Home Depot Traversaal Workshop
Welcome to the official repository for the Home Depot Traversaal Workshop, a hands-on teaching session that explores the evolution of AI agents—from simple instruction-followers to fully autonomous multi-agent systems. This workshop is tailored for engineers and researchers interested in agentic systems, Google Cloud ADK, and enterprise LLM deployments.

## 🎓 Part 1: Teaching + Hands-On Demos

We’ll progressively explore 4 levels of agent capability, with live coding and demonstrations:

| **Level**   | **Description**                                                              |
|-------------|-------------------------------------------------------------------------------|
| **Level 1** | Basic LLM Agents (single-agent, single-turn)                                 |
| **Level 2** | Agents + Tools (function-calling with context)                               |
| **Level 3** | Agents + Tools + Reasoning (multi-step logic, error handling, memory)        |
| **Level 4** | Multi-Agent Systems (A2A) with MCP integration                                |

## Case Studies
### 🛡️ Case 1: Secure SQL Assistant with Google ADK and Cloud
A multi-agent architecture for secure natural language-to-SQL conversion and execution, with privacy-preserving output.

Key Features:
- Judge Agent: Blocks unsafe prompts using advanced rule-based injection detection.
- SQL Agent: Converts natural queries to SQL and executes them securely on BigQuery.
- Masking Agent: Redacts sensitive information using Google Cloud DLP.

### 📦 Case 2: Delivery Route Intelligence Agent
Empowers GOAs (delivery associates) to reduce avoidable delivery failures by generating intelligent, order-specific insights.

Capabilities
- Risk-aware TL;DR summaries for each delivery
- Personalized customer messages
- Auto-generated recommendations
- Spatial + historical + contextual reasoning
- All actions logged with minimal manual input

### 📞 Case 3: Memory & Policy Enhanced Contact Center Agent
Combines memory, policy retrieval, and conversation understanding for hyper-personalized support.
Components
- Memory Assistant: Remembers customer data across sessions for contextual help.
- Policy RAG: Dynamically generated from transcripts to answer questions without hardcoding logic trees.
- Multi-turn Reasoning: Understands, recalls, and resolves complex customer queries.
