import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from mcp_kiwi_tcms.models import TOKEN_PREFIX, McpApiKey


@pytest.mark.django_db
def test_missing_key_is_401():
    client = Client()
    response = client.post("/mcp/", data="{}", content_type="application/json")
    assert response.status_code == 401
    assert "Bearer" in response["WWW-Authenticate"]


@pytest.mark.django_db
def test_basic_auth_is_401(user):
    client = Client()
    response = client.post(
        "/mcp/",
        data="{}",
        content_type="application/json",
        HTTP_AUTHORIZATION="Basic dGVzdDp0ZXN0",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_malformed_bearer_is_401(user):
    client = Client()
    response = client.post(
        "/mcp/",
        data="{}",
        content_type="application/json",
        HTTP_AUTHORIZATION="Bearer not-a-kiwi-key",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_revoked_key_is_401(auth_header, api_token):
    _plaintext, key = api_token
    key.revoke()
    client = Client()
    response = client.post(
        "/mcp/",
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
        content_type="application/json",
        **auth_header,
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_initialize_and_tools_list(auth_header):
    client = Client()
    init = client.post(
        "/mcp/",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}},
            }
        ),
        content_type="application/json",
        **auth_header,
    )
    assert init.status_code == 200
    payload = init.json()
    assert payload["result"]["serverInfo"]["name"] == "kiwi-tcms"
    assert "Mcp-Session-Id" in init.headers or "mcp-session-id" in {k.lower() for k in init.headers}

    listed = client.post(
        "/mcp/",
        data=json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        content_type="application/json",
        HTTP_MCP_SESSION_ID=init.headers.get("Mcp-Session-Id", ""),
        **auth_header,
    )
    names = {tool["name"] for tool in listed.json()["result"]["tools"]}
    assert "kiwi_ping" in names
    assert "kiwi_list_test_plans" in names
    assert "kiwi_rpc" in names


@pytest.mark.django_db
def test_tools_call_uses_api_key_user(auth_header, fake_kiwi_rpc, user):
    client = Client()
    response = client.post(
        "/mcp/",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "kiwi_list_products", "arguments": {"query": {}}},
            }
        ),
        content_type="application/json",
        **auth_header,
    )
    assert response.status_code == 200
    body = response.json()["result"]
    assert body["isError"] is False
    assert "Seacrets Stage QA" in body["content"][0]["text"]
    assert fake_kiwi_rpc[0][0] == user.username
    assert fake_kiwi_rpc[0][1] == "Product.filter"


@pytest.mark.django_db
def test_run_summary_and_blocked_rpc(auth_header, fake_kiwi_rpc):
    client = Client()
    summary = client.post(
        "/mcp/",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "kiwi_get_test_run_summary", "arguments": {"run_id": 3}},
            }
        ),
        content_type="application/json",
        **auth_header,
    )
    text = summary.json()["result"]["content"][0]["text"]
    assert "FAILED" in text
    assert "execution_count" in text

    blocked = client.post(
        "/mcp/",
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "kiwi_rpc",
                    "arguments": {"method": "TestPlan.remove", "args": [1]},
                },
            }
        ),
        content_type="application/json",
        **auth_header,
    )
    assert blocked.json()["result"]["isError"] is True


@pytest.mark.django_db
def test_create_key_command(user, capsys):
    call_command("kiwi_mcp_create_key", username="tester", name="ci")
    out = capsys.readouterr().out
    assert TOKEN_PREFIX in out
    assert McpApiKey.objects.filter(user=user, name="ci").exists()


@pytest.mark.django_db
def test_create_key_unknown_user():
    with pytest.raises(CommandError):
        call_command("kiwi_mcp_create_key", username="ghost")
