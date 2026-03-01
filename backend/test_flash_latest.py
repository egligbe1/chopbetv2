import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model_name = "gemini-flash-latest"
print(f"Testing {model_name} with google_search_retrieval...")
try:
    model = genai.GenerativeModel(
        model_name=model_name,
        tools=[{"google_search_retrieval": {}}]
    )
    response = model.generate_content("What matches are happening in the EPL today?")
    print(f"SUCCESS: {response.text[:100]}...")
except Exception as e:
    print(f"FAILED: {e}")
