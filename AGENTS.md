# AGENTS.md

This file provides essential guidance for AI coding agents working in this codebase. It summarizes key conventions, architecture, and patterns to ensure agents are immediately productive.

## Agent 3 — Test Validator & Improver (`/agent3`)

- **Rôle** : prend l’analyse Agent 1 (`testable_points`, …) et les tests Agent 2 (`ManualTestCase`), puis améliore la qualité.
- **FastAPI** :
  - `GET /agent3/story/{story_id}` — tableau de bord (couverture, points testables, doublons, ambiguïtés) ; option `generate_tests` pour lancer l’Agent 2.
  - `POST /agent3/validate-and-improve` — corps JSON : `analysis`, `tests`, optionnel `story` / `story_id`, seuils, flags.
  - `POST /agent3/validate-and-improve/by-story/{story_id}` — charge story + analyse SQLite si `analysis` absent ; `tests` toujours requis dans le corps.
- **Modules** (`app/services/`) :
  - `agent3_semantic_similarity.py` — embeddings sentence-transformers.
  - `agent3_coverage_service.py` — couverture point ↔ tests (cosinus).
  - `agent3_duplicate_service.py` — doublons sémantiques entre cas de test.
  - `agent3_ambiguity_service.py` — motifs flous + reformulation LLM (Groq).
  - `agent3_correction_loop.py` — appel Agent 2 (`generate_gap_coverage_tests`) pour points non couverts.
  - `agent3_prescriptive_service.py` — décision APPROVED / REQUIRES_REGENERATION, cibles de regénération, prompt Agent 2, propositions de tests.
- **Flux** : dédoublonnage initial → couverture → si taux \< seuil (défaut 70 %) jusqu’à 2 appels Agent 2 → conservation du meilleur snapshot de couverture → dédoublonnage → clarification d’ambiguïtés → rapport (`coverage_summary_text`, détails corrections) → **champs prescriptifs** (`validation_decision`, `regeneration_targets`, `feedback_prompt_for_agent2`, `improved_test_proposals`, `iteration_recommendation`, `should_retry`, `max_regeneration_attempts`).
- **Historique** : les routes `/audit/vague_formulations*` restent un audit **ciblé** sur des formulations interdites ; le validateur complet est sous `/agent3`.

## Build/Test Commands
- The project is a Python application. No explicit build system is used.
- Main entry points:
  - Main app: `app/main.py`
  - Evaluation: `eval/run_eval.py`, `eval/generate_agent_outputs.py`
- Run scripts with:
  - `python app/main.py`
  - `python eval/run_eval.py`
- No standard test framework or `test/` directory. Manual test scripts: `app/test_groq.py`, `app/api/manual_test_generation.py`.

## Architecture & Component Boundaries
- Modular structure under `app/`:
  - `api/`: FastAPI route handlers by domain
  - `core/`: Config and logging
  - `data/`: Epics data, vector store (Chroma DB)
  - `db/`: Database access/init
  - `models/`: Pydantic models
  - `prompts/`: LLM prompt templates
  - `repositories/`: Data access layer
  - `services/`: Business logic, orchestration
  - `utils/`: Utility functions
- `eval/`: Evaluation scripts/results

## Project-Specific Conventions
- Prompts for LLMs: `app/prompts/`
- Data: `app/data/`
- Models: Pydantic, in `app/models/`
- Service/repository patterns for logic/data
- Route handlers grouped by domain in `app/api/`
- Config centralized in `core/config.py`

## Potential Pitfalls
- Chroma vector store (in `app/data/vector_store/`) requires local SQLite files.
- No `requirements-dev.txt` or test dependencies; install as needed.
- Some scripts expect data files in `app/data/epics/`.
- Ensure all dependencies in `requirements.txt` are installed.
- No Dockerfile; setup is manual.
- Non-ASCII filenames (e.g., `paramÞtres`) may cause issues on some systems.

## Key Files/Directories
- `app/main.py`: Main entry point
- `app/api/routes_*.py`: API endpoint structure
- `app/models/`: Pydantic models
- `app/services/`: Core business logic
- `app/prompts/`: LLM prompt templates
- `eval/`: Agent evaluation scripts/results

---

For more details, see the relevant directories and scripts. Update this file as the project evolves to keep agents productive.
