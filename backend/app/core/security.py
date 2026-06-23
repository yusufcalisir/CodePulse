"""Security helpers for token validation and authentication."""

from fastapi import Header, HTTPException, status


async def verify_api_token(
    authorization: str | None = Header(None),
) -> str:
    """Validate the Authorization header.

    For MVP, this accepts the GitHub access token passed from the frontend.
    In production, implement proper JWT validation.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    # Accept "Bearer <token>" format
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use 'Bearer <token>'",
        )

    return parts[1]
