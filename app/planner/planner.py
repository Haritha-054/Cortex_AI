
def create_plan(user_request: str) -> dict:
    """Convert a user request into a simple execution plan."""

    request = user_request.strip()

    if not request:
        return {
            "goal": "",
            "steps": [],
            "error": "Request cannot be empty"
        }

    request_lower = request.lower()

    if "meeting" in request_lower or "notes" in request_lower:
        agent = "meeting"
        action = "summarize_notes"
    elif "email" in request_lower:
        agent = "email"
        action = "process_email"
    elif "calendar" in request_lower or "schedule" in request_lower:
        agent = "calendar"
        action = "manage_calendar"
    else:
        agent = "general"
        action = "process_request"

    return {
        "goal": request,
        "steps": [
            {
                "step_id": 1,
                "agent": agent,
                "action": action
            }
        ],
        "error": None
    }
