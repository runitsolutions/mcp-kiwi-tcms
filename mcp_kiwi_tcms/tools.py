"""Curated MCP tools, resources, and prompts over Kiwi RPC."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest

from mcp_kiwi_tcms.rpc import invoke_rpc, method_is_forbidden

JSON_OBJECT = {"type": "object", "additionalProperties": True}


def _dump(value: Any) -> str:
    return json.dumps(value, cls=DjangoJSONEncoder, indent=2, default=str)


def _rpc(request: HttpRequest, method: str, *args: Any, **kwargs: Any) -> Any:
    return invoke_rpc(request, method, list(args), kwargs)


def kiwi_ping(request: HttpRequest, **_kwargs: Any) -> dict[str, Any]:
    version = None
    try:
        version = _rpc(request, "KiwiTCMS.version")
    except Exception:  # noqa: BLE001 — version is optional when Kiwi is mocked
        version = "unknown"
    return {
        "ok": True,
        "user": getattr(request.user, "username", None),
        "kiwi_version": version,
    }


def kiwi_list_products(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "Product.filter", query or {})


def kiwi_list_test_plans(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "TestPlan.filter", query or {})


def kiwi_list_test_cases(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "TestCase.filter", query or {})


def kiwi_get_test_case(request: HttpRequest, case_id: int, **_k: Any) -> Any:
    rows = _rpc(request, "TestCase.filter", {"id": case_id})
    if not rows:
        raise ValueError(f"TestCase {case_id} not found")
    return rows[0]


def kiwi_list_test_runs(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "TestRun.filter", query or {})


def kiwi_get_test_run_summary(request: HttpRequest, run_id: int, **_k: Any) -> Any:
    runs = _rpc(request, "TestRun.filter", {"id": run_id})
    if not runs:
        raise ValueError(f"TestRun {run_id} not found")
    executions = _rpc(request, "TestExecution.filter", {"run": run_id})
    by_status: dict[str, int] = {}
    for execution in executions:
        name = execution.get("status__name") or str(execution.get("status") or "unknown")
        by_status[name] = by_status.get(name, 0) + 1
    return {"run": runs[0], "execution_count": len(executions), "by_status": by_status}


def kiwi_list_executions(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "TestExecution.filter", query or {})


def kiwi_list_builds(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "Build.filter", query or {})


def kiwi_list_versions(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "Version.filter", query or {})


def kiwi_list_priorities(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "Priority.filter", query or {})


def kiwi_list_categories(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "Category.filter", query or {})


def kiwi_list_plan_types(request: HttpRequest, query: dict | None = None, **_k: Any) -> Any:
    return _rpc(request, "PlanType.filter", query or {})


def kiwi_create_test_plan(request: HttpRequest, values: dict, **_k: Any) -> Any:
    return _rpc(request, "TestPlan.create", values)


def kiwi_add_cases_to_plan(
    request: HttpRequest, plan_id: int, case_ids: list[int], **_k: Any
) -> Any:
    results = []
    for case_id in case_ids:
        results.append(_rpc(request, "TestPlan.add_case", plan_id, case_id))
    return results


def kiwi_create_test_case(request: HttpRequest, values: dict, **_k: Any) -> Any:
    return _rpc(request, "TestCase.create", values)


def kiwi_update_test_case(request: HttpRequest, case_id: int, values: dict, **_k: Any) -> Any:
    return _rpc(request, "TestCase.update", case_id, values)


def kiwi_create_test_run(request: HttpRequest, values: dict, **_k: Any) -> Any:
    return _rpc(request, "TestRun.create", values)


def kiwi_add_cases_to_run(request: HttpRequest, run_id: int, case_ids: list[int], **_k: Any) -> Any:
    results = []
    for case_id in case_ids:
        results.append(_rpc(request, "TestRun.add_case", run_id, case_id))
    return results


def kiwi_update_execution(request: HttpRequest, execution_id: int, values: dict, **_k: Any) -> Any:
    return _rpc(request, "TestExecution.update", execution_id, values)


def kiwi_add_link_to_execution(
    request: HttpRequest,
    execution_id: int,
    url: str,
    name: str | None = None,
    is_defect: bool = False,
    **_k: Any,
) -> Any:
    payload = {"execution": execution_id, "url": url, "is_defect": is_defect}
    if name:
        payload["name"] = name
    return _rpc(request, "TestExecution.add_link", payload)


def kiwi_rpc(
    request: HttpRequest,
    method: str,
    args: list | None = None,
    kwargs: dict | None = None,
    **_k: Any,
) -> Any:
    if method_is_forbidden(method):
        raise PermissionDenied(f"{method} is not allowed")
    return invoke_rpc(request, method, args or [], kwargs or {})

QUERY_PROP = {
    "type": "object",
    "properties": {"query": {"type": "object", "additionalProperties": True}},
}

READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}
WRITE = {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "kiwi_ping",
        "description": "Confirm MCP auth and report the Kiwi user plus version.",
        "inputSchema": {"type": "object", "properties": {}},
        "annotations": READ_ONLY,
        "handler": kiwi_ping,
    },
    {
        "name": "kiwi_list_products",
        "description": "List Kiwi products (Product.filter).",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_products,
    },
    {
        "name": "kiwi_list_test_plans",
        "description": "List test plans. Pass Django lookups in query, e.g. {product: 1}.",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_test_plans,
    },
    {
        "name": "kiwi_list_test_cases",
        "description": "List test cases. query supports Django field lookups.",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_test_cases,
    },
    {
        "name": "kiwi_get_test_case",
        "description": "Fetch a single test case by id.",
        "inputSchema": {
            "type": "object",
            "properties": {"case_id": {"type": "integer"}},
            "required": ["case_id"],
        },
        "annotations": READ_ONLY,
        "handler": kiwi_get_test_case,
    },
    {
        "name": "kiwi_list_test_runs",
        "description": "List test runs (TestRun.filter).",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_test_runs,
    },
    {
        "name": "kiwi_get_test_run_summary",
        "description": "Test run metadata plus execution counts grouped by status.",
        "inputSchema": {
            "type": "object",
            "properties": {"run_id": {"type": "integer"}},
            "required": ["run_id"],
        },
        "annotations": READ_ONLY,
        "handler": kiwi_get_test_run_summary,
    },
    {
        "name": "kiwi_list_executions",
        "description": "List test executions. query e.g. {run: 12, status: 4}.",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_executions,
    },
    {
        "name": "kiwi_list_builds",
        "description": "List builds (Build.filter).",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_builds,
    },
    {
        "name": "kiwi_list_versions",
        "description": "List versions (Version.filter).",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_versions,
    },
    {
        "name": "kiwi_list_priorities",
        "description": "List case priorities.",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_priorities,
    },
    {
        "name": "kiwi_list_categories",
        "description": "List case categories.",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_categories,
    },
    {
        "name": "kiwi_list_plan_types",
        "description": "List test plan types.",
        "inputSchema": QUERY_PROP,
        "annotations": READ_ONLY,
        "handler": kiwi_list_plan_types,
    },
    {
        "name": "kiwi_create_test_plan",
        "description": "Create a test plan. values matches TestPlan.create (name, product, ...).",
        "inputSchema": {
            "type": "object",
            "properties": {"values": JSON_OBJECT},
            "required": ["values"],
        },
        "annotations": WRITE,
        "handler": kiwi_create_test_plan,
    },
    {
        "name": "kiwi_add_cases_to_plan",
        "description": "Attach existing test cases to a plan.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "integer"},
                "case_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["plan_id", "case_ids"],
        },
        "annotations": WRITE,
        "handler": kiwi_add_cases_to_plan,
    },
    {
        "name": "kiwi_create_test_case",
        "description": "Create a test case. values matches TestCase.create.",
        "inputSchema": {
            "type": "object",
            "properties": {"values": JSON_OBJECT},
            "required": ["values"],
        },
        "annotations": WRITE,
        "handler": kiwi_create_test_case,
    },
    {
        "name": "kiwi_update_test_case",
        "description": "Update a test case (TestCase.update).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "integer"},
                "values": JSON_OBJECT,
            },
            "required": ["case_id", "values"],
        },
        "annotations": WRITE,
        "handler": kiwi_update_test_case,
    },
    {
        "name": "kiwi_create_test_run",
        "description": "Create a test run. values matches TestRun.create (plan, build, manager).",
        "inputSchema": {
            "type": "object",
            "properties": {"values": JSON_OBJECT},
            "required": ["values"],
        },
        "annotations": WRITE,
        "handler": kiwi_create_test_run,
    },
    {
        "name": "kiwi_add_cases_to_run",
        "description": "Add confirmed test cases to a run (creates executions).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "integer"},
                "case_ids": {"type": "array", "items": {"type": "integer"}},
            },
            "required": ["run_id", "case_ids"],
        },
        "annotations": WRITE,
        "handler": kiwi_add_cases_to_run,
    },
    {
        "name": "kiwi_update_execution",
        "description": "Update an execution, typically {status: <id>} to record a result.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_id": {"type": "integer"},
                "values": JSON_OBJECT,
            },
            "required": ["execution_id", "values"],
        },
        "annotations": WRITE,
        "handler": kiwi_update_execution,
    },
    {
        "name": "kiwi_add_link_to_execution",
        "description": "Attach a URL (bug, log, artefact) to an execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "execution_id": {"type": "integer"},
                "url": {"type": "string"},
                "name": {"type": "string"},
                "is_defect": {"type": "boolean"},
            },
            "required": ["execution_id", "url"],
        },
        "annotations": WRITE,
        "handler": kiwi_add_link_to_execution,
    },
    {
        "name": "kiwi_rpc",
        "description": (
            "Escape hatch: call an allow-listed Kiwi RPC method (Class.method). "
            "Destructive remove/delete methods are blocked."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "method": {"type": "string"},
                "args": {"type": "array"},
                "kwargs": {"type": "object"},
            },
            "required": ["method"],
        },
        "annotations": {**WRITE, "openWorldHint": True},
        "handler": kiwi_rpc,
    },
]

HANDLERS: dict[str, Callable[..., Any]] = {spec["name"]: spec["handler"] for spec in TOOL_SPECS}


def list_tools() -> list[dict[str, Any]]:
    tools = []
    for spec in TOOL_SPECS:
        tools.append(
            {
                "name": spec["name"],
                "description": spec["description"],
                "inputSchema": spec["inputSchema"],
                "annotations": spec["annotations"],
            }
        )
    return tools


def call_tool(request: HttpRequest, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    handler = HANDLERS.get(name)
    if handler is None:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            "isError": True,
        }
    try:
        result = handler(request, **(arguments or {}))
    except Exception as exc:  # noqa: BLE001 — surface Kiwi/RPC errors to the MCP client
        return {
            "content": [{"type": "text", "text": f"{type(exc).__name__}: {exc}"}],
            "isError": True,
        }
    return {"content": [{"type": "text", "text": _dump(result)}], "isError": False}


def list_resources() -> list[dict[str, Any]]:
    return [
        {
            "uri": "kiwi://status",
            "name": "Kiwi MCP status",
            "description": "Authenticated user and Kiwi version.",
            "mimeType": "application/json",
        }
    ]


def read_resource(request: HttpRequest, uri: str) -> dict[str, Any]:
    if uri != "kiwi://status":
        raise ValueError(f"Unknown resource {uri}")
    text = _dump(kiwi_ping(request))
    return {
        "contents": [{"uri": uri, "mimeType": "application/json", "text": text}]
    }


def list_prompts() -> list[dict[str, Any]]:
    return [
        {
            "name": "summarize_test_run",
            "description": "Ask the model to summarize a Kiwi test run by id.",
            "arguments": [
                {
                    "name": "run_id",
                    "description": "Kiwi TestRun primary key",
                    "required": True,
                }
            ],
        }
    ]


def get_prompt(name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
    arguments = arguments or {}
    if name != "summarize_test_run":
        raise ValueError(f"Unknown prompt {name}")
    run_id = arguments.get("run_id", "<run_id>")
    return {
        "description": "Summarize a Kiwi test run",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"Use kiwi_get_test_run_summary with run_id={run_id} and "
                        "kiwi_list_executions with query={run: "
                        f"{run_id}"
                        "}. Summarize progress, failures, and next actions."
                    ),
                },
            }
        ],
    }
