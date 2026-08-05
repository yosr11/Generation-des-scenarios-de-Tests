# Représente une user story.id,titre,description;critères d’acceptation
# Un modèle pour représenter une User Story , Avec ses critères d’acceptation , Validé automatiquement

# bibliothèque Python qui sert à :définir des modèles de données ,valider automatiquement les données,convertir les types automatiquement
from pydantic import BaseModel
from typing import List, Optional


class Story(BaseModel):
    """
    Modèle représentant une User Story simplifiée
    """

    id: str
    title: str
    description: Optional[str] = ""
    labels: List[str] = []
    status: Optional[str] = None
    priority: Optional[str] = None
    tests_count: Optional[int] = 0
    tests: Optional[List[str]] = None
    requirement_status: Optional[str] = None

    # acceptance_criteria: List[dict] = []


# PrgppLBW0aKHpuLoN4tagCcQ43A1YWbxhfLT8L
