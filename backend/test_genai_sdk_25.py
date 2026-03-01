import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

model_id = "gemini-2.5-flash"
print(f"Testing {model_id} with google_search tool in google-genai SDK...")

try:
    response = client.models.generate_content(
        model=model_id,
        contents="What matches are happening in the EPL today?",
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    print(f"SUCCESS: {response.text[:100]}...")
except Exception as e:
    print(f"FAILED: {e}")
