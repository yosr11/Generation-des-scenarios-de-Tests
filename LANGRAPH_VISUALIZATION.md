# 🚀 LangGraph Pipeline Visualization Guide

## 📊 Vue d'ensemble

Tu peux maintenant visualiser le graphe LangGraph du pipeline orchestrator de 3 façons différentes :

---

## 🎯 Option 1 : Interface Web Interactive (Recommandée)

### ✨ Via l'API FastAPI

Démarre ton serveur :
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Puis ouvre dans le navigateur :
```
http://localhost:8000/pipeline/graph/diagram
```

**Avantages** :
- ✅ Visualisation interactive Mermaid
- ✅ Responsive design
- ✅ Légende des nœuds et couleurs
- ✅ Documentation du workflow intégrée

---

### 📥 Endpoints API supplémentaires

| Endpoint | Format | Description |
|----------|--------|-------------|
| `GET /pipeline/graph/diagram` | HTML | Diagramme interactif (recommandé) |
| `GET /pipeline/graph/ascii` | JSON | Diagramme ASCII en JSON |
| `GET /pipeline/graph/mermaid` | JSON | Définition Mermaid brute |
| `GET /pipeline/graph/png` | PNG | Image PNG (si dispo) |
| `GET /pipeline/info` | JSON | Infos structurelles du pipeline |

**Exemples** :
```bash
# Récupérer la définition Mermaid
curl http://localhost:8000/pipeline/graph/mermaid | jq '.mermaid'

# Récupérer les infos du pipeline
curl http://localhost:8000/pipeline/info | jq

# Récupérer le diagramme ASCII
curl http://localhost:8000/pipeline/graph/ascii | jq '.diagram'
```

---

## 🎯 Option 2 : Script Standalone

### ✨ Générer un fichier HTML indépendant

```bash
cd c:\Users\yomahfoudh\Desktop\Agent_Test
python scripts/visualize_pipeline.py
```

**Résultat** : Génère `pipeline_workflow.html` dans le répertoire courant

#### Variantes :

```bash
# Afficher le diagramme ASCII dans le terminal
python scripts/visualize_pipeline.py --ascii

# Afficher la définition Mermaid brute
python scripts/visualize_pipeline.py --mermaid

# Générer HTML ET ouvrir automatiquement dans le navigateur
python scripts/visualize_pipeline.py --open

# Spécifier un chemin de sortie personnalisé
python scripts/visualize_pipeline.py --output mon_graphe.html
```

---

## 🎯 Option 3 : Terminal ASCII

### ✨ Affichage rapide dans le terminal

```bash
python scripts/visualize_pipeline.py --ascii
```

**Output** :
```
╔════════════════════════════════════════════════════════════════════════════╗
║                    PIPELINE ORCHESTRATOR — WORKFLOW                        ║
╚════════════════════════════════════════════════════════════════════════════╝

                                    START
                                      │
                                      ▼
                        ┌─────────────────────────┐
                        │   1. Enrich Story       │
                        │   (Jira + Cache)        │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ 2. Classify Story       │
                        │ (Agent 1 — Type)        │
                        └────────────┬────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
            invalid/weak      functional        not_functional
                    │                │                │
                    ▼                ▼                ▼
                ┌──────┐    ┌──────────────────┐   ┌──────┐
                │ SKIP │    │ 3. Analysis      │   │ SKIP │
                └──────┘    │ (Agent 1 — Deep) │   └──────┘
                            └────────┬─────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ 4. Business Modeling    │
                        │ (Agent 2 — Optional)    │
                        └────────────┬────────────┘
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │ 5. Generate Tests       │
                        │ (Agent 3 + RAG/Legacy)  │
                        └────────────┬────────────┘
                                     │
                            ┌────────┴────────┐
                            │                 │
                      No tests         Tests generated
                            │                 │
                            ▼                 ▼
                       ┌─────────┐  ┌─────────────────────┐
                       │ NO_TESTS │  │ 6. Validation       │
                       └─────────┘  │ (Agent 4 — Coverage)│
                                     └────────┬────────────┘
                                              │
                                ┌─────────────┴──────────────┐
                                │                            │
                        Coverage >= 70%            Coverage < 70%
                        No duplicates               OR duplicates
                        No ambiguities              OR ambiguities
                                │                            │
                                ▼                            ▼
                        ┌───────────────┐          ┌──────────────────────┐
                        │ 7. Report Gen │          │ 8. Gap-Fill (Agent 3)│
                        │ (Agent 5)     │          │ + Re-validate (Agent4)│
                        └───────┬───────┘          └──────────┬───────────┘
                                │                             │
                                │              Iteration < MAX
                                │              ┌──────────────┘
                                │              │
                                │              └────────────────┐
                                │                                 │
                                └─────────────────┬───────────────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │     END      │
                                          │ (Result JSON)│
                                          └──────────────┘
```

