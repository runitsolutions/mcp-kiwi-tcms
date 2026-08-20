"""Bearer / X-Api-Key authentication for the MCP view."""

from __future__ import annotations

from django.http import HttpRequest

from mcp_kiwi_tcms.models import TOKEN_PREFIX, McpApiKey

WWW_AUTHENTICATE = 'Bearer realm="kiwi-mcp"'


class AuthenticationError(Exception):
    def __init__(self, detail: str = "invalid_api_key") -> None:
        super().__init__(detail)
        self.detail = detail


def extract_token(request: HttpRequest) -> str | None:
    authorization = request.headers.get("Authorization") or request.META.get(
        "HTTP_AUTHORIZATION", ""
    )
    if authorization:
        scheme, _, remainder = authorization.partition(" ")
        if scheme.lower() == "bearer" and remainder.strip():
            return remainder.strip()
        if scheme.lower() == "basic":
            raise AuthenticationError("basic_not_supported")

    header_key = request.headers.get("X-Api-Key") or request.META.get("HTTP_X_API_KEY")
    if header_key:
        return header_key.strip()
    return None


def authenticate_request(request: HttpRequest) -> McpApiKey:
    token = extract_token(request)
    if not token:
        raise AuthenticationError("missing_api_key")
    if not token.startswith(TOKEN_PREFIX):
        raise AuthenticationError("malformed_api_key")

    prefix = token[:16]
    candidates = McpApiKey.objects.select_related("user").filter(prefix=prefix)
    for key in candidates:
        if not key.is_active:
            raise AuthenticationError("revoked_api_key")
        if not key.user.is_active:
            raise AuthenticationError("inactive_user")
        if key.matches(token):
            key.mark_used()
            return key
    raise AuthenticationError("invalid_api_key")
