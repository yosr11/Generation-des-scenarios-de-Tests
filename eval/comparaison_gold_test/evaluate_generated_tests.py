"""
evaluate_generated_tests.py
============================
Évalue les generated_tests par rapport aux gold_tests pour chaque user story du JSON file.

Métriques :
  - Métrique 1 : Similarité cosinus (sentence-transformers, paraphrase-multilingual-MiniLM-L12-v2)
  - Métrique 2 : LLM as Judge (gpt-4.1 via GitHub Models)
      Dimensions jugées :
        coverage_score        – fonctionnalités couvertes par les generated vs gold
        missing_tests_score   – absence de scénarios présents dans les gold tests
        qa_quality_score      – clarté, exécutabilité, cohérence, structure
        business_similarity   – les mêmes objectifs métier sont-ils testés ?
        final_score           – moyenne des 4 dimensions

Usage :
  python -m eval.evaluate_generated_tests
  ou directement :
  python eval/evaluate_generated_tests.py

Sortie :
  eval/results/generated_tests_evaluation.json
"""

import json
import sys
import time
from pathlib import Path

# ── Chargement sentence-transformers ────────────────────────────────────────
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False
    print("[WARN] sentence-transformers non disponible – similarité cosinus ignorée.")

# ── Import du client LLM existant ───────────────────────────────────────────
# Ajouter la racine du projet afin que l'import "app.services.llm_client" fonctionne
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.services.llm_client import call_github_models

# ── Chemins ─────────────────────────────────────────────────────────────────
JSON_FILE = Path(__file__).parent / "JSON file.json"
OUTPUT_FILE = Path(__file__).resolve().parents[1] / "results" / "generated_tests_evaluation_gpt_4.1.json"

# ── Modèle sentence-transformers (multilingue FR/EN) ────────────────────────
ST_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# ── LLM Judge model ─────────────────────────────────────────────────────────
JUDGE_MODEL = "gpt-4.1"       # GitHub Models — contexte 128k, pas de limite TPM stricte
JUDGE_MAX_CHARS = None        # troncature par bloc (gold / generated). None = no truncation


# ────────────────────────────────────────────────────────────────────────────
# Utilitaires de sérialisation
# ────────────────────────────────────────────────────────────────────────────

def steps_to_text(steps: list) -> str:
    """Convertit une liste d'étapes en texte lisible — uniquement label, actions et résultat attendu.
    Data, revision_po et attachments sont exclus de la comparaison."""
    parts = []
    for s in steps:
        step_num = s.get("step", "")
        label = s.get("Etape") or s.get("Précondition") or s.get("Precondition", "")
        actions = "; ".join(a for a in s.get("actions", []) if a.strip())
        expected = "; ".join(s.get("expected_result", []))
        line = f"Étape {step_num}: {label}"
        if actions:
            line += f" | Actions: {actions}"
        if expected:
            line += f" | Résultat attendu: {expected}"
        parts.append(line)
    return "\n".join(parts)


def test_to_text(test: dict) -> str:
    """Sérialise un test (gold ou generated) en texte plat."""
    summary = test.get("summary", "")
    desc = " ".join(test.get("description", []))
    steps_txt = steps_to_text(test.get("steps", []))
    return f"Résumé: {summary}\nDescription: {desc}\nÉtapes:\n{steps_txt}"


def tests_list_to_text(tests) -> str:
    """Sérialise une liste ou un dict de tests en texte plat."""
    if isinstance(tests, dict):
        tests = [tests]
    if not tests:
        return "(aucun test)"
    return "\n\n---\n\n".join(test_to_text(t) for t in tests)


# ────────────────────────────────────────────────────────────────────────────
# Métrique 1 : Similarité cosinus
# ────────────────────────────────────────────────────────────────────────────

def cosine_similarity(vec_a: "np.ndarray", vec_b: "np.ndarray") -> float:
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def compute_cosine_similarity(gold_text: str, gen_text: str, model: "SentenceTransformer") -> float:
    vecs = model.encode([gold_text, gen_text], normalize_embeddings=False)
    return round(cosine_similarity(vecs[0], vecs[1]), 4)


# ────────────────────────────────────────────────────────────────────────────
# Métrique 2 : LLM as Judge
# ────────────────────────────────────────────────────────────────────────────

