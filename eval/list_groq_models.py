"""List Groq models, highlighting vision/llama-4 ones."""
import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

key = os.getenv("GROQ_API_KEY")
resp = httpx.get(
    "https://api.groq.com/openai/v1/models",
    headers={"Authorization": f"Bearer {key}"},
    verify=False,
    timeout=15.0,
)
data = resp.json()

print("== Modèles llama-4 / vision / maverick / scout ==")
for m in data.get("data", []):
    mid = m["id"]
    low = mid.lower()
    if any(k in low for k in ("llama-4", "vision", "maverick", "scout")):
        print(f"  - {mid}")

print("\n== Tous les modèles ==")
for m in sorted(data.get("data", []), key=lambda x: x["id"]):
    print(f"  - {m['id']}")
