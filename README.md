# mcp-kiwi-tcms

Kiwi TCMS plugin that serves the [Model Context Protocol](https://modelcontextprotocol.io/) at **`/mcp/`** inside the Kiwi process (Apache/WSGI, JSON Streamable HTTP, no SSE).

Authentication is **API key only**: `Authorization: Bearer kiwi_mcp_…` mapped to a Django user. No HTTP Basic, no OAuth, no IdP.

## Install in the Kiwi image

```dockerfile
RUN pip install --no-cache-dir \
      "mcp-kiwi-tcms @ git+https://github.com/runitsolutions/mcp-kiwi-tcms@<sha>"
```

Kiwi loads `kiwitcms.plugins` entry point `mcp = mcp_kiwi_tcms`, so URLs are mounted at `/mcp/`. Then:

```bash
./manage.py migrate mcp_kiwi_tcms
./manage.py kiwi_mcp_create_key --username <django-user> --name cursor
```

The command prints the plaintext token **once**. Store it outside git.

Smoke from the pod (the request must reach Django):

```bash
curl -sS -X POST https://tms.seacrets.online/mcp/ \
  -H "Authorization: Bearer kiwi_mcp_…" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{}}}'
```

## Cursor

```json
{
  "mcpServers": {
    "kiwi-tcms": {
      "url": "https://tms.seacrets.online/mcp/",
      "headers": {
        "Authorization": "Bearer kiwi_mcp_…"
      }
    }
  }
}
```

Revoke a key in Django admin (**MCP API keys**) or set `revoked_at`. That does not change the user's password.

If a reverse proxy in front of Kiwi intercepts `/mcp` with an HTML login page, this plugin never sees the request. That routing is out of scope here.

## Tools

Read: `kiwi_ping`, `kiwi_list_products`, `kiwi_list_test_plans`, `kiwi_list_test_cases`, `kiwi_get_test_case`, `kiwi_list_test_runs`, `kiwi_get_test_run_summary`, `kiwi_list_executions`, `kiwi_list_builds`, `kiwi_list_versions`, `kiwi_list_priorities`, `kiwi_list_categories`, `kiwi_list_plan_types`.

Write: `kiwi_create_test_plan`, `kiwi_add_cases_to_plan`, `kiwi_create_test_case`, `kiwi_update_test_case`, `kiwi_create_test_run`, `kiwi_add_cases_to_run`, `kiwi_update_execution`, `kiwi_add_link_to_execution`.

Escape hatch: `kiwi_rpc` (Kiwi `Class.method`; `*.remove` / `*.delete` blocked). Resource `kiwi://status`. Prompt `summarize_test_run`.

RPC runs **as the Django user that owns the key**.

## Develop

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
ruff check .
```

License: [AGPL-3.0-or-later](LICENSE), same as Kiwi TCMS plugins.
