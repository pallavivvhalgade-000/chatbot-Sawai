import secrets

from fastapi import (
    HTTPException,
    Security,
    status,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.config import settings


bearer_scheme = HTTPBearer(
    auto_error=False
)


def require_admin(
    credentials: (
        HTTPAuthorizationCredentials
        | None
    ) = Security(
        bearer_scheme
    ),
) -> None:
    """
    Protect staff-only APIs.

    This is suitable for the pilot/admin API.

    The secret must stay server-side and must never be
    placed inside the public chatbot JavaScript.
    """

    if not settings.admin_api_enabled:
        raise HTTPException(
            status_code=404,
            detail="Not found.",
        )


    expected = (
        settings.admin_api_token
        or ""
    )


    if not expected:
        raise HTTPException(
            status_code=503,
            detail=(
                "Admin API authentication "
                "is not configured."
            ),
        )


    provided = (
        credentials.credentials
        if credentials
        else ""
    )


    if not secrets.compare_digest(
        provided,
        expected,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid credentials.",
            headers={
                "WWW-Authenticate":
                    "Bearer"
            },
        )