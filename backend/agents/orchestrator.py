from backend.agents.planner import create_plan
from backend.agents.agent_registry import AGENT_REGISTRY

def execute_request(user_request: str) -> dict:
    """Plan and execute a request in order, respecting step dependencies."""
    plan = create_plan(user_request)
    if plan.get("error"):
        return {"status": "failed", "plan": plan, "results": [], "error": plan["error"]}

    results = []
    result_by_step = {}
    overall_status = "success"

    for step in plan["steps"]:
        step_id = step["step_id"]
        agent_name = step["agent"]
        action = step["action"]

        # A dependent step must not run if one of its prerequisites failed.
        failed_dependencies = [
            dep for dep in step.get("depends_on", [])
            if result_by_step.get(dep, {}).get("status") != "success"
        ]
        if failed_dependencies:
            item = {
                "step_id": step_id, "agent": agent_name, "action": action,
                "status": "failed",
                "message": f"Skipped because dependency step(s) failed: {failed_dependencies}",
            }
            results.append(item)
            result_by_step[step_id] = item
            overall_status = "failed"
            continue

        agent_function = AGENT_REGISTRY.get(agent_name)
        if agent_function is None:
            item = {
                "step_id": step_id, "agent": agent_name, "action": action,
                "status": "failed", "message": "Agent is not registered",
            }
            results.append(item)
            result_by_step[step_id] = item
            overall_status = "failed"
            continue

        try:
            agent_result = agent_function(
                action=action,
                goal=plan["goal"],
                objective=step.get("objective", ""),
                inputs=step.get("inputs", []),
                expected_output=step.get("expected_output", ""),
                prior_results={dep: result_by_step.get(dep) for dep in step.get("depends_on", [])},
            )
            step_status = agent_result.get("status", "failed")
            item = {
                "step_id": step_id,
                "agent": agent_name,
                "action": action,
                "status": step_status,
                "message": agent_result.get("message", ""),
                "details": agent_result,
            }
        except Exception as exc:
            item = {
                "step_id": step_id, "agent": agent_name, "action": action,
                "status": "failed", "message": str(exc),
            }

        results.append(item)
        result_by_step[step_id] = item
        if item["status"] != "success":
            overall_status = "failed"

    return {
        "status": overall_status,
        "plan": plan,
        "results": results,
        "error": None if overall_status == "success" else "One or more agent steps failed",
    }
