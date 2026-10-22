import json
from datetime import datetime, timezone
from typing import Any
from backend.agents.plan_validator import validate_plan
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.agents.auth_agent import (
    create_access_token,
    verify_access_token,
    authenticate_user,
    USERS_DB,
)
from backend.agents.security_agent import (
    validate_request,
    authorize_action,
    calculate_risk_score,
    approval_decision,
    AUTO_APPROVE_THRESHOLD,
    HIGH_RISK_THRESHOLD,
)
from backend.agents.planner import create_plan
from backend.agents.agent_registry import AGENT_REGISTRY
from backend.db.base import SessionLocal
from fastapi.middleware.cors import CORSMiddleware
from backend.db.models_core import TaskLog, AuditLog, AgentExecutionLog
from backend.schemas.contracts import RunRequest, RunResponse
from backend.routers import transcribe as transcribe_router
app = FastAPI(
    title="Enterprise AI Automation",
    description="Planner, Orchestrator, Security and Governance API",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(transcribe_router.router)
bearer_scheme = HTTPBearer(auto_error=False)
# ---------------------------------------------------------
# DEMO ROLE CONFIGURATION
# ---------------------------------------------------------
# IMPORTANT:
# This is only for local development and demonstration.
# Replace it with verified identity and role information
# from a real authentication provider before production use.
#
# Unknown users receive the employee role.
# Do not accept a role directly from /run-request JSON.
# ---------------------------------------------------------
USER_ROLES = {
    "admin": "admin",
    "manager": "manager",
}
def get_user_role(user_id: str) -> str:
    user = USERS_DB.get(user_id)
    if user and user.get("role"):
        return user["role"]
    return USER_ROLES.get(user_id, "employee")
# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------
class TokenRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    password: str | None = Field(default=None, max_length=100)
class ApprovalRequest(BaseModel):
    approved: bool
    comments: str = Field(default="", max_length=1000)
# ---------------------------------------------------------
# DATABASE HELPERS
# ---------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def write_audit(
    db: Session,
    user_id: str,
    action: str,
    details: dict[str, Any],
) -> None:
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            details=json.dumps(details, default=str),
        )
    )
def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None,
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization token",
        )
    result = verify_access_token(credentials.credentials)
    if not result.get("valid") or not result.get("user_id"):
        raise HTTPException(
            status_code=401,
            detail=result.get("error") or "Invalid token",
        )
    return result["user_id"]
# ---------------------------------------------------------
# RISK SCORING
# ---------------------------------------------------------
def assess_plan(plan: dict[str, Any], user_request: str) -> dict:
    """
    Assess every planned action.
    The request-level risk is the maximum action risk.
    """
    steps = plan.get("steps", [])
    if not steps:
        raise HTTPException(
            status_code=400,
            detail=plan.get("error") or "Planner returned no executable steps",
        )
    assessed_steps = []
    max_risk = 0
    for step in steps:
        agent = step.get("agent", "")
        action = step.get("action", "")
        if agent not in AGENT_REGISTRY:
            raise HTTPException(
                status_code=400,
                detail=f"Unregistered agent: {agent}",
            )
        risk = calculate_risk_score(action, user_request)
        max_risk = max(max_risk, risk)
        assessed_steps.append({
            **step,
            "risk_score": risk,
        })
    plan["steps"] = assessed_steps
    return {
        "risk_score": max_risk,
        "steps": assessed_steps,
    }
