from pathlib import Path
from typing import Any, Dict, List

from deepeval.test_case import ConversationalTestCase, Turn

from eval.DeepEval.data_preparation import collect_agent_payloads, load_eval_stories


def build_conversational_case(story: Dict[str, Any]) -> ConversationalTestCase:
    story_id = str(story.get("story_id", "unknown"))
    payloads = collect_agent_payloads(story)

    turns = [
        Turn(
            role="user", content=f"User story {story_id}\n\n{payloads['agent1_input']}"
        ),
        Turn(role="assistant", content=payloads["agent1"]),
        Turn(
            role="user", content="Refine the business model and workflow from Agent 1."
        ),
        Turn(role="assistant", content=payloads["agent2"]),
        Turn(role="user", content="Generate test cases from the business model."),
        Turn(role="assistant", content=payloads["agent3"]),
        Turn(
            role="user",
            content="Validate the generated tests and highlight gaps or ambiguities.",
        ),
        Turn(role="assistant", content=payloads["agent4"]),
        Turn(role="user", content="Produce the final QA report with recommendations."),
        Turn(role="assistant", content=payloads["agent5"]),
    ]

    return ConversationalTestCase(
        turns=turns,
        name=story_id,
        scenario="Multi-agent Jira story evaluation",
        metadata={"story_id": story_id},
    )


def build_conversational_cases(
    input_path: str | Path, max_cases: int | None = None
) -> List[ConversationalTestCase]:
    stories = load_eval_stories(input_path)
    if max_cases is not None:
        stories = stories[:max_cases]
    return [build_conversational_case(story) for story in stories]


def export_case_summary(
    cases: List[ConversationalTestCase], output_path: str | Path
) -> None:
    payload = []
    for case in cases:
        payload.append(
            {
                "name": case.name,
                "scenario": case.scenario,
                "turn_count": len(case.turns),
                "metadata": case.metadata,
            }
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        import json

        json.dump(payload, handle, ensure_ascii=False, indent=2)
