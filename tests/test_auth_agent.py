import pytest
from backend.agents.auth_agent import (
    create_access_token,
    verify_access_token,
    hash_password,
    verify_password,
    authenticate_user,
    USERS_DB,
)


def test_password_hash_and_verify():
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_real_user_authentication_success():
    # Test valid credentials for admin
    auth_admin = authenticate_user("admin", "AdminPassword123!")
    assert auth_admin["authenticated"] is True
    assert auth_admin["role"] == "admin"
    assert auth_admin["auth_type"] == "credential"

    # Test valid credentials for employee1
    auth_emp = authenticate_user("employee1", "EmployeePassword123!")
    assert auth_emp["authenticated"] is True
    assert auth_emp["role"] == "employee"
    assert auth_emp["auth_type"] == "credential"


def test_real_user_authentication_invalid_password():
    auth = authenticate_user("admin", "IncorrectPassword")
    assert auth["authenticated"] is False
    assert auth["error"] == "Invalid password"


def test_real_user_authentication_unknown_user():
    auth = authenticate_user("nonexistent_user", "SomePassword123!")
    assert auth["authenticated"] is False
    assert "not found" in auth["error"].lower()


def test_demo_authentication_fallback():
    # If no password is provided, demo mode provides role
    auth = authenticate_user("employee1", None)
    assert auth["authenticated"] is True
    assert auth["role"] == "employee"
    assert auth["auth_type"] == "demo"


def test_jwt_token_creation_and_verification():
    token = create_access_token("admin", role="admin")
    assert bool(token) is True

    result = verify_access_token(token)
    assert result["valid"] is True
    assert result["user_id"] == "admin"
    assert result["role"] == "admin"
    assert result["error"] is None


def test_jwt_invalid_token():
    result = verify_access_token("this-is-an-invalid-token")
    assert result["valid"] is False
    assert result["user_id"] is None
    assert result["error"] == "Invalid token"
