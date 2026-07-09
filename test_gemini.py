import os
from dotenv import load_dotenv
from google import genai

load_dotenv()  # reads .env, loads GOOGLE_API_KEY into environment

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found — check your .env file")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash", contents="Say hello in one short sentence."
)

print("Gemini response:")
print(response.text)