---

## 📁 Fichiers créés

| Fichier | Location | Purpose |
|---------|----------|---------|
| `graph_visualizer.py` | `app/utils/` | Fonctions de génération des diagrammes |
| `routes_graph_visualizer.py` | `app/api/` | Endpoints API pour la visualisation |
| `visualize_pipeline.py` | `scripts/` | Script standalone |
| `pipeline_workflow.html` | **Racine du projet** | HTML généré (créé à la première exécution) |
| `LANGRAPH_VISUALIZATION.md` | Ce fichier | Guide d'utilisation |

---

## 🔍 Comprendre le diagramme

### 🟢 Nœuds verts (START)
- Point d'entrée du pipeline

### 🟡 Nœuds jaunes (SKIP / NO_TESTS / NOT_FUNCTIONAL)
- États terminaux sans génération de tests
- Indiquent un problème ou une exclusion du pipeline

### 🟠 Nœuds orange (Agents)
- **Agent 1** : Classification & Analysis
- **Agent 2** : Business Modeling (optionnel)
- **Agent 3** : Génération de tests
- **Agent 4** : Validation & Coverage check
- **Agent 5** : Rapport final

### 🔵 Nœuds bleus (VALIDATE)
- Point de décision pour la boucle de feedback

### 🟣 Nœuds violets (GAP-FILL)
- Boucle de correction (Agent 3 + Agent 4)

### 🔴 Nœuds roses (END)
- Point de sortie du pipeline

---

## 🔄 La boucle de feedback (Gap-Fill)

```
Agent 4 détecte un problème (coverage < 70%, doublons, ambiguïtés)
                          ↓
            Agent 3 génère des tests pour les points manquants
                          ↓
            Tests sont fusionnés et dédoublonnés
                          ↓
            Agent 4 ré-valide la suite de tests étendue
                          ↓
        Coverage >= 70% ?   OU   Itérations MAX atteint ?
                  ↙YES                   ↘NO
           Agent 5 → END            Boucle repeat
```

**Configuration** :
- `max_correction_iterations` : Nombre max de boucles (défaut: 2)
- `coverage_threshold` : Seuil de couverture (défaut: 70%)

---

## 💡 Tips & Tricks

### Visualiser dans VS Code
Si tu utilises VS Code avec l'extension Markdown Preview:
1. Génère le fichier HTML
2. Ouvre-le avec "Open with Live Server" ou similaire
3. La visualisation s'affiche instantanément

### Exporter pour la documentation
```bash
# Mermaid brut pour inclure dans une doc Markdown
python scripts/visualize_pipeline.py --mermaid > diagram.mermaid

# HTML pour partager avec l'équipe
python scripts/visualize_pipeline.py --open
```

### Intégration CI/CD
```bash
# Générer l'HTML automatiquement lors du build
python scripts/visualize_pipeline.py --output docs/pipeline-workflow.html
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'mermaid'"
Pas de problème ! Le script fonctionne avec ou sans `mermaid-cli`. Les visualisations utilisent Mermaid.js en ligne (CDN).

### Pas d'affichage du diagramme
- Vérifie que tu es connecté à Internet (pour le CDN mermaid.js)
- Essaie le mode `--ascii` pour voir la version texte
- Consulte la console du navigateur (F12) pour les erreurs

### HTML vide
Le fichier HTML a besoin de Mermaid.js (chargé depuis CDN). Si ton navigateur bloque les scripts externes, ajoute une exception pour `cdn.jsdelivr.net`.

---

## 📚 Documentation supplémentaire

Pour plus de détails sur chaque agent:
- Voir `app/services/agent_orchestrator.py` (code source)
- Voir [Agent 1-5 Technical Specs](../README.md) dans ta documentation mémoire

---

## 🎓 Prochaines étapes

1. **Ouvre la visualisation interactive** : http://localhost:8000/pipeline/graph/diagram
2. **Explore les endpoints API** : Essaie les différents formats (JSON, ASCII, Mermaid)
3. **Génère le HTML indépendant** : `python scripts/visualize_pipeline.py`
4. **Inclus dans ton mémoire** : Capture d'écran ou export HTML

Bon workflow! 🚀
