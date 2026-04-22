"""Convert ghibli.tools functions to OpenAI-compatible tool schemas for LiteLLM."""

from __future__ import annotations

import inspect
from typing import get_type_hints

import ghibli.tools as _tools

_TOOL_NAMES = [
    "search_repositories",
    "get_repository",
    "list_issues",
    "list_pull_requests",
    "get_user",
    "list_releases",
    "get_languages",
    "list_contributors",
    "list_commits",
    "search_code",
    "search_users",
    "search_issues",
    "get_readme",
]

_PYTHON_TO_JSON_TYPE = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _build_schema(fn) -> dict:
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    doc = inspect.getdoc(fn) or ""

    description = doc.split("\n\n")[0].strip()

    param_docs: dict[str, str] = {}
    in_args = False
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped == "Args:":
            in_args = True
            continue
        if in_args:
            if stripped == "" or (stripped.endswith(":") and ":" not in stripped[:-1]):
                in_args = False
                continue
            if ":" in stripped:
                name, _, desc = stripped.partition(":")
                param_docs[name.strip()] = desc.strip()

    properties: dict[str, dict] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name == "self":
            continue
        raw_type = hints.get(name, str)
        origin = getattr(raw_type, "__origin__", None)
        if origin is type(None):
            raw_type = str
        args_ = getattr(raw_type, "__args__", None)
        if origin is not None and args_:
            non_none = [a for a in args_ if a is not type(None)]
            raw_type = non_none[0] if non_none else str

        is_required = param.default is inspect.Parameter.empty
        json_type = _PYTHON_TO_JSON_TYPE.get(raw_type, "string")
        if not is_required and json_type == "integer":
            json_type = "string"

        prop: dict = {"type": json_type}
        if name in param_docs:
            prop["description"] = param_docs[name]

        properties[name] = prop
        if is_required:
            required.append(name)

    params_schema: dict = {"type": "object", "properties": properties}
    if required:
        params_schema["required"] = required

    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": description,
            "parameters": params_schema,
        },
    }


def get_openai_tool_schemas() -> list[dict]:
    """Return all six ghibli GitHub tools as OpenAI-compatible tool schema dicts."""
    return [_build_schema(getattr(_tools, name)) for name in _TOOL_NAMES]
