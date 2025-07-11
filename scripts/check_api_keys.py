import os
from dotenv import load_dotenv

load_dotenv()

ebird_key = os.getenv("EBIRD_API_KEY", "")
openai_key = os.getenv("OPENAI_API_KEY", "")

print(
    f"eBird API Key configured: {len(ebird_key) > 0 and ebird_key != 'your_ebird_api_key_here'}"
)
print(
    f"OpenAI API Key configured: {len(openai_key) > 0 and openai_key != 'your_openai_api_key_here'}"
)

if len(ebird_key) > 0 and ebird_key != "your_ebird_api_key_here":
    print(f"eBird key length: {len(ebird_key)}")
else:
    print("Please configure EBIRD_API_KEY in .env file")
