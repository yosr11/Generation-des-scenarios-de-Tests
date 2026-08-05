"""Modèles Pydantic pour les réponses Agent 5 (Rapport Final)."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ReportStory(BaseModel):
    """Section : Synthèse de la User Story."""

    story_id: str = Field(..., description="Identifiant Jira de la story")
    story_title: str = Field(..., description="Titre/résumé de la story")
    story_type: str = Field(
        ..., description="Type (functional, technical, poc_or_study, etc.)"
    )
    actors: List[str] = Field(default_factory=list, description="Acteurs identifiés")
    actions: List[str] = Field(default_factory=list, description="Actions principales")
    business_rules: List[str] = Field(default_factory=list, description="Règles métier")
    technical_scope: List[str] = Field(
        default_factory=list, description="Périmètre technique (si applicable)"
    )


class ReportTestCase(BaseModel):
    """Représentation simplifiée d'un cas de test pour le rapport."""

    test_name: str
    objective: str
    scenario_type: str = Field(..., description="NOM, ALT, ou EXC")
    priority: str = Field(..., description="High, Medium, Low")
    step_count: int = Field(..., description="Nombre d'étapes")


class ReportTestSuite(BaseModel):
    """Section : Suite de Tests Générée."""

    total_tests: int = Field(..., description="Nombre total de cas de test")
    nom_count: int = Field(..., description="Nombre de tests NOM (nominaux)")
    alt_count: int = Field(..., description="Nombre de tests ALT (alternatifs)")
    exc_count: int = Field(..., description="Nombre de tests EXC (exceptions)")
    high_priority_count: int = Field(..., description="Nombre de tests haute priorité")
    tests_summary: List[ReportTestCase] = Field(
        default_factory=list, description="Liste simplifiée des tests"
    )


class ReportCoverageMetrics(BaseModel):
    """Section : Indicateurs de Couverture."""

    coverage_rate: float = Field(
        ..., ge=0, le=100, description="Taux de couverture (%)"
    )
    total_testable_points: int = Field(
        ..., description="Nombre total de points testables"
    )
    covered_points: int = Field(..., description="Nombre de points couverts")
    uncovered_points: List[str] = Field(
        default_factory=list, description="Points non couverts"
    )
    coverage_status: str = Field(
        ..., description="EXCELLENT (>85%), GOOD (70-85%), FAIR (50-70%), POOR (<50%)"
    )


class ReportQualityIssue(BaseModel):
    """Issue détectée lors de la validation."""

    issue_type: str = Field(..., description="duplicate, ambiguity, uncovered, etc.")
    severity: str = Field(..., description="critical, warning, info")
    description: str = Field(..., description="Description lisible")
    affected_tests: List[str] = Field(
        default_factory=list, description="Noms de tests affectés"
    )
    recommendation: str = Field(default="", description="Recommandation de correction")


class ReportQualityAssurance(BaseModel):
    """Section : Résultats Validation / QA."""

    validation_status: str = Field(..., description="VALID, PARTIALLY_VALID, INVALID")
    duplicate_pairs: int = Field(
        ..., description="Nombre de paires dupliquées détectées"
    )
    ambiguity_count: int = Field(..., description="Nombre d'étapes ambiguës détectées")
    issues: List[ReportQualityIssue] = Field(
        default_factory=list, description="Détail des issues"
    )
    llm_quality_score: Optional[int] = Field(
        default=None, ge=0, le=10, description="Score qualitatif global (0-10)"
    )
    llm_quality_summary: Optional[str] = Field(
        default="", description="Feedback qualitatif du LLM"
    )


class ReportRecommendation(BaseModel):
    """Recommandation pour les prochaines étapes."""

    priority: str = Field(..., description="critical, high, medium, low")
    action: str = Field(..., description="Action recommandée")
    rationale: str = Field(..., description="Justification")


class ReportExecutiveSummary(BaseModel):
    """Résumé exécutif synthétique et lisible."""

    overall_status: str = Field(
        ..., description="APPROVED, REQUIRES_REVIEW, NEEDS_REWORK"
    )
    key_findings: List[str] = Field(
        default_factory=list, description="Findings principaux (max 5)"
    )
    next_steps: List[str] = Field(
        default_factory=list, description="Prochaines étapes recommandées"
    )


class Agent5Report(BaseModel):
    """Rapport final complet généré par Agent 5."""

    story_id: str = Field(..., description="Identifiant Jira")
    report_title: str = Field(..., description="Titre du rapport")
    report_version: str = Field(default="1.0", description="Numéro de version")
    generated_timestamp: str = Field(
        ..., description="ISO 8601 timestamp de génération"
    )

    # Sections principales
    executive_summary: ReportExecutiveSummary = Field(
        ..., description="Résumé exécutif"
    )
    story_summary: ReportStory = Field(..., description="Synthèse de la story")
    test_suite: ReportTestSuite = Field(..., description="Suite de tests générée")
    coverage_metrics: ReportCoverageMetrics = Field(
        ..., description="Métriques de couverture"
    )
    quality_assurance: ReportQualityAssurance = Field(
        ..., description="Résultats validation/QA"
    )

    # Recommandations
    recommendations: List[ReportRecommendation] = Field(
        default_factory=list, description="Recommandations pour amélioration"
    )

    # Métadonnées
    agent_versions: dict = Field(
        default_factory=dict,
        description="Versions des agents utilisés (agent1_version, agent3_version, etc.)",
    )
    processing_notes: List[str] = Field(
        default_factory=list, description="Notes techniques de traitement"
    )


class Agent5ReportRequest(BaseModel):
    """Requête pour génération rapport (body optionnel du POST)."""

    output_format: str = Field(
        default="json", description="Format output: json, markdown"
    )


class Agent5ReportResponse(BaseModel):
    """Réponse contenant le rapport généré."""

    status: str = Field(..., description="success, error, partial")
    report: Optional[Agent5Report] = Field(
        default=None, description="Rapport structuré"
    )
    report_markdown: Optional[str] = Field(
        default=None, description="Version markdown (si demandée)"
    )
    error_message: Optional[str] = Field(
        default=None, description="Message d'erreur si applicable"
    )
    generation_duration_ms: int = Field(..., description="Temps de génération en ms")
