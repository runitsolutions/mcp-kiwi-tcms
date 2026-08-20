import json

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from mcp_kiwi_tcms.auth import WWW_AUTHENTICATE, AuthenticationError, authenticate_request
from mcp_kiwi_tcms.protocol import handle_mcp_request, origin_is_blocked


def _unauthorized(detail: str) -> JsonResponse:
    response = JsonResponse({"error": detail}, status=401)
    response["WWW-Authenticate"] = WWW_AUTHENTICATE
    return response


@csrf_exempt
@require_http_methods(["GET", "POST", "DELETE"])
def mcp_view(request):
    if origin_is_blocked(request):
        return JsonResponse({"error": "origin_not_allowed"}, status=403)

    try:
        api_key = authenticate_request(request)
    except AuthenticationError as exc:
        return _unauthorized(exc.detail)

    request.user = api_key.user

    if request.method == "GET":
        return HttpResponse(status=405, headers={"Allow": "POST, DELETE"})

    if request.method == "DELETE":
        return HttpResponse(status=204)

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            },
            status=400,
        )

    return handle_mcp_request(request, body)