JUDGE_SYSTEM_PROMPT = """
Tu es un expert QA chargé d'évaluer des tests générés par un LLM par rapport à des tests gold écrits par des humains.

Tu reçois :
- La user story source (contexte métier)
- Les gold tests (tests de référence écrits par des testeurs QA humains)
- Les generated tests (tests générés automatiquement par un agent IA)

Évalue les tests générés sur 5 dimensions, de 0 à 100 :

1. coverage_score
   - Dans quelle mesure les generated tests couvrent-ils les fonctionnalités testées par les gold tests ?
   - 100 = toutes les fonctionnalités des gold tests sont couvertes.
   - 0 = aucune fonctionnalité des gold tests n'est couverte.

2. missing_tests_score
   - Score inversé : 100 = aucun scénario manquant (les generated tests couvrent tout).
   - 0 = de nombreux scénarios importants des gold tests sont absents des generated tests.
   - Liste les scénarios manquants dans le champ missing_scenarios.

3. qa_quality_score
   - Les generated tests sont-ils : clairs, exécutables, cohérents, bien structurés ?
   - 100 = qualité professionnelle parfaite.
   - 0 = tests inutilisables, vagues, incohérents.

4. business_similarity
   - Les generated tests testent-ils les mêmes objectifs métier que les gold tests ?
   - 100 = objectifs métier identiques.
   - 0 = objectifs métier totalement différents.

final_score = moyenne arithmétique des 4 dimensions (calcule-la toi-même).

Retourne UNIQUEMENT un JSON valide avec cette structure exacte :
{
  "coverage_score": 0,
  "missing_tests_score": 0,
  "qa_quality_score": 0,
  "business_similarity": 0,
  "final_score": 0.0,
  "missing_scenarios": [],
  "summary": ""
}

Règles :
- summary : 2-4 phrases maximum, en français.
- Pas d'explication hors JSON.
- final_score doit être un nombre décimal.
""".strip()


def build_judge_user_prompt(user_story: dict, gold_text: str, gen_text: str) -> str:
    story_title = user_story.get("title", "")
    story_desc = user_story.get("description", "")
    if isinstance(story_desc, dict):
        story_desc = story_desc.get("user_story", str(story_desc))

    return f"""== USER STORY ==
Titre : {story_title}
Description : {story_desc}

== GOLD TESTS (référence humaine) ==
{gold_text}

== GENERATED TESTS (tests générés par l'IA) ==
{gen_text}

Évalue maintenant les generated tests selon les 5 dimensions définies.
""".strip()


def _truncate(text: str, max_chars: int) -> str:
    """Tronque un texte à max_chars caractères si nécessaire."""
    # If max_chars is None or non-positive, do not truncate
    if not max_chars or max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[tronqué pour respecter la limite de contexte]"


def call_llm_judge(user_story: dict, gold_text: str, gen_text: str) -> dict:
    gold_trunc = _truncate(gold_text, JUDGE_MAX_CHARS)
    gen_trunc  = _truncate(gen_text,  JUDGE_MAX_CHARS)
    user_prompt = build_judge_user_prompt(user_story, gold_trunc, gen_trunc)
    # Log the size of the blocks sent to the LLM for diagnostics
    try:
        gold_len = len(gold_trunc) if isinstance(gold_trunc, str) else 0
        gen_len = len(gen_trunc) if isinstance(gen_trunc, str) else 0
        print(f"  → Taille du bloc GOLD envoyé au juge: {gold_len} caractères")
        print(f"  → Taille du bloc GENERATED envoyé au juge: {gen_len} caractères")
    except Exception:
        # ne pas échouer l'évaluation pour un simple log
        pass
    try:
        raw_str = call_github_models(
            system_prompt=JUDGE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model_alias=JUDGE_MODEL,
            temperature=0.0,
            max_tokens=800,
        )
        result = json.loads(raw_str)
        scores = [
            result.get("coverage_score", 0),
            result.get("missing_tests_score", 0),
            result.get("qa_quality_score", 0),
            result.get("business_similarity", 0),
        ]
        result["final_score"] = round(sum(scores) / len(scores), 2)
        return result
    except Exception as e:
        print(f"  [LLM Judge] Erreur : {e}")
        return {
            "coverage_score": 0,
            "missing_tests_score": 0,
            "qa_quality_score": 0,
            "business_similarity": 0,
            "final_score": 0.0,
            "missing_scenarios": [],
            "summary": f"Erreur : {e}",
            "error": True,
        }


def get_verdict(score: float) -> str:
    if score >= 80:
        return "GOOD"
    elif score >= 60:
        return "PARTIAL"
    else:
        return "BAD"


# ────────────────────────────────────────────────────────────────────────────
# Pipeline principal
# ────────────────────────────────────────────────────────────────────────────