# ---------------------------------------------------------
# PLAN EXECUTION
# ---------------------------------------------------------
def execute_approved_plan(plan: dict[str, Any]) -> dict:
    """
    Execute the stored plan in order.
    Respect depends_on and pass previous results to dependent agents.
    """
    results = []
    results_by_step_id = {}
    overall_status = "success"
    goal = plan.get("goal", "")
    for step in plan.get("steps", []):
        step_id = step.get("step_id")
        agent_name = step.get("agent", "")
        action = step.get("action", "")
        dependencies = step.get("depends_on", []) or []
        agent_function = AGENT_REGISTRY.get(agent_name)
        # 1. Check whether every dependency completed successfully.
        failed_dependencies = [
            dep_id
            for dep_id in dependencies
            if dep_id not in results_by_step_id
            or results_by_step_id[dep_id].get("status") != "success"
        ]
        # 2. Skip this step if any dependency failed or was skipped.
        if failed_dependencies:
            item = {
                "step_id": step_id,
                "agent": agent_name,
                "action": action,
                "status": "skipped",
                "risk_score": step.get("risk_score"),
                "message": (
                    "Step skipped because dependency step(s) "
                    "did not succeed: "
                    + ", ".join(str(dep_id) for dep_id in failed_dependencies)
                ),
                "blocked_by": failed_dependencies,
                "details": {},
            }
            results.append(item)
            results_by_step_id[step_id] = item
            overall_status = "failed"
            continue
        # 3. Handle an unregistered agent.
        if agent_function is None:
            item = {
                "step_id": step_id,
                "agent": agent_name,
                "action": action,
                "status": "failed",
                "risk_score": step.get("risk_score"),
                "message": "Agent is not registered",
                "details": {},
            }
            results.append(item)
            results_by_step_id[step_id] = item
            overall_status = "failed"
            continue
        # 4. Collect the results of direct dependencies.
        dependency_results = {
            dep_id: results_by_step_id[dep_id]
            for dep_id in dependencies
        }
        # 5. Collect all previous successful step results.
        prior_results = {
            str(previous_id): previous_result
            for previous_id, previous_result in results_by_step_id.items()
            if previous_result.get("status") == "success"
        }
        # 6. Execute the agent and pass its required context.
        try:
            agent_result = agent_function(
                action=action,
                goal=goal,
                objective=step.get("objective", ""),
                inputs=step.get("inputs", []),
                expected_output=step.get("expected_output", ""),
                depends_on=dependencies,
                dependency_results=dependency_results,
                prior_results=prior_results,
                user_context=step.get("user_context", {}),
            )
            if not isinstance(agent_result, dict):
                raise TypeError("Agent must return a dictionary")
            agent_status = agent_result.get("status")
            if agent_status not in {"success", "failed"}:
                raise ValueError(
                    "Agent must return status='success' or status='failed'"
                )
            details = agent_result.get("details", {})
            if not isinstance(details, dict):
                raise ValueError("Agent details must be a dictionary")
            item = {
                "step_id": step_id,
                "agent": agent_name,
                "action": action,
                "status": agent_status,
                "risk_score": step.get("risk_score"),
                "message": agent_result.get("message", ""),
                "details": details,
                "error": agent_result.get("error") or details.get("error"),
            }
            results.append(item)
            results_by_step_id[step_id] = item
            if agent_status == "failed":
                overall_status = "failed"
        except Exception as exc:
            item = {
                "step_id": step_id,
                "agent": agent_name,
                "action": action,
                "status": "failed",
                "risk_score": step.get("risk_score"),
                "message": f"Agent execution failed: {type(exc).__name__}",
                "details": {},
                "error": str(exc),
            }
            results.append(item)
            results_by_step_id[step_id] = item
            overall_status = "failed"
    return {
        "status": overall_status,
        "results": results,
        "error": (
            None
            if overall_status == "success"
            else "One or more agent steps failed or were skipped"
        ),
    }
# ---------------------------------------------------------
# BASIC ENDPOINTS
# ---------------------------------------------------------
@app.get("/")
def home():
    return {
        "message": "Enterprise AI Automation API is running!"
    }
@app.get("/health")
def health_check():
    return {
        "status": "success",
        "details": {"service": "backend"},
        "error": None,
    }
