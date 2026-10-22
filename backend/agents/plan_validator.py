
from typing import Any


ALLOWED_AGENTS = {
    "meeting",
    "email",
    "calendar",
    "general",
}


REQUIRED_STEP_FIELDS = {
    "step_id",
    "agent",
    "action",
    "objective",
    "inputs",
    "expected_output",
    "depends_on",
}


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, dict):
        raise ValueError("Planner output must be a JSON object.")

    if not isinstance(plan.get("goal"), str) or not plan["goal"].strip():
        raise ValueError("Plan must contain a non-empty goal.")

    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("Plan must contain a non-empty steps list.")

    if len(steps) > 20:
        raise ValueError("Plan exceeds the maximum of 20 steps.")

    seen_ids = set()

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError(f"Step {index + 1} must be an object.")

        missing = REQUIRED_STEP_FIELDS - step.keys()
        if missing:
            raise ValueError(
                f"Step {index + 1} is missing: {sorted(missing)}"
            )

        step_id = step["step_id"]

        if not isinstance(step_id, int) or isinstance(step_id, bool):
            raise ValueError("step_id must be an integer.")

        if step_id in seen_ids:
            raise ValueError(f"Duplicate step_id: {step_id}")

        if step["agent"] not in ALLOWED_AGENTS:
            raise ValueError(
                f"Unsupported agent: {step['agent']}"
            )

        if not isinstance(step["action"], str) or not step["action"].strip():
            raise ValueError(f"Step {step_id} has an invalid action.")

        if not isinstance(step["objective"], str):
            raise ValueError(f"Step {step_id} objective must be text.")

        if not isinstance(step["inputs"], list):
            raise ValueError(f"Step {step_id} inputs must be a list.")

        if not isinstance(step["expected_output"], str):
            raise ValueError(
                f"Step {step_id} expected_output must be text."
            )

        dependencies = step["depends_on"]
        if not isinstance(dependencies, list):
            raise ValueError(
                f"Step {step_id} depends_on must be a list."
            )

        if len(dependencies) != len(set(dependencies)):
            raise ValueError(
                f"Step {step_id} has duplicate dependencies."
            )

        # This implementation executes steps in list order.
        for dep in dependencies:
            if dep not in seen_ids:
                raise ValueError(
                    f"Step {step_id} depends on unknown or later step {dep}."
                )

        step.setdefault("validation", [])
        step.setdefault("risk_hint", "unknown")

        if not isinstance(step["validation"], list):
            raise ValueError(
                f"Step {step_id} validation must be a list."
            )

        if step["risk_hint"] not in {
            "low", "medium", "high", "unknown"
        }:
            raise ValueError(
                f"Step {step_id} has an invalid risk_hint."
            )

        seen_ids.add(step_id)

    return plan
