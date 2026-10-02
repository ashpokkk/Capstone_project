"""
Supabase JWT verification (ES256, public keys fetched from Supabase's JWKS endpoint).
No secret is stored here: only SUPABASE_URL is needed.
"""

import logging
import os

import jwt
from jwt import PyJWKClient
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()
logger = logging.getLogger("fbr_chatbot")

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
ISSUER = f"{SUPABASE_URL}/auth/v1"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"

_jwks_client = PyJWKClient(JWKS_URL, cache_keys=True)
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """FastAPI dependency: returns the verified token claims, or raises 401."""
    if creds is None:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = creds.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience="authenticated",
            issuer=ISSUER,
        )
    except jwt.PyJWTError as e:
        logger.warning("Token rejected: %s", e)
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims