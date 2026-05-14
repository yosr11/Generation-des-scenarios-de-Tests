#Gère les variables d’environnement (.env).
#Centralise les chemins JSON ou les credentials API.

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    STORIES_PATH = os.getenv("STORIES_PATH", "app/data/stories.json")

settings = Settings()

# S'assurer que le dossier data existe
Path("app/data").mkdir(parents=True, exist_ok=True)