def load_data() -> list:
    encodings_to_try = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    last_err = None
    for enc in encodings_to_try:
        try:
            with open(JSON_FILE, encoding=enc) as f:
                return json.load(f)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            last_err = e
            continue
    raise last_err


def evaluate_story(
    story: dict,
    st_model,
) -> dict:
    story_id = story.get("story_id", "?")
    user_story = story.get("user_story", {})

    gold_raw = story.get("gold_tests", {})
    gen_raw = story.get("generated_tests", [])

    # Normalise gold_tests en liste
    if isinstance(gold_raw, dict):
        gold_tests = [gold_raw] if gold_raw else []
    elif isinstance(gold_raw, list):
        gold_tests = [t for t in gold_raw if t]
    else:
        gold_tests = []

    # Normalise generated_tests en liste
    if isinstance(gen_raw, dict):
        gen_tests = [gen_raw] if gen_raw else []
    elif isinstance(gen_raw, list):
        gen_tests = [t for t in gen_raw if t]
    else:
        gen_tests = []

    print(f"\n[{story_id}] gold={len(gold_tests)} tests | generated={len(gen_tests)} tests")

    if not gold_tests:
        print(f"  → Pas de gold tests, story ignorée.")
        return {
            "story_id": story_id,
            "user_story_title": user_story.get("title", ""),
            "skipped": True,
            "reason": "Pas de gold tests",
        }

    if not gen_tests:
        print(f"  → Pas de generated tests, story ignorée.")
        return {
            "story_id": story_id,
            "user_story_title": user_story.get("title", ""),
            "skipped": True,
            "reason": "Pas de generated tests",
        }

    gold_text = tests_list_to_text(gold_tests)
    gen_text = tests_list_to_text(gen_tests)

    # ── Métrique 1 : Cosine similarity ──────────────────────────────────────
    cosine_score = None
    if ST_AVAILABLE and st_model is not None:
        print(f"  → Calcul similarité cosinus...")
        cosine_score = compute_cosine_similarity(gold_text, gen_text, st_model)
        print(f"     Cosine similarity = {cosine_score}")

    # ── Métrique 2 : LLM Judge ──────────────────────────────────────────────
    print(f"  → Appel LLM Judge ({JUDGE_MODEL} via GitHub Models)...")
    judge_result = call_llm_judge(user_story, gold_text, gen_text)
    print(f"     Final score = {judge_result.get('final_score')} → {get_verdict(judge_result.get('final_score', 0))}")

    return {
        "story_id": story_id,
        "user_story_title": user_story.get("title", ""),
        "priority": user_story.get("priority", ""),
        "gold_tests_count": len(gold_tests),
        "generated_tests_count": len(gen_tests),
        "metric_1_cosine_similarity": cosine_score,
        "metric_2_llm_judge": {
            **judge_result,
            "verdict": get_verdict(judge_result.get("final_score", 0)),
        },
    }


def compute_summary(results: list) -> dict:
    evaluated = [r for r in results if not r.get("skipped")]
    if not evaluated:
        return {"evaluated_stories": 0}

    def safe(r, key):
        j = r.get("metric_2_llm_judge", {})
        return None if j.get("error") else j.get(key)

    def avg(lst):
        vals = [v for v in lst if v is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    cosine_values       = [r.get("metric_1_cosine_similarity") for r in evaluated]
    coverage_vals       = [safe(r, "coverage_score")      for r in evaluated]
    missing_vals        = [safe(r, "missing_tests_score")  for r in evaluated]
    quality_vals        = [safe(r, "qa_quality_score")     for r in evaluated]
    similarity_vals     = [safe(r, "business_similarity")  for r in evaluated]
    final_vals          = [safe(r, "final_score")          for r in evaluated]
    verdicts            = [r.get("metric_2_llm_judge", {}).get("verdict") for r in evaluated if not r.get("metric_2_llm_judge", {}).get("error")]

    # Tableau détaillé par story
    per_story = []
    for r in evaluated:
        j = r.get("metric_2_llm_judge", {})
        per_story.append({
            "story_id":            r["story_id"],
            "user_story_title":    r.get("user_story_title", ""),
            "cosine_similarity":   r.get("metric_1_cosine_similarity"),
            "coverage_score":      j.get("coverage_score"),
            "missing_tests_score": j.get("missing_tests_score"),
            "qa_quality_score":    j.get("qa_quality_score"),
            "business_similarity": j.get("business_similarity"),
            "final_score":         j.get("final_score"),
            "verdict":             j.get("verdict"),
        })

    return {
        "evaluated_stories": len(evaluated),
        "skipped_stories": len(results) - len(evaluated),
        "averages": {
            "cosine_similarity":   avg(cosine_values),
            "coverage_score":      avg(coverage_vals),
            "missing_tests_score": avg(missing_vals),
            "qa_quality_score":    avg(quality_vals),
            "business_similarity": avg(similarity_vals),
            "final_score":         avg(final_vals),
        },
        "verdict_distribution": {
            "GOOD":    verdicts.count("GOOD"),
            "PARTIAL": verdicts.count("PARTIAL"),
            "BAD":     verdicts.count("BAD"),
        },
        "per_story_scores": per_story,
    }


def load_previous_results() -> dict:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"results": []}


