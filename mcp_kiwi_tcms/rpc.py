"""In-process Kiwi RPC dispatcher. Permissions come from the API-key user."""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

FORBIDDEN_METHOD_PARTS = (
    ".remove",
    ".delete",
    "remove_case",
    "remove_tag",
    "remove_comment",
    "remove_link",
    "remove_cc",
    "remove_attachment",
)

CLASS_MODULES = {
    "Build": "tcms.rpc.api.build",
    "Category": "tcms.rpc.api.category",
    "Classification": "tcms.rpc.api.classification",
    "Component": "tcms.rpc.api.component",
    "KiwiTCMS": "tcms.rpc.api.kiwitcms",
    "Markdown": "tcms.rpc.api.markdown",
    "PlanType": "tcms.rpc.api.plantype",
    "Priority": "tcms.rpc.api.priority",
    "Product": "tcms.rpc.api.product",
    "Tag": "tcms.rpc.api.tag",
    "TestCase": "tcms.rpc.api.testcase",
    "TestCaseStatus": "tcms.rpc.api.testcasestatus",
    "TestExecution": "tcms.rpc.api.testexecution",
    "TestExecutionStatus": "tcms.rpc.api.testexecutionstatus",
    "TestPlan": "tcms.rpc.api.testplan",
    "TestRun": "tcms.rpc.api.testrun",
    "User": "tcms.rpc.api.user",
    "Version": "tcms.rpc.api.version",
}

_backend: Callable[..., Any] | None = None


def set_rpc_backend(fn: Callable[..., Any] | None) -> None:
    """Tests inject a fake backend so Kiwi does not need to be installed."""
    global _backend
    _backend = fn


def method_is_forbidden(method_name: str) -> bool:
    lowered = method_name.lower()
    return any(part in lowered for part in FORBIDDEN_METHOD_PARTS)


def _unwrap(fn: Callable[..., Any]) -> Callable[..., Any]:
    while hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


def _resolve(method_name: str) -> Callable[..., Any]:
    if "." not in method_name:
        raise ValueError(f"RPC method must be Class.method, got {method_name!r}")
    class_name, func_name = method_name.split(".", 1)
    module_path = CLASS_MODULES.get(class_name)
    if not module_path:
        raise ValueError(f"RPC class {class_name!r} is not allowed")
    module = importlib.import_module(module_path)
    fn = getattr(module, func_name, None)
    if fn is None:
        raise ValueError(f"Unknown RPC method {method_name}")
    return _unwrap(fn)


def invoke_rpc(
    request: HttpRequest,
    method_name: str,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
) -> Any:
    args = args or []
    kwargs = dict(kwargs or {})
    if _backend is not None:
        return _backend(request, method_name, args, kwargs)
    if method_is_forbidden(method_name):
        raise PermissionDenied(f"{method_name} is blocked by the MCP allow-list")
    user: AbstractBaseUser = request.user
    if not user.is_authenticated:
        raise PermissionDenied("API key user is not authenticated")
    fn = _resolve(method_name)
    signature = inspect.signature(fn)
    if "rpc_context" in signature.parameters:
        kwargs["rpc_context"] = SimpleNamespace(request=request)
    return fn(*args, **kwargs)
