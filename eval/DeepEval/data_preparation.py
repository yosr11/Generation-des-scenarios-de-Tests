import json
from pathlib import Path
from typing import Any, Dict, List


def load_eval_stories(input_path: str | Path) -> List[Dict[str, Any]]:
    path = Path(input_path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        if "results" in data:
            data = data["results"]
        elif "stories" in data:
            data = data["stories"]
        else:
            raise ValueError(
                "Le JSON doit contenir une liste de stories ou une clé 'results'/'stories'."
            )

    stories: List[Dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and "story_id" in item:
            stories.append(normalize_story(item))
        elif isinstance(item, dict) and "story" in item:
            stories.append(normalize_story(item["story"]))
    return stories


def normalize_story(story: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(story)
    for key in ["agent1", "agent2", "agent3", "agent4", "agent5"]:
        value = normalized.get(key, {})
        if not isinstance(value, dict):
            normalized[key] = {"output": value}
    return normalized


def serialize_payload(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def collect_agent_payloads(story: Dict[str, Any]) -> Dict[str, str]:
    output: Dict[str, str] = {}
    for key in ["agent1", "agent2", "agent3", "agent4", "agent5"]:
        agent = story.get(key, {})
        if isinstance(agent, dict):
            output[key] = serialize_payload(agent.get("output", {}))
        else:
            output[key] = serialize_payload(agent)

    input_payload = (
        story.get("agent1", {}).get("input", {})
        if isinstance(story.get("agent1"), dict)
        else {}
    )
    output["agent1_input"] = serialize_payload(input_payload)
    return output