def get_evaluated_story_ids(previous_results: dict) -> set:
    return {
        r["story_id"]
        for r in previous_results.get("results", [])
        if r.get("story_id")
    }


def main():
    print("=" * 60)
    print("Évaluation des Generated Tests vs Gold Tests")
    print("=" * 60)

    data = load_data()
    print(f"Stories chargées : {len(data)}")

    previous_results = load_previous_results()
    evaluated_ids = get_evaluated_story_ids(previous_results)
    print(f"Stories déjà évaluées : {len(evaluated_ids)}")

    # Charger le modèle sentence-transformers une seule fois
    st_model = None
    if ST_AVAILABLE:
        print(f"\nChargement du modèle sentence-transformers '{ST_MODEL_NAME}'...")
        try:
            st_model = SentenceTransformer(ST_MODEL_NAME)
            print("  Modèle chargé.")
        except Exception as e:
            print(f"  [WARN] Impossible de charger le modèle ST : {e}")

    results = previous_results.get("results", [])
    for story in data:
        story_id = story.get("story_id")
        if story_id in evaluated_ids:
            print(f"[{story_id}] déjà évaluée, skipped.")
            continue

        result = evaluate_story(story, st_model)
        results.append(result)
        # Petite pause entre les appels LLM pour éviter le rate-limit
        time.sleep(1)

    summary = compute_summary(results)

    output = {
        "evaluation_model": f"{JUDGE_MODEL} (GitHub Models) + paraphrase-multilingual-MiniLM-L12-v2",
        "summary": summary,
        "results": results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    avgs = summary.get("averages", {})
    verdicts = summary.get("verdict_distribution", {})

    print("\n" + "=" * 60)
    print("RÉSUMÉ GLOBAL")
    print("=" * 60)
    print(f"Stories évaluées             : {summary['evaluated_stories']}")
    print(f"Stories ignorées             : {summary.get('skipped_stories', 0)}")
    print()
    print(f"{'Métrique':<35} {'Moyenne':>8}")
    print("-" * 45)
    print(f"{'Cosine similarity':<35} {str(avgs.get('cosine_similarity', 'N/A')):>8}")
    print(f"{'Coverage score':<35} {str(avgs.get('coverage_score', 'N/A')):>8}")
    print(f"{'Missing tests score':<35} {str(avgs.get('missing_tests_score', 'N/A')):>8}")
    print(f"{'QA quality score':<35} {str(avgs.get('qa_quality_score', 'N/A')):>8}")
    print(f"{'Business similarity':<35} {str(avgs.get('business_similarity', 'N/A')):>8}")
    print(f"{'Final score (LLM Judge)':<35} {str(avgs.get('final_score', 'N/A')):>8}")
    print("-" * 45)
    print(f"\nVerdicts  → GOOD: {verdicts.get('GOOD', 0)} | PARTIAL: {verdicts.get('PARTIAL', 0)} | BAD: {verdicts.get('BAD', 0)}")

    print("\nDétail par story :")
    print(f"  {'Story ID':<18} {'Coverage':>9} {'Missing':>9} {'Quality':>9} {'BizSim':>8} {'Final':>7} {'Verdict':<9}")
    print("  " + "-" * 75)
    for row in summary.get("per_story_scores", []):
        print(
            f"  {row['story_id']:<18}"
            f" {str(row.get('coverage_score', '-')):>9}"
            f" {str(row.get('missing_tests_score', '-')):>9}"
            f" {str(row.get('qa_quality_score', '-')):>9}"
            f" {str(row.get('business_similarity', '-')):>8}"
            f" {str(row.get('final_score', '-')):>7}"
            f" {str(row.get('verdict', '-')):<9}"
        )

    print(f"\nRésultats sauvegardés → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()