
from backend.agents.orchestrator import execute_request
from unittest.mock import patch


def test_single_agent_request():
    result = execute_request("Process my email")

    assert result["status"] == "success"
    assert len(result["plan"]["steps"]) == 1
    assert result["results"][0]["agent"] == "email"
    assert result["results"][0]["status"] == "success"


def test_multi_agent_request():
    result = execute_request(
        "Schedule a meeting and send an email"
    )

    assert result["status"] == "success"

    agents = [
        step["agent"]
        for step in result["results"]
    ]

    assert agents == ["calendar", "email"]
    assert len(result["results"]) == 2


def test_empty_request():
    result = execute_request("")

    assert result["status"] == "failed"
    assert result["results"] == []
    assert result["error"] == "Request cannot be empty"


def test_agent_failure():
    with patch(
        "backend.agents.orchestrator.AGENT_REGISTRY",
        {
            "email": lambda action, goal: {
                "status": "failed",
                "message": "Simulated email failure",
            }
        },
    ):
        result = execute_request("Process my email")

    assert result["status"] == "failed"
    assert result["results"][0]["status"] == "failed"
    assert result["error"] == "One or more agent steps failed"

def test_unknown_agent():
    with patch(
        "backend.agents.orchestrator.create_plan",
        return_value={
            "goal": "Test unknown agent",
            "steps": [
                {
                    "step_id": 1,
                    "agent": "unknown_agent",
                    "action": "test_action",
                }
            ],
            "error": None,
        },
    ):
        result = execute_request("Test unknown agent")

    assert result["status"] == "failed"
    assert result["results"][0]["status"] == "failed"
    assert result["results"][0]["message"] == "Agent is not registered"


if __name__ == "__main__":
    test_single_agent_request()
    test_multi_agent_request()
    test_empty_request()
    test_agent_failure()

    print("All orchestrator tests passed!")
