import os
from dotenv import load_dotenv

# Load from .env in current directory
load_dotenv()

GEMINI_MODEL = "gemini-2.5-flash"
APP_NAME="delivery_intelligence"


# Access values
PROJECT_ID = os.getenv("PROJECT_ID")
DATASET_ID = os.getenv("DATASET_ID")
LOCATION= os.getenv("LOCATION")

#API KEYS
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Required for VertexAI to function properly
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ["GOOGLE_CLOUD_PROJECT"] =PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] =LOCATION
