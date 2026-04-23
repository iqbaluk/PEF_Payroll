"""
Authentication — simple login system with hashed passwords.
Users stored in users.json next to app.py.
"""
import json, hashlib, secrets
from pathlib import Path
from functools import wraps
from flask import session, redirect, url_for, request

BASE_DIR   = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users.json"

# ── Password hashing ───────────────────────────────────────────────────────────
def hash_password(password: str, salt: str = None) -> tuple:
    if not salt:
        salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return h, salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    h, _ = hash_password(password, salt)
    return h == stored_hash

# ── User store ─────────────────────────────────────────────────────────────────
def load_users() -> dict:
    if USERS_FILE.exists():
        return json.loads(USERS_FILE.read_text())
    # Default admin user
    h, s = hash_password("admin123")
    users = {
        "admin": {
            "name":     "Administrator",
            "hash":     h,
            "salt":     s,
            "role":     "admin",
        }
    }
    save_users(users)
    return users

def save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2))

def authenticate(username: str, password: str) -> dict | None:
    """Return user dict if valid, else None."""
    users = load_users()
    user  = users.get(username.strip().lower())
    if not user:
        return None
    if verify_password(password, user["hash"], user["salt"]):
        return user
    return None

def change_password(username: str, new_password: str):
    users = load_users()
    if username not in users:
        raise ValueError("User not found.")
    h, s = hash_password(new_password)
    users[username]["hash"] = h
    users[username]["salt"] = s
    save_users(users)

def add_user(username: str, name: str, password: str, role: str = "user"):
    users = load_users()
    if username in users:
        raise ValueError("Username already exists.")
    h, s = hash_password(password)
    users[username.strip().lower()] = {
        "name": name, "hash": h, "salt": s, "role": role
    }
    save_users(users)

def delete_user(username: str):
    users = load_users()
    if username == "admin":
        raise ValueError("Cannot delete admin user.")
    users.pop(username, None)
    save_users(users)

def get_all_users() -> list:
    users = load_users()
    return [{"username": k, "name": v["name"], "role": v["role"]}
            for k, v in users.items()]

# ── Flask decorators ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated

def get_current_user() -> dict | None:
    if session.get("logged_in"):
        return {
            "username": session.get("username"),
            "name":     session.get("user_name"),
            "role":     session.get("user_role"),
        }
    return None