# ---------------------------------------------------------
# TOKEN ENDPOINT
# ---------------------------------------------------------
@app.post("/token")
def generate_token(
    request: TokenRequest,
    db: Session = Depends(get_db),
):
    user_id = request.user_id.strip()
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="User ID cannot be empty",
        )
    auth = authenticate_user(user_id, request.password)
    if not auth.get("authenticated"):
        write_audit(
            db,
            user_id,
            "authentication_failed",
            {
                "reason": auth.get("error", "Authentication failed"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=auth.get("error", "Invalid credentials"),
        )

    role = auth["role"]
    token = create_access_token(user_id, role=role)
    action_type = (
        "token_issued_credential"
        if auth.get("auth_type") == "credential"
        else "token_issued_demo"
    )
    write_audit(
        db,
        user_id,
        action_type,
        {
            "role": role,
            "auth_type": auth.get("auth_type", "demo"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": role,
        "auth_type": auth.get("auth_type", "demo"),
        "warning": (
            None
            if auth.get("auth_type") == "credential"
            else "Demo authentication only; not production-secure"
        ),
    }
# ---------------------------------------------------------
# SUBMIT REQUEST
# ---------------------------------------------------------
@app.post("/run-request", response_model=RunResponse)
def run_request(
    request: RunRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
):
    user_id = get_authenticated_user(credentials)
    if user_id != request.user_id:
        write_audit(
            db,
            user_id,
            "user_id_mismatch_rejected",
            {
                "authenticated_user": user_id,
                "requested_user": request.user_id,
            },
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail="You cannot submit requests for another user",
        )
    security = validate_request(user_id, request.request)
    if not security["allowed"]:
        write_audit(
            db,
            user_id,
            "request_rejected_validation",
            {"reason": security["reason"]},
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=security["reason"],
        )
    role = get_user_role(user_id)
    # Plan before executing anything.
    planning_request = request.request

    if request.context:
        planning_request += (
            "\n\nAdditional user-provided context:\n"
            + json.dumps(request.context, ensure_ascii=False)
        )

    plan = create_plan(planning_request)
    for step in plan.get("steps", []):
        step["user_context"] = request.context

    # Validate the generated plan before authorization and risk assessment.
    if not plan.get("error") and plan.get("steps"):
        try:
            plan = validate_plan(plan)
        except (ValueError, TypeError) as exc:
            write_audit(
                db,
                user_id,
                "planning_failed",
                {"error": str(exc)},
            )
            db.commit()
            raise HTTPException(
                status_code=400,
                detail=f"Invalid planner output: {exc}",
            )

    # Preserve the user's context for agent execution.
    if request.context:
        for step in plan.get("steps", []):
            step["user_context"] = request.context

    if plan.get("error") or not plan.get("steps"):
        write_audit(
            db,
            user_id,
            "planning_failed",
            {"error": plan.get("error", "No executable steps")},
        )
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=plan.get("error") or "No executable plan generated",
        )
    # Authorize every action before any execution.
    for step in plan["steps"]:
        permission = authorize_action(role, step.get("action", ""))
        if not permission["allowed"]:
            write_audit(
                db,
                user_id,
                "authorization_denied",
                {
                    "role": role,
                    "agent": step.get("agent"),
                    "action": step.get("action"),
                    "reason": permission["reason"],
                },
            )
            db.commit()
            raise HTTPException(
                status_code=403,
                detail=permission["reason"],
            )
    # Assess risk before deciding whether execution is permitted.
    assessment = assess_plan(plan, request.request)
    risk_score = assessment["risk_score"]
    decision = approval_decision(risk_score)
    task_status = (
        "pending_approval"
        if decision["requires_human_approval"]
        else "approved"
    )
    task = TaskLog(
        user_id=user_id,
        request=request.request,
        status=task_status,
    )
    db.add(task)
    db.flush()
    write_audit(
        db,
        user_id,
        "risk_assessed",
        {
            "task_id": task.id,
            "role": role,
            "risk_score": risk_score,
            "threshold": AUTO_APPROVE_THRESHOLD,
            "high_risk_threshold": HIGH_RISK_THRESHOLD,
            "tier": decision.get("tier", "unknown"),
            "required_role": decision.get("required_role", "none"),
            "approval_required": decision["requires_human_approval"],
            "plan": plan,
        },
    )
    # HIGH RISK: persist the plan and stop. Do not execute it.
    if decision["requires_human_approval"]:
        write_audit(
            db,
            user_id,
            "approval_pending",
            {
                "task_id": task.id,
                "risk_score": risk_score,
                "tier": decision.get("tier", "unknown"),
                "required_role": decision.get("required_role", "admin"),
                "status": "pending",
                "plan": plan,
            },
        )
        db.commit()
        db.refresh(task)
        return RunResponse(
            status="failed",
            details={
                "task_id": task.id,
                "user_id": user_id,
                "risk_score": risk_score,
                "tier": decision.get("tier", "unknown"),
                "required_role": decision.get("required_role", "manager"),
                "approval_status": "pending",
                "message": decision.get("reason", "Human approval is required before execution."),
                "plan": plan,
            },
            error="Approval required",
        )
    # LOW RISK: auto-approved. Execute the already assessed plan.
    execution = execute_approved_plan(plan)
    task.status = execution["status"]
    for item in execution["results"]:
        db.add(
            AgentExecutionLog(
                task_id=task.id,
                agent_name=item["agent"],
                action=item["action"],
                status=item["status"],
                result=item.get("message", ""),
            )
        )
    write_audit(
        db,
        user_id,
        "request_execution_finished",
        {
            "task_id": task.id,
            "risk_score": risk_score,
            "approval_status": "auto_approved",
            "execution_status": execution["status"],
            "results": execution["results"],
        },
    )
    db.commit()
    return RunResponse(
        status=execution["status"],
        details={
            "user_id": user_id,
            "task_id": task.id,
            "risk_score": risk_score,
            "approval_status": "auto_approved",
            "plan": plan,
            "results": execution["results"],
        },
        error=execution["error"],
    )
# ---------------------------------------------------------
# HUMAN APPROVAL ENDPOINT
# ---------------------------------------------------------
@app.post("/tasks/{task_id}/approval")
def decide_approval(
    task_id: int,
    request: ApprovalRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
):
    approver_id = get_authenticated_user(credentials)
    approver_role = get_user_role(approver_id)
    if approver_role not in {"admin", "manager"}:
        write_audit(
            db,
            approver_id,
            "approval_unauthorized",
            {
                "task_id": task_id,
                "approver_role": approver_role,
                "reason": "Employees do not have permission to decide task approvals",
            },
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail="Only an administrator or manager can approve or reject tasks",
        )
    task = db.query(TaskLog).filter(TaskLog.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "pending_approval":
        raise HTTPException(
            status_code=409,
            detail="Task is not awaiting approval",
        )
    # Find the stored pending-approval audit event.
    audit = (
        db.query(AuditLog)
        .filter(
            AuditLog.user_id == task.user_id,
            AuditLog.action == "approval_pending",
        )
        .order_by(AuditLog.id.desc())
        .all()
    )
    pending_data = None
    for record in audit:
        try:
            parsed = json.loads(record.details or "{}")
        except json.JSONDecodeError:
            continue
        if parsed.get("task_id") == task_id:
            pending_data = parsed
            break
    if pending_data is None or not pending_data.get("plan"):
        raise HTTPException(
            status_code=500,
            detail="Stored approval plan could not be found",
        )
    task_risk = pending_data.get("risk_score", 100)
    # Tiered check: High risk (>70) strictly requires admin role
    if task_risk > HIGH_RISK_THRESHOLD and approver_role != "admin":
        write_audit(
            db,
            approver_id,
            "approval_unauthorized",
            {
                "task_id": task_id,
                "approver_role": approver_role,
                "required_role": "admin",
                "risk_score": task_risk,
                "reason": "High-risk task (>70) strictly requires administrator approval",
            },
        )
        db.commit()
        raise HTTPException(
            status_code=403,
            detail="High-risk task (>70) strictly requires administrator approval",
        )
    if not request.approved:
        task.status = "rejected"
        write_audit(
            db,
            approver_id,
            "approval_rejected",
            {
                "task_id": task_id,
                "request_owner": task.user_id,
                "comments": request.comments,
            },
        )
        db.commit()
        return {
            "task_id": task_id,
            "status": "rejected",
            "executed": False,
        }
    # Re-check authorization using the current server-side role.
    plan = pending_data["plan"]
    owner_role = get_user_role(task.user_id)
    for step in plan.get("steps", []):
        permission = authorize_action(
            owner_role,
            step.get("action", ""),
        )
        if not permission["allowed"]:
            write_audit(
                db,
                approver_id,
                "approval_reauthorization_denied",
                {
                    "task_id": task_id,
                    "request_owner": task.user_id,
                    "action": step.get("action"),
                    "reason": permission["reason"],
                },
            )
            db.commit()
            raise HTTPException(
                status_code=403,
                detail="Task owner no longer has permission to execute this action",
            )
    # Mark approved and execute the stored plan exactly once.
    task.status = "approved"
    write_audit(
        db,
        approver_id,
        "approval_granted",
        {
            "task_id": task_id,
            "request_owner": task.user_id,
            "comments": request.comments,
        },
    )
    db.commit()
    execution = execute_approved_plan(plan)
    task.status = execution["status"]
    for item in execution["results"]:
        db.add(
            AgentExecutionLog(
                task_id=task.id,
                agent_name=item["agent"],
                action=item["action"],
                status=item["status"],
                result=item.get("message", ""),
            )
        )
    write_audit(
        db,
        approver_id,
        "approved_task_execution_finished",
        {
            "task_id": task_id,
            "execution_status": execution["status"],
            "results": execution["results"],
        },
    )
    db.commit()
    return {
        "task_id": task_id,
        "status": task.status,
        "executed": True,
        "results": execution["results"],
        "plan": plan,
        "risk_score": task_risk,
        "approval_status": "approved",
        "error": execution["error"],
    }
