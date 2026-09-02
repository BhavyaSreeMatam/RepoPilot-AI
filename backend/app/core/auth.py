from functools import lru_cache
from typing import Any, Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.core.config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


def unauthorized(detail: str = "Invalid or missing authentication token."):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_cognito_issuer() -> str:
    settings = get_settings()

    return (
        f"https://cognito-idp.{settings.aws_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}"
    )


@lru_cache
def get_jwk_client() -> PyJWKClient:
    issuer = get_cognito_issuer()

    return PyJWKClient(
        f"{issuer}/.well-known/jwks.json"
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """
    Validate an Amazon Cognito access token and return its claims.

    Security checks:
    - Bearer token must be present
    - JWT signature must match Cognito JWKS
    - token issuer must match our Cognito User Pool
    - token must not be expired
    - token_use must be "access"
    - client_id must match RepoPilot's Cognito app client
    - token must contain a Cognito user sub
    """

    if credentials is None:
        unauthorized("Authentication is required.")

    if credentials.scheme.lower() != "bearer":
        unauthorized()

    token = credentials.credentials
    settings = get_settings()
    issuer = get_cognito_issuer()

    try:
        signing_key = get_jwk_client().get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            options={
                # Cognito access tokens identify the app using client_id
                # rather than the standard aud claim.
                "verify_aud": False,
            },
        )

    except (InvalidTokenError, PyJWKClientError):
        unauthorized()

    except Exception:
        # Do not expose low-level authentication/JWKS details to clients.
        unauthorized()

    if claims.get("token_use") != "access":
        unauthorized("An access token is required.")

    if claims.get("client_id") != settings.cognito_app_client_id:
        unauthorized("Token was issued for a different application.")

    if not claims.get("sub"):
        unauthorized("Token does not contain a valid user identity.")

    return claims


def get_current_user_sub(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> str:
    """
    Convenience dependency for endpoints that only need the Cognito user ID.
    """

    return current_user["sub"]