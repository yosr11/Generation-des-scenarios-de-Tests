#!/usr/bin/env python3
"""
Normalise evalAgents.json :
- Agent 2 : convertit output (array) → output (dict avec clé "tests")
"""

import json
from pathlib import Path

def normalize_agent2_output(story):
    """
    Normalise Agent 2 output : array → dict
    
    Avant :
    "agent2": { "output": [{ "test_name": "...", "steps": [...] }, ...] }
    
    Après :
    "agent2": { "output": { "tests": [{ "test_name": "...", "steps": [...] }, ...] } }
    """
    if "agent2" not in story:
        return story
    
    agent2 = story["agent2"]
    
    # Vérifier si output est une liste
    if isinstance(agent2.get("output"), list):
        print(f"  ✅ Story {story.get('story_id', 'UNKNOWN')}: Agent 2 output est un array → conversion en dict")
        agent2["output"] = {
            "tests": agent2["output"],
            "_normalized": True  # Flag pour tracking
        }
    
    return story


def main():
    json_path = Path("c:\\Users\\yomahfoudh\\Desktop\\Agent_Test\\eval\\DeepEval\\evalAgents.json")
    
    print(f"📖 Lecture {json_path}...")
    with open(json_path, "r", encoding="utf-8") as f:
        stories = json.load(f)
    
    print(f"📊 Total stories : {len(stories)}")
    print("\n🔧 Normalisation Agent 2...\n")
    
    # Normaliser chaque story
    for i, story in enumerate(stories, 1):
        normalize_agent2_output(story)
    
    # Sauvegarder
    backup_path = json_path.with_stem(f"{json_path.stem}.backup")
    print(f"\n💾 Backup → {backup_path.name}")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Écriture normalisée → {json_path.name}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=2)
    
    print("\n✅ Normalisation terminée !")
    print("\nExemple structure après normalisation :")
    print(json.dumps({
        "agent2": {
            "output": {
                "tests": [
                    {"test_name": "Test 1", "steps": [...]},
                    {"test_name": "Test 2", "steps": [...]}
                ],
                "_normalized": True
            }
        }
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
