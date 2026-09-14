"""Module 19 (stack finalization) — JWT authentication + role-based access
control, matching `build prompt.md` TECH STACK: "Auth: JWT, role-based access
control (MP / District / State / Ministry)".

Model
-----
* Users live in Postgres (`users` table, added to db.SCHEMA) with an
  rbac `role` and a JSONB `scope`::
      ministry            -> {}                        (national)
      state_nodal         -> {state: "Uttar Pradesh"}
      district_authority  -> {state: "Uttar Pradesh", ida: "BAREILLY"}
      mp                  -> {mp: "Hardeep"}
      auditor             -> {}                        (cross-cutting)
* Passwords: salted PBKDF2-HMAC-SHA256 (stdlib, no bcrypt dependency).
* Login issues a signed HS256 JWT (sub/role/sc/exp/iat).
* `authorize()` enforces fail-closed role + scope rules on top of the existing
  query params; every protected endpoint applies it to the caller.

Demo vs production
------------------
* AUTH_REQUIRED=0 (default, dev/demo): endpoints answer anonymously, but any
  *presented* token is still validated and scoped fail-closed.
* AUTH_REQUIRED=1: every protected endpoint demands a valid token and enforces
  role + scope.
"""

import hashlib
import hmac
import json
import logging
import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv('JWT_SECRET', 'dev-insecure-change-me')
if SECRET_KEY == 'dev-insecure-change-me':
    logger.warning('JWT_SECRET is the insecure dev default — set JWT_SECRET in production.')
ALGO = 'HS256'
TOKEN_TTL_SECONDS = int(os.getenv('JWT_TTL_SECONDS', str(12 * 3600)))
AUTH_REQUIRED = os.getenv('AUTH_REQUIRED', '0') == '1'

ROLES = ('ministry', 'state_nodal', 'district_authority', 'mp', 'auditor')

# username, password, role, scope, display_name
DEMO_USERS = [
    ('ministry', 'ministry@123', 'ministry', {}, 'Ministry of Statistics & PI'),
    ('up_nodal', 'up@nodal123', 'state_nodal', {'state': 'Uttar Pradesh'}, 'UP Nodal Authority'),
    ('da_bareilly', 'bareilly@123', 'district_authority',
     {'state': 'Uttar Pradesh', 'ida': 'BAREILLY'}, 'Bareilly District Authority'),
    ('mp_hardeep', 'hardeep@123', 'mp', {'mp': 'Hardeep'}, 'Shri Hardeep Singh Puri'),
    ('auditor', 'audit@mspi123', 'auditor', {}, 'CAG Auditor'),
]

DEMO_CREDENTIALS = [
    {'username': u[0], 'role': u[2], 'example_password': u[1]} for u in DEMO_USERS
]


def seed_users(conn) -> None:
    """Idempotent upsert of the demo RBAC users (hash rewritten each boot)."""
    from src.db import upsert_user
    for username, password, role, scope, display in DEMO_USERS:
        salt, phash = make_password(password)
        upsert_user(conn, username, role, scope, salt, phash, display)

_bearer = HTTPBearer(auto_error=False)


# ---------- password hashing ----------
def make_password(password: str, salt_hex: Optional[str] = None) -> tuple[str, str]:
    """Return (salt_hex, password_hash_hex) — PBKDF2-HMAC-SHA256, 200k iters."""
    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    if not salt_hex:
        salt_hex = salt.hex()
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200_000)
    return salt_hex, dk.hex()


def verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    _, candidate = make_password(password, salt_hex)
    return hmac.compare_digest(candidate, password_hash)


# ---------- JWT ----------
def create_token(username: str, role: str, scope: dict) -> str:
    now = int(__import__('time').time())
    claims = {
        'sub': username,
        'role': role,
        'sc': scope or {},
        'iat': now,
        'exp': now + TOKEN_TTL_SECONDS,
    }
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGO)


def decode_token(token: str) -> dict:
    """Decode + verify. Raises jwt exceptions on invalid/expired."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGO])


# ---------- FastAPI dependency ----------
def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[dict]:
    """Return claim dict for a presented token, else None (anonymous).

    Anonymous is only permitted when AUTH_REQUIRED=0 (demo); a presented token
    is always validated fail-closed.
    """
    if creds is None:
        if AUTH_REQUIRED:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                                detail='Authentication required')
        return None
    try:
        return decode_token(creds.credentials)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Token expired') from e
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from e


def _contains(haystack: str, needle: str) -> bool:
    a, b = haystack.lower(), needle.lower()
    return needle != '' and (a in b or b in a)


def authorize(
    user: Optional[dict],
    *,
    allowed_roles: Optional[tuple[str, ...]] = None,
    role: Optional[str] = None,          # must match requested dashboard role
    state: Optional[str] = None,
    ida: Optional[str] = None,
    mp: Optional[str] = None,
    work_state: Optional[str] = None,
    work_ida: Optional[str] = None,
    work_mp: Optional[str] = None,
    work: Optional[dict] = None,
) -> None:
    """Fail-closed RBAC check. Raises HTTP 401/403 when denied."""
    if user is None:
        if not AUTH_REQUIRED:
            return                      # demo mode: anonymous allowed
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail='Authentication required')

    role_name = user.get('role')
    if role_name not in ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail='Unknown role')
    if allowed_roles and role_name not in allowed_roles:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail=f'{role_name} is not allowed to perform this action')
    if role and role_name != role:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail=f'Role {role_name} cannot open the {role} dashboard')

    scope = user.get('sc') or {}
    deny = lambda msg: (_ for _ in ()).throw(
        HTTPException(status.HTTP_403_FORBIDDEN, detail=msg))

    # scope params the caller asked for must be within the caller's scope
    if scope.get('state') and state and scope['state'].strip().lower() != state.strip().lower():
        deny('State outside your scope')
    if scope.get('ida') and ida:
        if not scope['ida'].lower() in ida.lower() and not ida.lower() in scope['ida'].lower():
            deny('District (IDA) outside your scope')
    if scope.get('mp') and mp and not _contains(mp, scope['mp']):
        deny('MP outside your scope')

    # explicit whole-work row scoping (actions, risk detail)
    if work or work_state or work_ida or work_mp:
        w_state = work_state if work_state is not None else (work or {}).get('state')
        w_ida = work_ida if work_ida is not None else (work or {}).get('ida')
        w_mp = work_mp if work_mp is not None else (work or {}).get('mp_name')
        if role_name == 'district_authority':
            if scope.get('ida') and not _contains(str(w_ida or ''), scope['ida']):
                deny('Work is outside your district')
        elif role_name == 'state_nodal':
            if scope.get('state') and str(w_state or '').strip().lower() != scope['state'].strip().lower():
                deny('Work is outside your state')
        elif role_name == 'mp':
            if scope.get('mp') and not _contains(str(w_mp or ''), scope['mp']):
                deny('Work is outside your MP portfolio')


def require_scope(user: Optional[dict], key: str):
    """Fail-closed: a scoped role must carry the key."""
    if user is None:
        return None
    val = (user.get('sc') or {}).get(key)
    if not val:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail=f'Your role has no {key} scope to filter by')
    return val