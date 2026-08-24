# 🔄 PipelineState — Explication Complète

## 📌 Qu'est-ce que PipelineState ?

**PipelineState** est un **conteneur d'état partagé** qui circule entre tous les nœuds du graphe LangGraph. C'est comme une **valise de données** qui passe de main en main à travers le pipeline.

### Analogie Simple
```
Imagine une chaîne de montage automobile :

START ──┬────────────────────────────────────────────────────────────┐
        │                                                            │
        │ VALISE (State) contient:                                 │
        │ • Pièces du véhicule (données)                           │
        │ • Étapes complétées (historique)                         │
        │ • Configuration (paramètres)                             │
        │                                                            │
     Station 1        Station 2        Station 3        Station 4   │
     (Enrich)    →    (Classify)  →   (Analysis)  →   (Generate) │
        ↓              ↓               ↓               ↓             │
        │ Lit la valise │ Lit la valise │ Lit la valise│ Lit la valise
        │ Ajoute stuff  │ Ajoute stuff  │ Ajoute stuff│ Ajoute stuff
        │ Retourne      │ Retourne      │ Retourne    │ Retourne    │
        │               │               │             │             │
        └───────────────┴───────────────┴─────────────┴─────────────→ END
```

---

## 🏗️ Structure du PipelineState

Le `PipelineState` est une `TypedDict` avec 3 catégories:

### 1️⃣ **ENTRÉES** (Configuration initiale)
```python
# Paramètres passés au pipeline
story_id: str                           # ID Jira (ex: "PROJ-123")
use_rag: bool                          # Utiliser RAG ou non
use_legacy_rag: bool                   # Utiliser legacy test RAG
model_agent1: str                      # Modèle pour Agent 1
model_agent3: str                      # Modèle pour Agent 3
model_agent4_quality: str              # Modèle pour Agent 4
model_agent5: str                      # Modèle pour Agent 5
model_agent2: str                      # Modèle pour Agent 2
coverage_threshold: float              # Seuil de couverture (ex: 0.70 = 70%)
max_correction_iterations: int         # Max 3 boucles gap-fill
force_reanalyze: bool                  # Forcer re-analyse
force_refresh: bool                    # Forcer refetch Jira
```

### 2️⃣ **DONNÉES ACCUMULÉES** (Résultats intermédiaires)
```python
# Données qui s'accumulent au fur du pipeline
story: Dict[str, Any]                  # Story Jira enrichie (Agent 1 input)
rag_context: Optional[list]            # Contexte RAG (Agent 1 & 3 input)
legacy_examples: Optional[list]        # Tests legacy similaires (Agent 3 few-shot)

# Résultats Agent 1
classification: Optional[Any]          # Story type (functional/invalid/technical)
analysis: Optional[Any]                # Analysis détaillée
analysis_dict: Optional[Dict]          # Même chose en dict

# Résultats Agent 2
business_model: Optional[Any]          # Business goals & workflows

# Résultats Agent 3
generation_result: Optional[Any]       # Metadata générateur
tests: List[Any]                       # Tests générés (ManualTestCase[])
agent3_golden_rule_warnings: List[str] # Warnings QA
agent3_message: Optional[str]          # Message status

# Résultats Agent 4
validation: Optional[Any]              # Validation report (coverage, duplicates, etc)

# Résultats Agent 5
report: Optional[Any]                  # Rapport final
```

### 3️⃣ **CONTRÔLE** (Métadonnées d'exécution)
```python
correction_iteration: int              # Numéro itération actuelle (0, 1, 2, ...)
status: str                            # "running" | "completed" | "failed" | "skipped"
errors: List[str]                      # Liste des erreurs rencontrées
duration_ms: int                       # Temps total d'exécution
token_usage: Optional[Dict]            # Tokens utilisés par agent
```

---

## 🔄 Comment ça Circule ?

### **Étape 1: START** (Initialisation)
```python
initial_state = {
    "story_id": "PROJ-123",
    "model_agent1": "qwen3.6",
    "coverage_threshold": 0.70,
    "correction_iteration": 0,
    "status": "running",
    "errors": [],
    "tests": [],
}
# ▼ État minimal, prêt à être enrichi
```

