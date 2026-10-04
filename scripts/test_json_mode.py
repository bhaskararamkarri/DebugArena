"""Test JSON mode and reasoning controls on Nebius Token Factory for Super and Nano."""
import os
import dotenv
import openai

dotenv.load_dotenv()
client = openai.OpenAI(base_url="https://api.studio.nebius.ai/v1", api_key=os.getenv("NEBIUS_API_KEY"))

prompt = "You are a coding agent. Return ONLY JSON action: {\"type\": \"submit\"}"

# Test 1: JSON mode on Super
try:
    res_super = client.chat.completions.create(
        model="nvidia/nemotron-3-super-120b-a12b",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=500,
    )
    print("Super response_format=json_object SUCCESS:", repr(res_super.choices[0].message.content[:100]))
except Exception as e:
    print("Super response_format=json_object FAILED:", e)

# Test 2: JSON mode on Nano
try:
    res_nano = client.chat.completions.create(
        model="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=500,
    )
    print("Nano response_format=json_object SUCCESS:", repr(res_nano.choices[0].message.content[:100]))
except Exception as e:
    print("Nano response_format=json_object FAILED:", e)
