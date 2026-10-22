import re

# Risk score thresholds for human approval governance
AUTO_APPROVE_THRESHOLD = 30  # <= 30 is automatically approved
HIGH_RISK_THRESHOLD = 70     # > 70 requires administrator-level approval

# Permissions for each role.
# An action must be explicitly listed to be permitted.
ROLE_PERMISSIONS = {
    "admin": {
        "process_request",
        "process_email",
        "manage_calendar",
        "summarize_notes",
        "manage_drive",
        "manage_tasks",
        "manage_slack",
    },
    "manager": {
        "process_request",
        "process_email",
        "manage_calendar",
        "summarize_notes",
        "manage_tasks",
    },
    "employee": {
        "process_request",
        "process_email",
        "summarize_notes",
        "manage_calendar",
        "manage_tasks",
    },
}

# Prompt-injection patterns to protect planning and agent execution.
INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|system) instructions",
    r"disregard (all )?(previous|prior|system) instructions",
    r"forget (all )?(previous|prior|system) instructions",
    r"reveal (the )?(system prompt|hidden instructions|internal rules)",
    r"bypass (all )?(security|safety|access|authorization) controls",
    r"ignore your (rules|guidelines)",
    r"override your (rules|instructions|system prompt)",
    r"\bjailbreak\b",
    r"\bdan mode\b",
]


def validate_request(user_id: str, user_request: str) -> dict:
    """Validate a user's ID and request before planning."""
    if not user_id or not user_id.strip():
        return {
            "allowed": False,
            "reason": "User ID cannot be empty",
        }

    if not user_request or not user_request.strip():
        return {
            "allowed": False,
            "reason": "Request cannot be empty",
        }

    if len(user_request) > 5000:
        return {
            "allowed": False,
            "reason": "Request is too long",
        }

    normalized = user_request.lower()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            return {
                "allowed": False,
                "reason": "Potential prompt-injection instruction detected",
            }

    return {
        "allowed": True,
        "reason": "Request validated successfully",
    }


def authorize_action(role: str, action: str) -> dict:
    """Check whether a role is allowed to perform an action."""
    normalized_role = role.strip().lower() if role else ""
    normalized_action = action.strip().lower() if action else ""

    permissions = ROLE_PERMISSIONS.get(normalized_role, set())

    if normalized_action not in permissions:
        return {
            "allowed": False,
            "reason": (
                f"Role '{normalized_role or 'unknown'}' "
                f"does not have permission for action "
                f"'{normalized_action or 'unknown'}'"
            ),
        }

    return {
        "allowed": True,
        "reason": "Permission granted",
    }


def calculate_risk_score(action: str, user_request: str) -> int:
    """Calculate an action risk score from 0 to 100."""
    score = 10
    normalized_action = (action or "").lower()
    normalized_request = (user_request or "").lower()

    # Actions that can affect external systems or data.
    if normalized_action in {
        "process_email",
        "manage_calendar",
        "manage_drive",
        "manage_tasks",
        "manage_slack",
    }:
        score += 20

    # Potentially sensitive or consequential operations.
    if any(
        word in normalized_request
        for word in (
            "delete",
            "send",
            "share",
            "external",
            "permanently",
        )
    ):
        score += 25

    if any(
        word in normalized_request
        for word in (
            "password",
            "secret",
            "confidential",
            "personal data",
        )
    ):
        score += 30

    return min(score, 100)


def approval_decision(risk_score: int) -> dict:
    """
    Decide whether an action requires human approval based on 30 / 70 risk tiers:
    - 0 to 30: Low risk -> Auto-approved
    - 31 to 70: Medium risk -> Human approval required (manager or admin)
    - 71 to 100: High risk -> Administrator approval strictly required
    """
    if not isinstance(risk_score, int) or isinstance(risk_score, bool):
        raise ValueError("Risk score must be an integer")

    if not 0 <= risk_score <= 100:
        raise ValueError("Risk score must be between 0 and 100")

    if risk_score <= AUTO_APPROVE_THRESHOLD:
        return {
            "approved": True,
            "requires_human_approval": False,
            "tier": "low",
            "required_role": "none",
            "reason": "Low risk (<= 30): automatically approved",
        }

    if risk_score <= HIGH_RISK_THRESHOLD:
        return {
            "approved": False,
            "requires_human_approval": True,
            "tier": "medium",
            "required_role": "manager",
            "reason": f"Medium risk ({risk_score}/100): manager or admin approval required",
        }

    return {
        "approved": False,
        "requires_human_approval": True,
        "tier": "high",
        "required_role": "admin",
        "reason": f"High risk ({risk_score}/100): administrator approval strictly required",
    }
