
from backend.agents.planner import create_plan


request = "Schedule a meeting and send an email"

result = create_plan(request)

print("\nPLANNER OUTPUT:")
print(result)

assert result["error"] is None, result["error"]

agents = [step["agent"] for step in result["steps"]]

assert "calendar" in agents
assert "email" in agents

print("\nQwen planner test passed!")
