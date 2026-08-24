# 🚀 PipelineState — Résumé Rapide

## Qu'est-ce que c'est ?

**PipelineState** = un conteneur de données partagées qui circule entre tous les agents du pipeline.

```
START → AGENT1 → AGENT2 → AGENT3 → AGENT4 → AGENT5 → END
  ↓       ↓        ↓        ↓        ↓        ↓       ↓
  └───────┴────────┴────────┴────────┴────────┴───────┘
         PipelineState circule ici (⟲)
```

---

## 3 Catégories de Champs

### 1️⃣ **INPUTS** (Paramètres)
```python
story_id: "PROJ-123"                  # ID Jira
use_rag: true                         # Options
model_agent1: "qwen3.6"              # Modèles LLM
coverage_threshold: 0.70             # Seuil 70%
max_correction_iterations: 2         # Max 2 boucles
```

### 2️⃣ **OUTPUTS** (Résultats accumulés)
```python
story: {...}                         # Story enrichie (Agent 1)
analysis: {...}                      # Analyse (Agent 1)
business_model: {...}                # Business (Agent 2)
tests: [{...}, {...}]               # Tests générés (Agent 3)
validation: {...}                    # Validation (Agent 4)
report: {...}                        # Rapport final (Agent 5)
```

### 3️⃣ **CONTROL** (Métadonnées)
```python
correction_iteration: 1              # Itération actuelle
status: "running"                    # État du pipeline
errors: []                           # Erreurs
duration_ms: 45000                   # Temps écoulé
token_usage: {...}                   # Tokens utilisés
```

---

## Comment ça Marche ? (5 étapes)

### ✨ Étape 1: Chaque agent LIT l'état
```python
def node_agent3_generate(state: PipelineState) -> dict:
    story = state["story"]              # ← LIT
    analysis = state["analysis"]        # ← LIT
    tests = state["tests"]              # ← LIT
```

### 🔨 Étape 2: Fait son travail
```python
    result = generate_tests(story, analysis)
```

### 📝 Étape 3: Retourne ce qu'il a modifié/ajouté
```python
    return {
        "tests": result.tests,          # ← ÉCRIT
        "generation_result": result,    # ← ÉCRIT
    }
```

### 🔄 Étape 4: LangGraph fusionne le retour avec l'état
```python
# state avant = {story: {...}, analysis: {...}}
# return du node = {tests: [...], generation_result: {...}}
# state après = {story: {...}, analysis: {...}, tests: [...], generation_result: {...}}
```

### 🔁 Étape 5: L'agent suivant reçoit l'état complet
```python
def node_agent4_validate(state: PipelineState) -> dict:
    tests = state["tests"]              # ← Disponible !
    analysis = state["analysis"]        # ← Disponible !
    validation = validate(tests, analysis)
    return {"validation": validation}
```

---

## Visualisation Simple

```
INITIAL STATE
├─ story_id: "PROJ-123"
├─ use_rag: true
├─ correction_iteration: 0
└─ status: "running"

            ▼ (ENRICH lit story_id)

STATE APRÈS ENRICH
├─ story_id: "PROJ-123"
├─ use_rag: true
├─ story: {...enriched from Jira...}
├─ correction_iteration: 0
└─ status: "running"

            ▼ (CLASSIFY lit story)

STATE APRÈS CLASSIFY
├─ story_id: "PROJ-123"
├─ use_rag: true
├─ story: {...}
├─ classification: {type: "functional", ...}
├─ analysis: {...}
├─ correction_iteration: 0
└─ status: "running"

            ▼ ... (etc)

FINAL STATE (après END)
├─ story_id: "PROJ-123"
├─ story: {...}
├─ analysis: {...}
├─ business_model: {...}
├─ tests: [{...}, {...}, ...]
├─ validation: {...}
├─ report: {...}
├─ status: "completed"
└─ duration_ms: 45000
```

---

## Avantages 🎯

