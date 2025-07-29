# Home Depot Delivery Intelligence System

A comprehensive AI-powered delivery risk assessment and customer communication system that analyzes delivery orders, assesses risks, and generates automated customer communications.

## Overview

This system takes an **Order ID** as input and performs a comprehensive analysis across multiple dimensions:

1. **Parallel Data Retrieval**: Queries 4 BigQuery tables simultaneously to gather customer and order information
2. **Environmental Analysis**: Performs weather and street view analysis for delivery location
3. **Risk Assessment**: Analyzes delivery risks and vehicle optimization recommendations
4. **Communication Generation**: Creates customer emails and case cards with TL;DR summaries
5. **Action Tracking**: Stores results in BigQuery action table for future reference

## System Architecture

### Directory Structure

```
delivery-intelligence-agent/
├── main.py                          # Main application entry point
├── requirements.txt                 # Python dependencies
├── README.md                       # This file
├── .env                           # Environment configuration (create this)
└── workflow/
    ├── __init__.py
    ├── agent_workflows/           # Main workflow orchestrators
    │   ├── delivery_intelligence.py    # Primary delivery analysis workflow
    │   └── query_action_agent.py       # Action table query/update workflow
    ├── agents/                    # Individual AI agents
    │   ├── customer_information.py     # Customer data retrieval
    │   ├── customer_history.py         # Delivery history analysis
    │   ├── order_information.py        # Order details retrieval
    │   ├── weather.py                  # Weather analysis
    │   ├── street_view.py              # Street view analysis
    │   ├── risk.py                     # Risk assessment & vehicle optimization
    │   ├── email.py                    # Customer email generation
    │   ├── case_card.py                # Case card synthesis
    │   ├── action.py                   # Action table updates
    │   └── query_action_table.py       # Action table queries
    ├── tools/                      # Tool implementations
    │   ├── order_information_tool.py   # BigQuery data retrieval tools
    │   ├── weather_tool.py             # Weather API integration
    │   ├── streetview_tool.py          # Street view API integration
    │   ├── action_update_tool.py       # Action table update tools
    │   └── query_action_tool.py        # Action table query tools
    ├── services/                   # Business logic services
    │   ├── check_actions.py            # Action table checking
    │   └── street_image_analysis.py    # Street view image analysis
    ├── mcp/                        # Model Context Protocol
    │   ├── delivery_tools.py           # Tool definitions
    │   ├── mcp_server.py              # MCP server implementation
    │   └── tools_server.py            # Tools server
    └── utils/                      # Utilities
        └── config.py                   # Configuration management
```

## Setup Instructions

### Prerequisites

- Python 3.8+
- Google Cloud Platform account with BigQuery access
- Google Maps API key
- OpenAI API key
- Vertex AI access

### Step 1: Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/traversaal-ai/home-depot-traversaal-workshop.git
   cd delivery-intelligence-agent
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Environment Configuration

Create a `.env` file in the root directory with the following configuration:

```bash
# Vertex AI Configuration
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=<YOUR-GOOGLE-CLOUD-PROJECT-ID>
LOCATION=<YOUR-PROJECT-LOCATION>

# BigQuery Configuration
PROJECT_ID=<YOUR-GOOGLE-CLOUD-PROJECT-ID>
DATASET_ID=<YOUR-BIGQUERY-DATASET-ID>

# API Keys
GOOGLE_API_KEY=<YOUR-GOOGLE-MAPS-API-KEY>
OPENAI_API_KEY=<YOUR-OPENAI-API-KEY>
```

**To create the .env file in your workbench:**

1. Open terminal in your workbench
2. Run: `nano .env`
3. Paste the content above, replacing placeholder values with your actual credentials
4. Save: Press `Ctrl+O`, then `Enter`
5. Exit: Press `Ctrl+X`

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: BigQuery Setup

Ensure your BigQuery dataset contains the following tables:
- `deliveries` - Main delivery orders
- `customers` - Customer information
- `addresses` - Delivery addresses
- `delivery_products` - Order items
- `products` - Product catalog
- `actions` - Action tracking table

