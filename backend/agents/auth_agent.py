import os
import hmac
import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
TOKEN_EXPIRY_MINUTES = 30


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Hash a password using PBKDF2 HMAC SHA-256 with a salt."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{key.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plain password against a stored PBKDF2 hash."""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(key, expected_key)
    except Exception:
        return False


# Standard enterprise credentials for production/demo verification
# Salt and key hashes pre-generated with deterministic salts for testing
_FIXED_SALT = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")
USERS_DB = {
    "admin": {
        "user_id": "admin",
        "role": "admin",
        "password_hash": hash_password("AdminPassword123!", _FIXED_SALT),
    },
    "manager": {
        "user_id": "manager",
        "role": "manager",
        "password_hash": hash_password("ManagerPassword123!", _FIXED_SALT),
    },
    "employee1": {
        "user_id": "employee1",
        "role": "employee",
        "password_hash": hash_password("EmployeePassword123!", _FIXED_SALT),
    },
    "employee2": {
        "user_id": "employee2",
        "role": "employee",
        "password_hash": hash_password("EmployeePassword123!", _FIXED_SALT),
    },
}


def authenticate_user(user_id: str, password: str | None = None) -> dict:
    """
    Authenticate a user by user_id and optional password.
    Supports real credential verification while providing demo compatibility.
    """
    normalized_id = user_id.strip()
    if not normalized_id:
        return {"authenticated": False, "error": "User ID cannot be empty"}

    user = USERS_DB.get(normalized_id)

    # If password is provided, perform real password authentication
    if password is not None:
        if not user:
            return {"authenticated": False, "error": f"User '{normalized_id}' not found"}
        if not verify_password(password, user["password_hash"]):
            return {"authenticated": False, "error": "Invalid password"}
        return {
            "authenticated": True,
            "user_id": user["user_id"],
            "role": user["role"],
            "auth_type": "credential",
        }

    # Demo fallback: If no password is provided
    role = user["role"] if user else ("admin" if normalized_id == "admin" else "employee")
    return {
        "authenticated": True,
        "user_id": normalized_id,
        "role": role,
        "auth_type": "demo",
    }


def create_access_token(user_id: str, role: str | None = None) -> str:
    """Create a signed JWT access token containing subject and role claims."""
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is missing from .env")

    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRY_MINUTES),
    }
    if role:
        payload["role"] = role

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> dict:
    """Verify and decode a JWT access token."""
    if not SECRET_KEY:
        raise RuntimeError("JWT_SECRET_KEY is missing from .env")

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return {
            "valid": True,
            "user_id": payload.get("sub"),
            "role": payload.get("role"),
            "error": None,
        }

    except jwt.ExpiredSignatureError:
        return {
            "valid": False,
            "user_id": None,
            "role": None,
            "error": "Token has expired",
        }

    except jwt.InvalidTokenError:
        return {
            "valid": False,
            "user_id": None,
            "role": None,
            "error": "Invalid token",
        }