| Avantage | Bénéfice |
|----------|----------|
| **Pas d'API** | Les agents ne s'appellent pas, partage via état |
| **Pas de DB** | Les données circulent en mémoire (rapide) |
| **Historique** | Chaque agent voit ce qui s'est passé avant |
| **Debugging** | On peut logger l'état à chaque étape |
| **Type-safe** | TypedDict garantit les types |
| **Recalcul facile** | Rejoue le pipeline avec le même état initial |

---

## Analogie du Monde Réel

Imagine une **chaîne de montage de voiture** :

```
INITIAL: Carcasse vide
   ↓
STATION 1: Ajoute moteur
   → État: {carcasse, moteur}
   ↓
STATION 2: Ajoute roues
   → État: {carcasse, moteur, roues}
   ↓
STATION 3: Ajoute intérieur
   → État: {carcasse, moteur, roues, intérieur}
   ↓
STATION 4: Paint & Polish
   → État final: {carcasse, moteur, roues, intérieur, paint}
```

Chaque **station ajoute ce dont elle a besoin**, et chaque **station suivante** voit tout ce qui a été fait avant.

---

## Exemple Concret dans le Code

```python
# ─── Agent 3 Génère les Tests ───

def node_agent3_generate(state: PipelineState) -> dict:
    # READ
    story = state["story"]                  # Besoin de la story enrichie
    analysis = state["analysis"]            # Besoin de l'analyse
    rag_context = state.get("rag_context") # Optionnel
    
    # PROCESS
    tests = generate_tests_llm(
        story=story,
        analysis=analysis,
        rag_context=rag_context
    )
    
    # WRITE & RETURN
    return {
        "tests": tests,                     # Ajoute les tests à l'état
        "generation_result": {...}         # Ajoute metadata
    }
    
# RÉSULTAT: 
# L'état maintenant a: story + analysis + tests + generation_result

# ─── Agent 4 Valide les Tests ───

def node_agent4_validate(state: PipelineState) -> dict:
    # READ (tout ce qui a été accumulé)
    tests = state["tests"]                  # Vient d'Agent 3 ✓
    analysis = state["analysis"]            # Vient d'Agent 1 ✓
    story = state["story"]                  # Vient de Enrich ✓
    
    # PROCESS
    validation = validate_tests(
        tests=tests,
        analysis=analysis,
        coverage_threshold=state["coverage_threshold"]
    )
    
    # WRITE & RETURN
    return {
        "validation": validation
    }
    
# RÉSULTAT:
# L'état maintenant a: story + analysis + tests + validation
```

---

## Cas Particulier: La Boucle Gap-Fill

```
Agent 4 détecte: coverage < 70%
                    ↓
DECISION: "Il faut plus de tests"
                    ↓
Gap-Fill (Agent 3) : 
   • LIT: tests actuels + uncovered points
   • GÉNÈRE: nouveaux tests pour points manquants
   • ÉCRIT: merged tests (anciens + nouveaux)
   • UPDATE: correction_iteration++
                    ↓
Re-Validate (Agent 4):
   • LIT: tests étendus
   • VALIDE: nouvelle couverture
   • Si still < 70% ET iterations < MAX:
       → Boucle repeat
   • Sinon:
       → Vers Agent 5
```

---

## Résumé En Une Phrase

> **PipelineState** = une valise de données qui voyage à travers chaque agent, s'enrichit à chaque étape, et arrive à la fin remplie de tous les résultats.

---

## Ressources Complètes

- 📖 **[PIPELINESTATE_EXPLAINED.md](PIPELINESTATE_EXPLAINED.md)** — Explication complète avec diagrammes
- 🎮 **[pipelinestate_interactive.html](pipelinestate_interactive.html)** — Animation interactive
- 📊 **[pipeline_workflow.html](pipeline_workflow.html)** — Diagramme du workflow
- 💻 **[agent_orchestrator.py](app/services/agent_orchestrator.py)** — Code source
