# Bilan Mi-Stage — Agent IA de Test Logiciel
## Projet de Fin d'Études — Mois 1 à 3

---

## 1. Contexte du Projet

**Objectif :** Concevoir et développer un système multi-agents basé sur des LLMs (Large Language Models) capable d'analyser automatiquement des user stories Jira et de générer des tests manuels structurés.

**Stack technique :**
- **Backend :** Python, FastAPI
- **LLMs :** Groq API (Qwen3-32B, GPT-OSS-20B, GPT-OSS-120B, Llama4-Scout-17B)
- **RAG :** ChromaDB + Sentence-Transformers (all-MiniLM-L6-v2)
- **Base de données :** SQLite (WAL mode)
- **Source de données :** Jira REST API

---

## 2. Architecture Réalisée

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI (app/main.py)                 │
├─────────────────────────────────────────────────────────┤
│  API Layer (app/api/)                                   │
│  ├── routes_stories.py    → Récupération stories Jira   │
│  ├── routes_epic.py       → Gestion des epics           │
│  ├── routes_analysis.py   → Analyse des stories         │
│  ├── routes_documents.py  → Collecte docs + indexation  │
│  ├── routes_db.py         → Requêtes base de données    │
│  └── manual_test_generation.py → Génération tests       │
├─────────────────────────────────────────────────────────┤
│  Services (app/services/)                               │
│  ├── jira_service.py           → Client REST Jira       │
│  ├── epic_service.py           → Gestion epics Jira     │
│  ├── story_analysis_service.py → Agent 1 : Analyse      │
│  ├── manual_test_generator.py  → Agent 2 : Tests        │
│  ├── manual_test_strategy.py   → Décision stratégie     │
│  ├── manual_test_validator.py  → Validation tests       │
│  ├── llm_client.py             → Client Groq API        │
│  ├── rag_service.py            → Pipeline RAG           │
│  └── document_collector.py     → Collecte documents     │
├─────────────────────────────────────────────────────────┤
│  Data Layer                                             │
│  ├── models/     → Schémas Pydantic (7 modèles)        │
│  ├── repositories/ → CRUD SQLite (3 repositories)      │
│  ├── db/         → Connexion + schéma SQLite            │
│  ├── prompts/    → Prompts LLM (2 prompts principaux)   │
│  └── utils/      → Nettoyage, extraction JSON, docs     │
├─────────────────────────────────────────────────────────┤
│  Évaluation (eval/)                                     │
│  ├── confusion_matrix_eval.py  → Classification         │
│  ├── judge_runner.py           → LLM-as-Judge           │
│  ├── judge_prompt.py           → Prompt du juge          │
│  └── evaluate_extraction.py   → Extraction F1           │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Agent 1 — Analyse de User Stories

### 3.1 Fonctionnement

L'Agent 1 reçoit une user story Jira (description + critères d'acceptation) et produit une analyse structurée contenant 14 champs :

| Champ | Description |
|-------|-------------|
| `story_type` | Classification : functional, technical, non_functional, poc_or_study, documentation, invalid_or_too_weak |
| `actors` | Acteurs/rôles mentionnés dans la story |
| `actions` | Comportements concrets décrits |
| `business_rules` | Contraintes métier |
| `technical_scope` | Composants techniques (si story technique) |
| `testable_points` | Assertions vérifiables |
| `user_flows` | Parcours utilisateur étape par étape |
| `acceptance_criteria_explicit` | Critères d'acceptation explicites |
| `acceptance_criteria_inferred` | Critères déduits du contexte |
| `recommended_test_type` | manual ou automated |
| `clarification_questions` | Questions pour lever les ambiguïtés |
| `analysis_reason` | Justification de la classification |

### 3.2 Pipeline de traitement

1. **Récupération** : Jira REST API → story brute
2. **Nettoyage** : Suppression HTML/wiki markup, extraction des références (URLs, clés Jira, utilisateurs de test)
3. **Enrichissement** : Contexte epic, flags heuristiques (JDD, technical signals)
4. **RAG (optionnel)** : Recherche sémantique dans les documents de l'epic via ChromaDB
5. **Analyse LLM** : Envoi au modèle avec prompt spécialisé (800+ lignes)
6. **Validation** : Parsing JSON, normalisation des enums FR→EN, validation Pydantic
7. **Persistance** : Sauvegarde en SQLite

### 3.3 Comparaison et choix du modèle LLM

Quatre modèles ont été testés et comparés sur le même jeu de stories pour sélectionner le meilleur candidat :