### **Étape 2: Agent 1 (ENRICH)**
```python
def node_enrich_story(state: PipelineState) -> dict:
    story_id = state["story_id"]        # ← LIT story_id
    
    story = fetch_from_jira(story_id)   # Fetch Jira
    story = clean_and_enrich(story)     # Nettoyage
    
    return {
        "story": story,                 # ← ÉCRIT story
        "status": "running"
    }

# Input state:  {story_id: "PROJ-123", ...}
# Output state: {story_id: "PROJ-123", story: {...enriched...}, ...}
```

### **Étape 3: Agent 1 (CLASSIFY)**
```python
def node_classify_story(state: PipelineState) -> dict:
    story = state["story"]              # ← LIT story
    
    classification = classify_with_llm(story)  # Agent 1
    analysis = merge_results(classification)
    
    return {
        "classification": classification,  # ← ÉCRIT classification
        "analysis": analysis,              # ← ÉCRIT analysis
        "analysis_dict": analysis.to_dict()
    }

# Input state:  {story_id: "...", story: {...}, ...}
# Output state: {story_id: "...", story: {...}, classification: {...}, analysis: {...}, ...}
```

### **Étape 4: Agent 2 (BUSINESS MODEL)**
```python
def node_agent2_business_model(state: PipelineState) -> dict:
    analysis_dict = state["analysis_dict"]  # ← LIT analysis_dict
    model = state.get("model_agent2")
    
    business_model = build_business_model(analysis_dict, model)
    
    return {
        "business_model": business_model   # ← ÉCRIT business_model
    }

# State accumule: story + classification + analysis + business_model
```

### **Étape 5: Agent 3 (GENERATE)**
```python
def node_agent3_generate(state: PipelineState) -> dict:
    story = state["story"]              # ← LIT story
    analysis_dict = state["analysis_dict"]  # ← LIT analysis_dict
    business_model = state["business_model"]  # ← LIT business_model
    rag_context = state.get("rag_context")  # ← LIT RAG (optionnel)
    legacy_examples = state.get("legacy_examples")  # ← LIT tests legacy
    
    result = generate_tests(
        story=story,
        analysis=analysis_dict,
        business_model=business_model,
        rag_context=rag_context,
        legacy_examples=legacy_examples
    )
    
    return {
        "generation_result": result,    # ← ÉCRIT generation_result
        "tests": result.tests,          # ← ÉCRIT tests (liste)
        "agent3_golden_rule_warnings": result.warnings
    }

# State accumule: tout + tests
```

### **Étape 6: Agent 4 (VALIDATE)**
```python
def node_agent4_validate(state: PipelineState) -> dict:
    tests = state["tests"]              # ← LIT tests
    analysis = state["analysis"]        # ← LIT analysis
    
    validation = validate_tests(
        tests=tests,
        testable_points=analysis.testable_points,
        coverage_threshold=state["coverage_threshold"]
    )
    
    return {
        "validation": validation,       # ← ÉCRIT validation
        "status": "running"             # ← UPDATE status
    }

# State accumule: tout + validation
```

### **Étape 7: DECISION (Gap-Fill ou Agent 5)**
```python
def route_after_agent4(state: PipelineState) -> str:
    validation = state["validation"]            # ← LIT validation
    coverage = validation.report.coverage_rate  # Couverture ?
    iteration = state["correction_iteration"]   # Itérations ?
    max_iter = state["max_correction_iterations"]
    
    # Décision basée sur l'état
    if coverage >= 0.70 or iteration >= max_iter:
        return "agent5_report"  # Vers Agent 5 (END)
    else:
        return "agent3_gap_fill"  # Boucle correction
```

### **Étape 8 (Optionnel): Gap-Fill Loop**
```python
def node_agent3_gap_fill(state: PipelineState) -> dict:
    tests = state["tests"]              # ← LIT tests actuels
    validation = state["validation"]    # ← LIT validation
    uncovered = validation.report.uncovered_testable_points  # Points manquants
    
    # Générer tests pour les points manquants
    new_tests = generate_gap_fill_tests(uncovered)
    
    # Fusionner avec existants
    merged_tests = tests + new_tests
    
    return {
        "tests": merged_tests,                    # ← UPDATE tests
        "correction_iteration": iteration + 1    # ← UPDATE itération
    }

# Puis re-validation (boucle Agent 4)
```

