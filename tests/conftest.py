import secrets

import pytest
from django.contrib.auth import get_user_model
from mcp_kiwi_tcms.models import TOKEN_PREFIX, McpApiKey
from mcp_kiwi_tcms.rpc import set_rpc_backend


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="tester", password="unused")


@pytest.fixture
def api_token(user):
    plaintext = TOKEN_PREFIX + secrets.token_urlsafe(24)
    key = McpApiKey.issue(user, "cursor", plaintext)
    return plaintext, key


@pytest.fixture
def auth_header(api_token):
    plaintext, _key = api_token
    return {"HTTP_AUTHORIZATION": f"Bearer {plaintext}"}


@pytest.fixture(autouse=True)
def fake_kiwi_rpc():
    store = []

    def backend(request, method, args, kwargs):
        store.append((request.user.username, method, args, kwargs))
        if method.endswith(".filter"):
            query = args[0] if args else {}
            if method == "TestCase.filter" and query.get("id") == 7:
                return [{"id": 7, "summary": "Login"}]
            if method == "TestRun.filter" and query.get("id") == 3:
                return [{"id": 3, "summary": "Nightly"}]
            if method == "TestExecution.filter":
                return [
                    {"id": 1, "run": 3, "status": 4, "status__name": "PASSED"},
                    {"id": 2, "run": 3, "status": 5, "status__name": "FAILED"},
                ]
            return [{"id": 1, "name": "Seacrets Stage QA"}]
        if method == "KiwiTCMS.version":
            return "15.2"
        return {"ok": True, "method": method, "args": args, "kwargs": kwargs}

    set_rpc_backend(backend)
    yield store
    set_rpc_backend(None)
