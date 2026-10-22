
import pytest

from backend.agents.plan_validator import validate_plan


def valid_plan():
    return {
        "goal": "Summarize meeting notes and draft an email",
        "intent": "meeting_follow_up",
        "steps": [
            {
                "step_id": 1,
                "agent": "meeting",
                "action": "summarize_notes",
                "objective": "Summarize the notes",
                "inputs": ["meeting_notes"],
                "expected_output": "A meeting summary",
                "depends_on": [],
                "validation": ["Use supplied notes only"],
                "risk_hint": "low",
            },
            {
                "step_id": 2,
                "agent": "email",
                "action": "process_email",
                "objective": "Draft a follow-up email",
                "inputs": ["summary from step 1"],
                "expected_output": "An email draft",
                "depends_on": [1],
                "validation": ["Do not send the email"],
                "risk_hint": "low",
            },
        ],
    }


def test_valid_plan():
    plan = validate_plan(valid_plan())
    assert len(plan["steps"]) == 2


def test_duplicate_step_id_rejected():
    plan = valid_plan()
    plan["steps"][1]["step_id"] = 1

    with pytest.raises(ValueError):
        validate_plan(plan)


def test_unknown_dependency_rejected():
    plan = valid_plan()
    plan["steps"][1]["depends_on"] = [99]

    with pytest.raises(ValueError):
        validate_plan(plan)


def test_missing_objective_rejected():
    plan = valid_plan()
    del plan["steps"][0]["objective"]

    with pytest.raises(ValueError):
        validate_plan(plan)


def test_unknown_agent_rejected():
    plan = valid_plan()
    plan["steps"][0]["agent"] = "unknown_agent"

    with pytest.raises(ValueError):
        validate_plan(plan)