### **Étape 9: Agent 5 (REPORT)**
```python
def node_agent5_report(state: PipelineState) -> dict:
    analysis = state["analysis"]        # ← LIT
    generation_result = state["generation_result"]  # ← LIT
    validation = state["validation"]    # ← LIT
    
    report = generate_final_report(
        analysis=analysis,
        generation=generation_result,
        validation=validation,
        iterations=state["correction_iteration"]
    )
    
    return {
        "report": report,               # ← ÉCRIT rapport final
        "status": "completed"           # ← UPDATE status
    }
```

### **END**
```python
final_state = {
    "story_id": "PROJ-123",
    "story": {...},
    "classification": {...},
    "analysis": {...},
    "business_model": {...},
    "tests": [{...}, {...}, ...],
    "validation": {...},
    "report": {...},
    "status": "completed",
    "correction_iteration": 1,
    "duration_ms": 45000,
    "token_usage": {"agent1": 1500, "agent3": 3000, ...}
}
```

---

## 🎯 Pourquoi PipelineState ?

### ✅ **Avantages**

| Avantage | Explication |
|----------|-------------|
| **Partage de données** | Les agents n'ont pas besoin d'API entre eux, tout passe via l'état |
| **Évite les DB calls** | Les données circulent en mémoire (plus rapide) |
| **Historique** | Chaque étape voit ce qui s'est passé avant |
| **Recalcul facile** | On peut re-exécuter le pipeline avec le même état |
| **Debugging** | On peut logger/analyser l'état à chaque étape |
| **Parallélisation future** | Si besoin de paralleliser certains agents |
| **Type-safe** | TypedDict garantit les types (même en Python) |

---

## 📊 Diagramme du Flux d'État

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          INITIAL STATE                                      │
│  story_id: "PROJ-123"                                                       │
│  use_rag: true                                                              │
│  model_agent1: "qwen3.6"                                                    │
│  correction_iteration: 0                                                    │
│  status: "running"                                                          │
└────────────────────────┬──────────────────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────────┐
         │ ENRICH (node_enrich_story)        │
         │ LIT: story_id                     │
         │ ÉCRIT: story                      │
         └───────────────────┬───────────────┘
                             │
                             ▼
     ┌───────────────────────────────────────────────────┐
     │ STATE AFTER ENRICH                                │
     │ + story: {id, summary, description, ...}          │
     └───────────┬───────────────────────────────────────┘
                 │
                 ▼
         ┌──────────────────────────────────┐
         │ CLASSIFY (node_classify_story)   │
         │ LIT: story                       │
         │ ÉCRIT: classification, analysis  │
         └──────────────┬────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────────────┐
   │ STATE AFTER CLASSIFY                            │
   │ + classification: {type, ...}                   │
   │ + analysis: {actors, actions, testable_points} │
   └──────────┬──────────────────────────────────────┘
              │
              ▼
     ┌─────────────────────────────────┐
     │ AGENT 2 (node_agent2_business)  │
     │ LIT: analysis_dict              │
     │ ÉCRIT: business_model           │
     └────────────┬──────────────────────┘
                  │
                  ▼
  ┌────────────────────────────────────────┐
  │ STATE AFTER AGENT 2                    │
  │ + business_model: {goals, workflows}   │
  └──────────┬─────────────────────────────┘
             │
             ▼
     ┌──────────────────────────────────┐
     │ GENERATE (node_agent3_generate)  │
     │ LIT: story, analysis, rag_context│
     │ ÉCRIT: tests, generation_result  │
     └────────┬────────────────────────────┘
              │
              ▼
  ┌──────────────────────────────────────┐
  │ STATE AFTER GENERATE                 │
  │ + tests: [{...}, {...}, ...]         │
  │ + generation_result: metadata        │
  └───────┬──────────────────────────────┘
          │
          ▼
     ┌───────────────────────────────┐
     │ VALIDATE (node_agent4_validate)│
     │ LIT: tests, analysis          │
     │ ÉCRIT: validation             │
     └──────┬────────────────────────┘
            │
            ▼
  ┌───────────────────────────────┐
  │ DECISION POINT                │
  │ coverage >= 70% ?             │
  │ iterations < MAX ?            │
  └──┬──────────────────────┬──────┘
     │ YES (valid)          │ NO (need fixes)
     │                      │
     ▼                      ▼
   REPORT              GAP-FILL (loop)
   Agent 5             + Re-validate
     │                      │
     │              ┌────────┘
     │              │
     ▼              ▼
  ┌──────────────────────────────────┐
  │ REPORT (node_agent5_report)      │
  │ LIT: analysis, tests, validation │
  │ ÉCRIT: report, status="completed"│
  └──────┬───────────────────────────┘
         │
         ▼
  ┌──────────────────────────────────┐
  │ FINAL STATE                      │
  │ ✓ Toutes données disponibles    │
  │ ✓ status = "completed"           │
  └──────────────────────────────────┘
