"""Modèles Pydantic pour Agent 1.5 — QA Business Modeling."""

from typing import List, Literal
from pydantic import BaseModel, Field


class BusinessGoal(BaseModel):
    """Intention utilisateur de haut niveau — ce que l'acteur veut accomplir."""

    id: str  # BG-1, BG-2...
    label: str  # Titre court (ex: "Consulter les processus disponibles")
    description: str  # Ce que l'acteur veut accomplir et pourquoi
    actors: List[str] = Field(default_factory=list)
    priority: Literal["haute", "moyenne", "basse"] = "moyenne"


class BusinessWorkflow(BaseModel):
    """Parcours end-to-end permettant d'atteindre un BusinessGoal."""

    id: str  # BW-1, BW-2...
    label: str  # Nom du parcours (ex: "Consultation et sélection d'un processus")
    linked_goal_id: str  # Référence au BusinessGoal (ex: "BG-1")
    trigger: str  # Ce qui déclenche le workflow
    actors_involved: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)  # Étapes ordonnées du parcours
    success_criteria: List[str] = Field(default_factory=list)  # État final attendu
    alternative_paths: List[str] = Field(
        default_factory=list
    )  # Branches / cas alternatifs


class BusinessModelingResult(BaseModel):
    """Résultat complet de l'Agent 1.5 pour une story."""

    story_id: str
    business_goals: List[BusinessGoal] = Field(default_factory=list)
    business_workflows: List[BusinessWorkflow] = Field(default_factory=list)
    modeling_notes: str = ""
