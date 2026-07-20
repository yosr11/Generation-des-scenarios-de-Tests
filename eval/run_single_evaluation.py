#!/usr/bin/env python3
# eval/run_single_evaluation.py
import sys
import json
from pathlib import Path
import importlib.util

if len(sys.argv) < 2:
    print("Usage: python eval/run_single_evaluation.py <STORY_ID> [output_path]")
    sys.exit(1)

story_id = sys.argv[1]
out_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path("eval/results/generated_tests_evaluation_YOU-9098.json")

# locate module file
mod_path = Path("eval/comparaison_gold_test/evaluate_generated_tests.py").resolve()
spec = importlib.util.spec_from_file_location("eval_module", str(mod_path))
eval_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eval_mod)

# load original JSON data using the same loader (respects encodings)
data = eval_mod.load_data()
story = None
for s in data:
    if s.get("story_id") == story_id:
        story = s
        break

if not story:
    print(f"Story {story_id} not found in {eval_mod.JSON_FILE}")
    sys.exit(2)

# try to load sentence-transformers model if available (module handles failure)
st_model = None
try:
    if eval_mod.ST_AVAILABLE:
        from sentence_transformers import SentenceTransformer
        st_model = SentenceTransformer(eval_mod.ST_MODEL_NAME)
except Exception as e:
    print(f"[WARN] ST model not loaded: {e}")

# evaluate single story
result = eval_mod.evaluate_story(story, st_model)
summary = eval_mod.compute_summary([r for r in [result] if not r.get("skipped")])

output = {
    "evaluation_model": f"{eval_mod.JUDGE_MODEL} (GitHub Models) + {eval_mod.ST_MODEL_NAME}",
    "summary": summary,
    "results": [result],
}

out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Saved single-story evaluation → {out_path}")