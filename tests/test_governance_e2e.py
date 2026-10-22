import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.db.base import SessionLocal
from backend.db.models_core import TaskLog, AuditLog


client = TestClient(app)


def test_real_authentication_flow():
    # 1. Invalid credentials returns 401
    bad_login = client.post("/token", json={"user_id": "admin", "password": "WrongPassword"})
    assert bad_login.status_code == 401

    # 2. Valid credentials returns 200 with JWT and role
    good_login = client.post("/token", json={"user_id": "admin", "password": "AdminPassword123!"})
    assert good_login.status_code == 200
    data = good_login.json()
    assert "access_token" in data
    assert data["role"] == "admin"
    assert data["auth_type"] == "credential"


def test_user_id_mismatch_audit_logged():
    login_res = client.post("/token", json={"user_id": "employee1", "password": "EmployeePassword123!"})
    token = login_res.json()["access_token"]

    # Attempt to submit a request on behalf of a different user
    res = client.post(
        "/run-request",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_id": "admin",  # mismatch with employee1
            "request": "Summarize my notes",
            "context": {},
        },
    )
    assert res.status_code == 403

    # Verify audit log was recorded and committed
    db = SessionLocal()
    try:
        audit = (
            db.query(AuditLog)
            .filter(AuditLog.action == "user_id_mismatch_rejected")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert audit is not None
        assert audit.user_id == "employee1"
    finally:
        db.close()


def test_human_approval_30_70_governance():
    # Login as admin to get token
    admin_login = client.post("/token", json={"user_id": "admin", "password": "AdminPassword123!"})
    admin_token = admin_login.json()["access_token"]

    # Login as employee
    emp_login = client.post("/token", json={"user_id": "employee1", "password": "EmployeePassword123!"})
    emp_token = emp_login.json()["access_token"]

    # Test the approval governance endpoint directly with a pending task
    db = SessionLocal()
    try:
        task = TaskLog(
            user_id="admin",
            request="High risk approval test task",
            status="pending_approval",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        # Record approval_pending audit with risk_score = 85 (>70)
        audit_payload = {
            "task_id": task.id,
            "risk_score": 85,
            "tier": "high",
            "plan": {
                "goal": "High risk test",
                "steps": [
                    {
                        "step_id": 1,
                        "agent": "email",
                        "action": "process_email",
                        "objective": "Draft email",
                        "inputs": [],
                        "depends_on": [],
                    }
                ],
            },
        }
        db.add(AuditLog(user_id="admin", action="approval_pending", details=json.dumps(audit_payload)))
        db.commit()

        # Employee attempts to approve high-risk task -> 403
        emp_decide = client.post(
            f"/tasks/{task.id}/approval",
            headers={"Authorization": f"Bearer {emp_token}"},
            json={"approved": True, "comments": "Employee trying to approve"},
        )
        assert emp_decide.status_code == 403

        # Admin approves high-risk task
        admin_decide = client.post(
            f"/tasks/{task.id}/approval",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"approved": True, "comments": "Admin approved high-risk operation"},
        )
        assert admin_decide.status_code == 200
        assert admin_decide.json()["executed"] is True

        # Verify final status updated
        db.refresh(task)
        assert task.status in {"success", "failed"}
    finally:
        db.close()
