"""Test Nebius Token Factory connectivity for Super and Nano."""
import os
import dotenv
import openai

dotenv.load_dotenv()
client = openai.OpenAI(base_url="https://api.studio.nebius.ai/v1", api_key=os.getenv("NEBIUS_API_KEY"))

# Test Nano
try:
    res_nano = client.chat.completions.create(
        model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        messages=[{"role": "user", "content": "Respond with exact JSON: {\"type\": \"submit\"}"}],
        temperature=0.2,
        max_tokens=1500,
    )
    msg = res_nano.choices[0].message
    print("Nebius Nano content:", repr(msg.content))
    print("Nebius Nano reasoning:", repr(msg.reasoning[:100] if msg.reasoning else None))
except Exception as e:
    print("Nebius Nano error:", e)

# Test Super
try:
    res_super = client.chat.completions.create(
        model="nvidia/nemotron-3-super-120b-a12b",
        messages=[{"role": "user", "content": "Respond with exact JSON: {\"type\": \"submit\"}"}],
        temperature=0.2,
        max_tokens=50,
    )
    print("Nebius Super response:", res_super.choices[0].message.content)
except Exception as e:
    print("Nebius Super error:", e)