## Usage

### Running the System

1. **Start the application**:
   ```bash
   python main.py
   ```

2. **Enter an Order ID** when prompted:
   ```
   Home Depot Delivery Intelligence System
   Enter 'q' to quit the program
   
   Order ID (or 'q' to quit): 12345
   ```

### System Workflow

When you enter an Order ID, the system follows this workflow:

1. **Check Previous Actions**: First checks if the order has been processed before
2. **If New Order**: Runs the full delivery intelligence pipeline
3. **If Existing Order**: Allows querying and updating previous results

### Delivery Intelligence Pipeline

For new orders, the system executes this sequence:

1. **Parallel Data Retrieval** (3 agents run simultaneously):
   - Customer Information Agent
   - Customer History Agent  
   - Order Information Agent

2. **Sequential Analysis**:
   - Weather Analysis Agent
   - Street View Analysis Agent
   - Risk Analyzer Agent
   - Email Generation Agent
   - Case Card Agent
   - Action Storage Agent

### Output Examples

**Case Card Output**:
```
🗂️ Case Card: ORDER 12345
📍 Address & Contact Info
Customer: John Doe
Address: 123 Main St, Anytown, ST 12345
Building Type: Residential
Contact Preference: Email

📅 Delivery History
- 2 previous deliveries to this address
- 1 failed delivery (2024-01-15) - Weather related
- Successful deliveries: 2024-02-01, 2024-03-10

🧠 Risk Summary (TL;DR)
Medium risk delivery due to weather sensitivity and narrow driveway access. 
Recommend smaller vehicle for better maneuverability.

🛠️ Recommendations
- Confirm driveway access with customer
- Consider rescheduling if weather worsens
- Use smaller delivery vehicle

✉️ Crafted Email to Customer
Subject: Delivery Confirmation Needed – Order #12345
Dear John Doe,
We're preparing your delivery, but a few factors may affect a smooth delivery experience...
```

## Key Features

### Risk Assessment Categories

1. **Vehicle Mismatch Risks**:
   - Overloaded vehicle analysis
   - Wrong vehicle type for access
   - Inappropriate vehicle for product type

2. **Weather Risks**:
   - Weather-sensitive products during adverse conditions
   - Safety concerns for drivers/equipment

3. **Access Risks**:
   - Physical access limitations
   - Parking and maneuvering space
   - Gate access, security restrictions

4. **Historical Pattern Risks**:
   - Previous failed deliveries
   - Customer communication issues
   - Timing/scheduling conflicts

### Vehicle Optimization

The system analyzes and recommends optimal vehicle types:
- **Small Van**: ~1,500 lbs, ~200 cubic ft, 1-2 pallets
- **Box Truck**: ~10,000 lbs, ~1,000 cubic ft, 8-10 pallets
- **Flatbed**: ~40,000 lbs, ~2,500+ cubic ft, 20+ pallets
- **Crane Truck**: For items >5,000 lbs
- **Specialized**: For hazardous materials, oversized items

### Risk Levels

- **High**: Delivery must be rescheduled or vehicle changed
- **Medium**: Delivery can proceed with modifications
- **Low**: Optimal setup, proceed as planned

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_GENAI_USE_VERTEXAI` | Enable Vertex AI | Yes |
| `GOOGLE_CLOUD_PROJECT` | Google Cloud Project ID | Yes |
| `LOCATION` | Google Cloud Location | Yes |
| `PROJECT_ID` | BigQuery Project ID | Yes |
| `DATASET_ID` | BigQuery Dataset ID | Yes |
| `GOOGLE_API_KEY` | Google Maps API Key | Yes |
| `OPENAI_API_KEY` | OpenAI API Key | Yes |

### Model Configuration

The system uses Google's Gemini 2.5 Flash model by default. This can be modified in `workflow/utils/config.py`.

##  Troubleshooting

### Common Issues

1. **BigQuery Connection Error**:
   - Verify your Google Cloud credentials
   - Ensure BigQuery API is enabled
   - Check project and dataset permissions

2. **API Key Errors**:
   - Verify Google Maps API key is valid
   - Ensure OpenAI API key is active
   - Check API quotas and billing

3. **Vertex AI Errors**:
   - Verify Vertex AI API is enabled
   - Check project location configuration
   - Ensure proper authentication

### Debug Mode

To enable debug logging, modify the logging configuration in `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Database Schema

