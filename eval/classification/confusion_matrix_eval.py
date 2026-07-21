# eval/confusion_matrix_eval.py
import argparse
import json
from sklearn.metrics import confusion_matrix, classification_report, f1_score


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def print_confusion_and_report(y_true, y_pred, labels, title):
    print(f"\n==== {title} ====")
    print("Matrice de confusion :")
    print(confusion_matrix(y_true, y_pred, labels=labels))
    print("\nClassification report :")
    print(classification_report(y_true, y_pred, labels=labels, zero_division=0))


def main():
    parser = argparse.ArgumentParser(
        description="Évaluation Agent 1 (classification story_type)"
    )
    parser.add_argument(
        "--gold",
        default="annotations.json",
        help="Chemin du fichier d'annotations (gold)",
    )
    parser.add_argument(
        "--pred",
        default="results/agent1_classification_output.json",
        help="Chemin du fichier de prédictions de l'agent 1",
    )
    args = parser.parse_args()

    # --- Charger gold ---
    gold_raw = load_json(args.gold)

    # Support {"stories_test_strategy": [...]} ou liste directe
    if isinstance(gold_raw, dict):
        stories = gold_raw.get("stories_test_strategy") or gold_raw.get("stories") or []
    else:
        stories = gold_raw
    gold = {s["story_id"]: s["story_type"] for s in stories}

    # --- Charger prédictions ---
    pred_raw = load_json(args.pred)

    # Support {"stories": [...]} ou liste directe
    if isinstance(pred_raw, dict):
        preds = pred_raw.get("stories") or pred_raw.get("results") or []
    else:
        preds = pred_raw
    pred = {s["story_id"]: s["story_type"] for s in preds}

    # --- Intersection ---
    common_ids = sorted(set(gold) & set(pred))
    only_gold = set(gold) - set(pred)
    only_pred = set(pred) - set(gold)

    print(f"Stories dans gold           : {len(gold)}")
    print(f"Stories dans pred           : {len(pred)}")
    print(f"Stories en commun (évaluées): {len(common_ids)}")
    if only_gold:
        print(f"Stories gold sans prédiction: {sorted(only_gold)}")
    if only_pred:
        print(f"Stories pred sans annotation: {sorted(only_pred)}")

    if not common_ids:
        print("\nAucune story en commun — vérifier les story_id.")
        return

    y_true = [gold[i] for i in common_ids]
    y_pred = [pred[i] for i in common_ids]
    labels = sorted(set(y_true + y_pred))

    print_confusion_and_report(y_true, y_pred, labels, "Story Type")

    # --- Détail des erreurs ---
    errors = [
        (sid, gold[sid], pred[sid]) for sid in common_ids if gold[sid] != pred[sid]
    ]
    if errors:
        print(f"\n==== Erreurs de classification ({len(errors)}) ====")
        for sid, true, predicted in errors:
            print(f"  {sid:30s}  gold={true:25s}  pred={predicted}")
    else:
        print("\nAucune erreur — classification parfaite.")

    # --- Macro F1 & Weighted F1 ---
    macro_f1 = f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    weighted_f1 = f1_score(
        y_true, y_pred, labels=labels, average="weighted", zero_division=0
    )
    print("\n==== Métriques globales ====")
    print(f"Macro F1    : {macro_f1:.4f}")
    print(f"Weighted F1 : {weighted_f1:.4f}")

    # --- Accuracy simple ---
    correct = sum(1 for sid in common_ids if gold[sid] == pred[sid])
    print(f"Accuracy    : {correct}/{len(common_ids)} = {correct/len(common_ids):.2%}")


if __name__ == "__main__":
    main()
