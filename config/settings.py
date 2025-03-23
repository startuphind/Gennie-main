import os
from dotenv import load_dotenv

# Load .env file if exists
load_dotenv()

# Environment variables or default values
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY", "")

# AZURE DOC INTELLIGENCE STUP
AZURE_DOCUMENT_INTELLIGENCE_API_ENDPOINT = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_ENDPOINT","")
AZURE_DOCUMENT_INTELLIGENCE_API_KEY = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_API_KEY", "")