"""MCP Streamable HTTP, JSON-only (no SSE) — suitable for Kiwi's WSGI/Apache stack."""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlparse

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse

from mcp_kiwi_tcms import __version__
from mcp_kiwi_tcms.tools import (
    call_tool,
    get_prompt,
    list_prompts,
    list_resources,
    list_tools,
    read_resource,
)

PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}
SESSION_TTL = 3600
SESSION_HEADER = "Mcp-Session-Id"


def _session_cache_key(session_id: str) -> str:
    return f"mcp-kiwi-session:{session_id}"


def origin_is_blocked(request: HttpRequest) -> bool:
    origin = request.headers.get("Origin") or request.META.get("HTTP_ORIGIN")
    if not origin:
        return False
    extra = getattr(settings, "MCP_KIWI_ALLOWED_ORIGINS", None) or []
    allowed = {request.get_host(), *extra}
    host = urlparse(origin).netloc or urlparse(origin).path
    return host not in allowed and origin not in extra


def _json_rpc_result(rpc_id: Any, result: Any, session_id: str | None = None) -> JsonResponse:
    response = JsonResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})
    if session_id:
        response[SESSION_HEADER] = session_id
    return response


def _json_rpc_error(
    rpc_id: Any, code: int, message: str, status: int = 200, session_id: str | None = None
) -> JsonResponse:
    response = JsonResponse(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}},
        status=status,
    )
    if session_id:
        response[SESSION_HEADER] = session_id
    return response


def _initialize_result(client_protocol: str | None) -> dict[str, Any]:
    version = client_protocol if client_protocol in SUPPORTED_PROTOCOLS else PROTOCOL_VERSION
    return {
        "protocolVersion": version,
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
            "prompts": {"listChanged": False},
        },
        "serverInfo": {"name": "kiwi-tcms", "version": __version__},
        "instructions": (
            "Kiwi TCMS MCP. Authenticate with Authorization: Bearer kiwi_mcp_<secret>. "
            "Prefer curated kiwi_* tools; kiwi_rpc is an allow-listed escape hatch."
        ),
    }


def handle_mcp_request(request: HttpRequest, body: Any) -> HttpResponse:
    if not isinstance(body, dict):
        return _json_rpc_error(None, -32600, "Batch JSON-RPC is not supported")

    rpc_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}
    if not isinstance(params, dict):
        params = {}

    incoming_session = request.headers.get(SESSION_HEADER) or request.META.get(
        "HTTP_MCP_SESSION_ID"
    )

    if method is None:
        return _json_rpc_error(rpc_id, -32600, "Missing method")

    if method == "initialize":
        session_id = str(uuid.uuid4())
        cache.set(
            _session_cache_key(session_id),
            {
                "user_id": request.user.pk,
                "protocol": params.get("protocolVersion"),
            },
            SESSION_TTL,
        )
        return _json_rpc_result(
            rpc_id, _initialize_result(params.get("protocolVersion")), session_id
        )

    if method == "notifications/initialized" or method.startswith("notifications/"):
        return HttpResponse(status=202)

    if method == "ping":
        return _json_rpc_result(rpc_id, {}, incoming_session)

    if method == "tools/list":
        return _json_rpc_result(rpc_id, {"tools": list_tools()}, incoming_session)

    if method == "tools/call":
        name = params.get("name")
        if not name:
            return _json_rpc_error(rpc_id, -32602, "tools/call requires name")
        result = call_tool(request, name, params.get("arguments") or {})
        return _json_rpc_result(rpc_id, result, incoming_session)

    if method == "resources/list":
        return _json_rpc_result(rpc_id, {"resources": list_resources()}, incoming_session)

    if method == "resources/read":
        uri = params.get("uri")
        if not uri:
            return _json_rpc_error(rpc_id, -32602, "resources/read requires uri")
        try:
            return _json_rpc_result(rpc_id, read_resource(request, uri), incoming_session)
        except ValueError as exc:
            return _json_rpc_error(rpc_id, -32602, str(exc))

    if method == "prompts/list":
        return _json_rpc_result(rpc_id, {"prompts": list_prompts()}, incoming_session)

    if method == "prompts/get":
        name = params.get("name")
        if not name:
            return _json_rpc_error(rpc_id, -32602, "prompts/get requires name")
        try:
            return _json_rpc_result(
                rpc_id, get_prompt(name, params.get("arguments") or {}), incoming_session
            )
        except ValueError as exc:
            return _json_rpc_error(rpc_id, -32602, str(exc))

    return _json_rpc_error(rpc_id, -32601, f"Method not found: {method}")
