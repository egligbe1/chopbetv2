import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-1.5-flash") # Try 1.5-flash as it usually has higher limits
try:
    response = model.generate_content("Say hello")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
