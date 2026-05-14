import json

def one_to_one_match(pred, gold, match_fn):
    tp = fp = fn = 0
    matched_gold = set()
    for p in pred:
        found = False
        for i, g in enumerate(gold):
            if i not in matched_gold and match_fn(p, g):
                tp += 1
                matched_gold.add(i)
                found = True
                break
        if not found:
            fp += 1
    fn = len(gold) - len(matched_gold)
    return tp, fp, fn

def exact_match(a, b):
    return a.strip().lower() == b.strip().lower()

def semantic_match(a, b):
    # Matching simple basé sur les mots communs
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    if not a_words or not b_words:
        return False
    overlap = len(a_words & b_words) / max(len(a_words), len(b_words))
    return overlap >= 0.5

def compute_metrics(tp, fp, fn, total_gold, total_pred):
    precision = tp / total_pred if total_pred > 0 else 0
    recall    = tp / total_gold if total_gold > 0 else 0
    f1        = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "total_gold": total_gold,
        "total_pred": total_pred,
        "precision": round(precision, 3),
        "recall":    round(recall, 3),
        "f1":        round(f1, 3),
    }

def evaluate(gold_path, pred_path):
    with open(gold_path, encoding="utf-8") as f:
        gold_data = json.load(f)
    with open(pred_path, encoding="utf-8") as f:
        pred_data = json.load(f)

    gold_stories = {s["story_id"]: s for s in gold_data}
    pred_stories = {s["analysis"]["story_id"]: s["analysis"] for s in pred_data["results"]}

    field_metrics = {}
    error_types   = set()

    for field in ["actors", "actions", "business_rules", "acceptance_criteria"]:
        tp = fp = fn = total_gold = total_pred = 0

        for sid, gold_story in gold_stories.items():
            pred_story = pred_stories.get(sid, {})

            if field == "acceptance_criteria":
                gold_items = (gold_story.get("acceptance_criteria_explicit", [])
                            + gold_story.get("acceptance_criteria_inferred", []))
                pred_items = (pred_story.get("acceptance_criteria_explicit", [])
                            + pred_story.get("acceptance_criteria_inferred", []))
            else:
                gold_items = gold_story.get(field, [])
                pred_items = pred_story.get(field, [])

            total_gold += len(gold_items)
            total_pred += len(pred_items)

            match_fn = exact_match if field == "actors" else semantic_match
            t, f, n  = one_to_one_match(pred_items, gold_items, match_fn)
            tp += t; fp += f; fn += n

            if n > 0:
                error_types.add(f"missing {field}")
            if f > 0:
                error_types.add(f"hallucinated {field}")
            if field != "actors" and t < len(gold_items):
                error_types.add(f"weak semantic matching for {field}")

        field_metrics[field] = compute_metrics(tp, fp, fn, total_gold, total_pred)

    macro_f1              = sum(m["f1"]        for m in field_metrics.values()) / len(field_metrics)
    overall_quality_score = sum(m["precision"] for m in field_metrics.values()) / len(field_metrics)

    return {
        **field_metrics,
        "global_summary": {
            "macro_f1":             round(macro_f1, 3),
            "overall_quality_score": round(overall_quality_score, 3),
        },
        "error_analysis": {
            "main_errors": sorted(error_types)
        }
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", required=True)
    parser.add_argument("--pred", required=True)
    parser.add_argument("--out",  required=False)
    args = parser.parse_args()

    result = evaluate(args.gold, args.pred)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))