| Modèle | Fournisseur | Taille | Observations |
|--------|-------------|--------|-------------|
| Qwen3-32B | Groq | 32B | Bonne qualité mais lent, limites TPM restrictives |
| GPT-OSS-20B | Groq | 20B | Rapide mais extraction parfois incomplète |
| GPT-OSS-120B | Groq | 120B | Très bon en JSON structuré, coût élevé en tokens |
| **Llama 4 Scout 17B** | Groq | 17B | **Retenu** — meilleur compromis qualité/vitesse/coût |

**Critères de sélection :**
- Qualité de la classification `story_type` (accuracy)
- Fidélité de l'extraction des attributs (actors, actions, business_rules, etc.)
- Respect du format JSON de sortie (taux de parsing réussi au 1er essai)
- Temps de réponse moyen par story
- Respect des limites TPM (tokens par minute) du tier gratuit Groq

**Résultat :** Llama 4 Scout 17B a été retenu comme modèle principal pour les deux agents car il offre le meilleur équilibre entre qualité d'extraction, rapidité et stabilité du format JSON.

- Temperature : 0.2
- Retry automatique avec backoff exponentiel en cas de rate limit

---

## 4. Agent 2 — Génération de Tests Manuels

### 4.1 Fonctionnement

L'Agent 2 prend l'analyse produite par l'Agent 1 et génère des cas de test manuels structurés.

**Sortie par test case :**
- `test_name` : Nom du test
- `objective` : Objectif clair
- `preconditions` : Prérequis
- `scenario_type` : NOM (nominal), ALT (alternatif), EXC (exception)
- `priority` : High, Medium, Low
- `steps[]` : Liste d'étapes (action + données + résultat attendu)

### 4.2 Caractéristiques

- **Prompts spécialisés par type de story** : functional, POC/study, documentation, technical
- **Auto-réparation JSON** : Si le LLM produit un JSON malformé, un second appel LLM reformate la réponse
- **Validation structurelle** : Min 3 steps, max 15, verbe à l'infinitif, pas de "Vérifier" en action
- **Normalisation des enums** : "manuel" → "manual", "généré" → "generated"
- **Gestion TPM** : Ajustement dynamique du max_tokens pour respecter les limites Groq

### 4.3 Stratégie de décision

Avant de générer, `manual_test_strategy.py` décide si la story justifie des tests manuels :
- Stories `invalid_or_too_weak` → pas de génération
- Stories sans description → pas de génération
- Stories techniques pures → évaluation au cas par cas

---

## 5. Couche RAG (Retrieval-Augmented Generation)

### 5.1 Architecture

- **Embedding** : all-MiniLM-L6-v2 (Sentence-Transformers)
- **Vector Store** : ChromaDB (persisté localement)
- **Chunking** : 500 caractères, overlap 100 caractères

### 5.2 Pipeline

1. **Collecte** : Récupération des pièces jointes Jira (PDF, DOCX, TXT) — story + epic + issues liées
2. **Extraction** : Conversion en texte (pdfplumber, python-docx)
3. **Indexation** : Chunking → embedding → stockage ChromaDB (une collection par epic)
4. **Retrieval** : Recherche sémantique top-k pour enrichir le prompt de l'Agent 1/2

---

## 6. Évaluation de l'Agent 1

### 6.1 Méthode 1 — Matrice de Confusion (Classification)

**Objectif :** Évaluer la qualité de la classification `story_type`.

**Dataset :** 172 user stories annotées manuellement.

**Résultats :**

| Métrique | Valeur |
|----------|--------|
| Accuracy | 96.51% |
| Macro F1 | 0.973 |
| Weighted F1 | 0.965 |
| Erreurs | 6/172 |

**Matrice de confusion :**

|  | doc | functional | invalid | poc_study | technical |
|--|-----|-----------|---------|-----------|-----------|
| **doc** | 1 | 0 | 0 | 0 | 0 |
| **functional** | 0 | 108 | 1 | 0 | 1 |
| **invalid** | 0 | 0 | 10 | 0 | 0 |
| **poc_study** | 0 | 0 | 0 | 7 | 0 |
| **technical** | 0 | 4 | 0 | 0 | 40 |

**Analyse des erreurs :**
- 5 erreurs sur l'axe functional ↔ technical (stories hybrides)
- 1 faux positif `invalid_or_too_weak`
- Classes minoritaires bien identifiées (documentation, poc_or_study : F1 = 1.00)

**Limites :** Dataset déséquilibré (64% functional), d'où l'importance du weighted F1 plutôt que l'accuracy brute.

### 6.2 Méthode 2 — LLM-as-Judge (Qualité des attributs extraits)

**Objectif :** Évaluer la qualité sémantique des attributs extraits (actors, actions, business_rules, testable_points, etc.) — ce qu'aucune métrique classique ne peut mesurer.

