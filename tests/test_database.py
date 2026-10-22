import json
from datetime import datetime, timezone
from sqlalchemy import text
from backend.db.base import engine, SessionLocal, create_tables
from backend.db.models_core import TaskLog, AuditLog, AgentExecutionLog


def setup_module():
    """Ensure database tables exist before running database tests."""
    create_tables()


def test_database_connection():
    """Verify that PostgreSQL / database engine is reachable."""
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_task_log_crud():
    """Verify writing, reading, and updating task logs."""
    db = SessionLocal()
    try:
        task = TaskLog(
            user_id="test_user_db",
            request="Summarize notes for testing",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.id is not None
        assert task.status == "pending"

        # Update status
        task.status = "approved"
        db.commit()

        queried = db.query(TaskLog).filter(TaskLog.id == task.id).first()
        assert queried is not None
        assert queried.status == "approved"
    finally:
        db.close()


def test_audit_log_crud():
    """Verify writing and reading structured audit logs."""
    db = SessionLocal()
    try:
        details_payload = {
            "risk_score": 25,
            "tier": "low",
            "threshold": 30,
            "action": "summarize_notes",
        }
        audit = AuditLog(
            user_id="test_auditor",
            action="risk_assessed_test",
            details=json.dumps(details_payload),
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)

        assert audit.id is not None
        queried = db.query(AuditLog).filter(AuditLog.id == audit.id).first()
        assert queried is not None
        parsed = json.loads(queried.details)
        assert parsed["risk_score"] == 25
        assert parsed["tier"] == "low"
    finally:
        db.close()


def test_agent_execution_log_crud():
    """Verify writing and reading agent execution logs linked to tasks."""
    db = SessionLocal()
    try:
        task = TaskLog(
            user_id="exec_test_user",
            request="Process email test",
            status="approved",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        exec_log = AgentExecutionLog(
            task_id=task.id,
            agent_name="email",
            action="process_email",
            status="success",
            result="Draft created successfully",
        )
        db.add(exec_log)
        db.commit()
        db.refresh(exec_log)

        assert exec_log.id is not None
        assert exec_log.task_id == task.id
        assert exec_log.agent_name == "email"
        assert exec_log.status == "success"
    finally:
        db.close()


def test_transaction_rollback():
    """Verify session rollback cleans up uncommitted changes."""
    db = SessionLocal()
    try:
        task = TaskLog(
            user_id="rollback_user",
            request="Rollback test request",
            status="pending",
        )
        db.add(task)
        db.rollback()

        queried = db.query(TaskLog).filter(TaskLog.user_id == "rollback_user").first()
        assert queried is None
    finally:
        db.close()