### Schema Definition

**Table: customers**
```sql
CUSTOMER_ID INT PRIMARY KEY
CUSTOMER_NAME STRING
PRO_XTRA_MEMBER BOOLEAN
MANAGED_ACCOUNT BOOLEAN
```

**Table: osrs**
```sql
OSR_ID INT PRIMARY KEY
OSR_NAME STRING
```

**Table: addresses**
```sql
ADDRESS_ID INT PRIMARY KEY
DESTINATION_ADDRESS STRING
STREET_VIEW_URL STRING
COMMERCIAL_ADDRESS_FLAG BOOLEAN
BUSINESS_HOURS STRING
STRT_VW_IMG_DSCRPTN STRING
```

**Table: flocs**
```sql
FLOC STRING PRIMARY KEY
FLOC_TYPE STRING
SERVICE_TYPE STRING
FLOC_DELIVERY_ATTEMPTS_LAST_15_DAYS FLOAT
FLOC_OTC_FAILURES_LAST_15_DAYS FLOAT
FLOC_OTC_FAILURE_PCT_LAST_15_DAYS FLOAT
```

**Table: weather**
```sql
WEATHER_ID INT PRIMARY KEY
WTHR_CATEGORY STRING
PRECIPITATION FLOAT
```

**Table: products**
```sql
PRODUCT_ID INT PRIMARY KEY
PRODUCT_DESCRIPTION STRING
```

**Table: risk_features**
```sql
FEATURE_ID INT PRIMARY KEY
FEATURE_NAME STRING
```

**Table: keywords**
```sql
KEYWORD_ID INT PRIMARY KEY
KEYWORD STRING
```

**Table: deliveries**
```sql
DATA_ID STRING PRIMARY KEY
MARKET STRING
SCHEDULED_DELIVERY_DATE DATETIME
DELIVERY_CREATE_DATE DATETIME
VEHICLE_TYPE STRING
CUSTOMER_ORDER_NUMBER STRING
WORK_ORDER_NUMBER STRING
SPECIAL_ORDER BOOLEAN
FLOC STRING -- FK → flocs.FLOC
UNATTENDED_FLAG BOOLEAN
WINDOW_START STRING
WINDOW_END STRING
QUANTITY FLOAT
VOLUME_CUBEFT FLOAT
WEIGHT FLOAT
PALLET FLOAT
DLVRY_RISK_DECILE FLOAT
DLVRY_RISK_BUCKET STRING
DLVRY_RISK_PERCENTILE FLOAT
CUSTOMER_NOTES STRING
CUSTOMER_NOTES_LLM_SUMMARY STRING
HISTORIC_NOTES_LLM_SUMMARY STRING
HISTORIC_NOTES_W_LABELS STRING
RI_GENERATE_DATETIME DATETIME
CUSTOMER_ID INT -- FK → customers
OSR_ID INT -- FK → osrs
ADDRESS_ID INT -- FK → addresses
WEATHER_ID INT -- FK → weather
```

**Table: delivery_products**
```sql
DATA_ID STRING -- FK → deliveries
PRODUCT_ID INT -- FK → products
```

**Table: delivery_risk_features**
```sql
DATA_ID STRING -- FK → deliveries
FEATURE_ID INT -- FK → risk_features
```

**Table: delivery_keywords**
```sql
DATA_ID STRING -- FK → deliveries
KEYWORD_ID INT -- FK → keywords
```

**Table: actions**
```sql
order_id STRING
customer_id INT
customer_name STRING
message STRING
summary STRING
timestamp DATETIME
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is proprietary software for Home Depot delivery operations.

## 🆘 Support

For technical support or questions about the delivery intelligence system, contact the development team.

---