**Modèle juge :** GPT-OSS-120B (via Groq), temperature=0.0

**3 dimensions évaluées (0-100) :**

| Dimension | Ce qu'elle mesure |
|-----------|-------------------|
| **Fidelity** | Les éléments extraits sont-ils fidèles à la story source ? Pénalise les vraies hallucinations uniquement |
| **Completeness** | L'analyse capture-t-elle tous les éléments importants présents dans la source ? (tolérant pour les champs naturellement vides) |
| **Coherence** | Cohérence interne entre les champs de l'analyse |

**Verdict final :** Basé sur le `final_score` (moyenne des 3 dimensions) :
- GOOD ≥ 85
- PARTIAL ≥ 70
- BAD < 70

**Seuils d'erreur critique :** fidelity < 70 OU coherence < 70 OU completeness < 70

---

## 7. Composants Utilitaires

### 7.1 Nettoyage de texte (`utils/cleaning.py`)
- Suppression HTML et wiki markup Jira
- Extraction automatique : URLs, clés Jira, utilisateurs de test, codes environnement
- Construction de flags heuristiques (signaux JDD, techniques, complétude)
- Génération de description optimisée pour LLM

### 7.2 Extraction JSON robuste (`utils/json_utils.py`)
- Gestion des wrappers LLM (code fences, balises `<think>`)
- Réparation de JSON tronqué (fermeture automatique des accolades/crochets)
- Extraction par balance de délimiteurs

### 7.3 Chargement de documents (`utils/document_loader.py`)
- Support PDF (pdfplumber), DOCX (python-docx), TXT/CSV/JSON/XML
- Fallback gracieux sur formats non supportés
- Limite de taille : 10 MB

---

## 8. Base de Données

**4 tables SQLite :**

| Table | Contenu | Colonnes principales |
|-------|---------|---------------------|
| `stories` | Stories Jira nettoyées | id, title, description_clean, acceptance_criteria_clean, labels, priority, status |
| `story_analysis` | Résultats d'analyse Agent 1 | story_id, model, story_type, actors, actions, business_rules, testable_points |
| `generated_scenarios` | Scénarios de test générés | story_id, title, type, priority, steps, expected_result |
| `story_scoring` | Scores qualité | story_id, coverage, quality, grade |

---

## 9. API REST (Endpoints)

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/stories/{key}` | GET | Récupérer une story Jira |
| `/stories/{key}/cleaned` | GET | Story nettoyée + enrichie |
| `/epics/` | GET | Lister les epics |
| `/epics/{key}/stories` | GET | Stories d'un epic |
| `/analysis/{key}` | GET | Analyser une story (Agent 1) |
| `/analysis/epic/{key}` | GET | Analyser toutes les stories d'un epic |
| `/documents/{key}` | GET | Documents d'une story |
| `/documents/index/{key}` | POST | Indexer documents pour RAG |
| `/manual-tests/generate/{id}` | POST | Générer tests manuels (Agent 2) |
| `/db/stories` | GET | Requêter les stories stockées |
| `/db/stories/{id}/analysis/latest` | GET | Dernière analyse d'une story |

---

## 10. Bilan Quantitatif

| Élément | Quantité |
|---------|----------|
| Fichiers Python | ~40 |
| Modèles Pydantic | 7 |
| Endpoints API | 15+ |
| Tables SQLite | 4 |
| Prompts LLM | 2 principaux + 5 variantes |
| Modèles LLM testés | 4 (Qwen3, GPT-OSS-20B, GPT-OSS-120B, Llama4) |
| Stories évaluées | 172 (classification) + 48 (LLM-as-Judge) |
| Annotations gold | 172 story_type |

---

## 11. Ce qu'il reste à faire (Mois 4-6)

| Tâche | Priorité | Statut |
|-------|----------|--------|
| Re-runner le LLM-as-Judge avec le prompt corrigé (completeness) | Haute | En cours |
| Évaluation de l'Agent 2 (tests manuels) | Haute | À faire |
| Implémenter `scoring_service.py` (couverture testable_points → tests) | Haute | À faire |
| Implémenter `orchestrator_service.py` (pipeline bout-en-bout) | Moyenne | À faire |
| Génération de tests automatisés (Agent 3) | Moyenne | À faire |
| Endpoints rapport et exécution (`routes_report.py`, `routes_execute.py`) | Basse | À faire |
| Rédaction du rapport PFE | Haute | En cours |

---

## 12. Dépendances Principales

```
fastapi, uvicorn
groq, httpx
pydantic
chromadb, sentence-transformers
scikit-learn
pdfplumber, python-docx
requests, python-dotenv
```
