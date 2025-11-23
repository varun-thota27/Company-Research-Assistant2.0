import os
from dotenv import load_dotenv

load_dotenv()

# Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Gemini (Google GenAI)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Optional: change model names as per your account access
GEMINI_TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
GEMINI_AUDIO_MODEL = os.getenv("GEMINI_AUDIO_MODEL", "gemini-1.5-pro")
