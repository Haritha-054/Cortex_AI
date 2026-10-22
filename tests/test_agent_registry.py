
from unittest.mock import patch

from backend.agents.agent_registry import (
    execute_meeting,
    execute_email,
)


def test_meeting_summary_uses_supplied_notes():
    notes = "Ravi will finish testing by Friday."

    with patch(
        "backend.agents.agent_registry._call_ollama",
        return_value="Action item: Ravi finishes testing by Friday.",
    ):
        result = execute_meeting(
            action="summarize_notes",
            goal="Summarize notes",
            user_context={"meeting_notes": notes},
        )

    assert result["status"] == "success"
    assert "summary" in result["details"]
    assert result["details"]["execution_mode"] == "ollama"


def test_meeting_fails_without_notes():
    result = execute_meeting(
        action="summarize_notes",
        goal="Summarize notes",
        user_context={},
        inputs=[],
    )

    assert result["status"] == "failed"


def test_email_uses_meeting_dependency():
    dependencies = {
        1: {
            "status": "success",
            "details": {"summary": "Testing is due Friday."},
        }
    }

    with patch(
        "backend.agents.agent_registry._call_ollama",
        return_value="Subject: Testing update\n\nHi team...",
    ):
        result = execute_email(
            action="process_email",
            goal="Draft follow-up",
            dependency_results=dependencies,
        )

    assert result["status"] == "success"
    assert "email_draft" in result["details"]
    assert result["details"]["sent"] is False


def test_email_fails_without_summary():
    result = execute_email(
        action="process_email",
        goal="Draft follow-up",
        dependency_results={},
        prior_results={},
        user_context={},
    )

    assert result["status"] == "failed"


def test_email_skipped_when_meeting_summary_fails():
    from backend.main import execute_approved_plan

    plan = {
        "goal": "Summarize meeting notes and draft an email",
        "intent": "meeting_follow_up",
        "steps": [
            {
                "step_id": 1,
                "agent": "meeting",
                "action": "summarize_notes",
                "objective": "Summarize the notes",
                "inputs": [],
                "expected_output": "A meeting summary",
                "depends_on": [],
                "user_context": {},  # Meeting notes missing -> meeting agent fails
            },
            {
                "step_id": 2,
                "agent": "email",
                "action": "process_email",
                "objective": "Draft a follow-up email",
                "inputs": ["summary from step 1"],
                "expected_output": "An email draft",
                "depends_on": [1],
                "user_context": {},
            },
        ],
    }

    execution = execute_approved_plan(plan)
    assert execution["status"] == "failed"
    assert len(execution["results"]) == 2

    meeting_step = execution["results"][0]
    email_step = execution["results"][1]

    assert meeting_step["agent"] == "meeting"
    assert meeting_step["status"] == "failed"

    assert email_step["agent"] == "email"
    assert email_step["status"] == "skipped"
    assert 1 in email_step["blocked_by"]


def test_calendar_agent_dispatch():
    from backend.agents.agent_registry import execute_calendar

    result = execute_calendar(
        action="manage_calendar",
        goal="Schedule review meeting",
    )
    assert result["status"] == "success"
    assert result["agent"] == "calendar"
    assert result["details"]["execution_mode"] == "simulated"


def test_general_agent_dispatch():
    from backend.agents.agent_registry import execute_general

    result = execute_general(
        action="process_request",
        goal="Analyze quarterly metrics",
        objective="Analyze quarterly metrics",
    )
    assert result["status"] == "success"
    assert result["agent"] == "general"
    assert result["details"]["execution_mode"] == "simulated"


def test_all_expected_agent_mappings_exist():
    from backend.agents.agent_registry import AGENT_REGISTRY

    expected_agents = {"meeting", "email", "calendar", "general"}
    assert set(AGENT_REGISTRY.keys()) == expected_agents

    for agent_name, agent_func in AGENT_REGISTRY.items():
        assert callable(agent_func), f"Agent {agent_name} must be callable"


