
from backend.agents.planner import create_plan


def test_empty_request():
    result = create_plan(" ")
    assert result["error"] == "Request cannot be empty"
    assert result["steps"] == []


def test_email_request():
    result = create_plan("Draft an email")
    assert result["error"] is None
    assert result["steps"][0]["agent"] == "email"


def test_multi_agent_request():
    result = create_plan(
        "Schedule a meeting, prepare meeting notes, and send an email"
    )

    agents = [step["agent"] for step in result["steps"]]

    assert agents == ["calendar", "meeting", "email"]
    assert result["error"] is None


if __name__ == "__main__":
    test_empty_request()
    test_email_request()
    test_multi_agent_request()
    print("All planner tests passed!")
