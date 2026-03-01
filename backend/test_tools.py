import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Test with various syntaxes
models_to_test = ["gemini-2.5-flash", "gemini-2.0-flash"]
tools_to_test = ["google_search_retrieval", "google_search"]

for m_name in models_to_test:
    for t_name in tools_to_test:
        print(f"Testing {m_name} with tool {t_name}...")
        try:
            model = genai.GenerativeModel(model_name=m_name, tools=t_name)
            response = model.generate_content("What matches are happening in the EPL today?")
            print(f"SUCCESS: {response.text[:100]}...")
            break 
        except Exception as e:
            print(f"FAILED: {e}")
    else:
        continue
    break
