import os
from dotenv import load_dotenv
import httpx
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise Exception("❌ Vous devez définir GROQ_API_KEY dans votre .env")

# Désactiver SSL pour bypass proxy entreprise
# Compatible Windows / Python 3.10 / proxy filtrant
transport = httpx.HTTPTransport(verify=False)

client = Groq(
    api_key=api_key,
    http_client=httpx.Client(transport=transport)
)

print("⏳ Test de connexion à Groq…")

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": "Bonjour, ceci est un test API Groq."}
    ]
)

print("\n✅ Connexion réussie ! Réponse du modèle :\n")
print(response.choices[0].message.content)