```

---

## 💻 Exemple Complet de Code

```python
# ✅ COMMENT LES AGENTS UTILISENT L'ÉTAT

# AGENT 1 - LIT ET ÉCRIT
def node_classify_story(state: PipelineState) -> dict:
    # LIRE de l'état
    story = state["story"]
    
    # TRAITER
    classification = llm_classify(story)
    analysis = merge_results(classification)
    
    # ÉCRIRE de retour dans l'état
    return {
        "classification": classification,
        "analysis": analysis,
        "analysis_dict": analysis.to_dict()
    }

# AGENT 3 - LIT MULTIPLE ET ÉCRIT
def node_agent3_generate(state: PipelineState) -> dict:
    # LIRE plusieurs champs
    story = state["story"]
    analysis_dict = state["analysis_dict"]
    business_model = state["business_model"]
    rag_context = state.get("rag_context")
    legacy_examples = state.get("legacy_examples")
    model = state.get("model_agent3", "nova-lite-2")
    
    # TRAITER avec toutes les données
    result = generate_manual_tests_for_story_data(
        story=story,
        analysis=analysis_dict,
        model_alias=model,
        rag_context=rag_context,
        legacy_examples=legacy_examples,
    )
    
    # ÉCRIRE le résultat
    return {
        "generation_result": result,
        "tests": list(result.tests),
        "agent3_golden_rule_warnings": list(getattr(result, "golden_rule_warnings", None) or []),
        "agent3_message": getattr(result, "message", None),
    }

# ROUTEUR CONDITIONNEL - LIT ET DÉCIDE
def route_after_agent4(state: PipelineState) -> str:
    # LIRE pour décider
    validation = state.get("validation")
    if not validation:
        return "agent5_report"
    
    report = validation.report
    coverage = report.coverage_rate
    iteration = state.get("correction_iteration", 0)
    max_iter = state.get("max_correction_iterations", 2)
    
    # DÉCIDER le prochain nœud
    if iteration < max_iter and coverage < 0.70:
        logger.info(f"Coverage {coverage:.1%} < 70% → gap-fill")
        return "agent3_gap_fill"
    else:
        logger.info(f"Coverage {coverage:.1%} >= 70% → report")
        return "agent5_report"
```

---

## 🎓 Résumé

| Concept | Explication |
|---------|------------|
| **PipelineState** | Conteneur d'état partagé TypedDict |
| **LIT** | Chaque nœud lit les champs dont il a besoin |
| **ÉCRIT** | Chaque nœud retourne un dict avec les champs à mettre à jour |
| **ACCUMULE** | Les données s'accumulent au fur du pipeline |
| **CIRCULE** | L'état complet circule de nœud en nœud |
| **FINAL** | À la fin, l'état contient TOUS les résultats |
| **RÉCUPÉRABLE** | On peut récupérer le rapport final depuis `final_state["report"]` |

---

**C'est ça `PipelineState`!** 🎯 Une simple but puissante façon de passer les données à travers le pipeline LangGraph.
