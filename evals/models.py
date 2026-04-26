"""LiteLLM multi-model chat interface for ghibli eval pipeline."""

from __future__ import annotations

import json
import os
import re
import time

import litellm
from litellm.exceptions import APIConnectionError as LiteLLMConnectionError
from litellm.exceptions import RateLimitError as LiteLLMRateLimitError
from litellm.exceptions import ServiceUnavailableError as LiteLLMServiceUnavailableError
from litellm.exceptions import Timeout as LiteLLMTimeout

import ghibli.tools as _tools
from ghibli.exceptions import ToolCallError
from ghibli.prompt import get_system_prompt
from ghibli.tool_schema import get_openai_tool_schemas

_OLLAMA_CLOUD_API_BASE = "https://ollama.com"

_MODEL_CONFIG: dict[str, dict] = {
    "gemini": {
        "model_id": "gemini/gemini-2.5-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "gemini-vertex": {
        # Gemini 3 Flash (preview) via Vertex AI — global endpoint required for
        # preview models. Auth via ADC + GOOGLE_CLOUD_PROJECT env var.
        # Gemini 3 thinking is enabled by default ("low" thinking_level is
        # LiteLLM's auto-default for Gemini 3+ when reasoning_effort unset).
        "model_id": "vertex_ai/gemini-3-flash-preview",
        "vertex_project_env": "GOOGLE_CLOUD_PROJECT",
        "vertex_location": "global",
    },
    "gemini-vertex-pro": {
        # Gemini 2.5 Pro via Vertex AI — stronger tool-use reasoning than Flash.
        "model_id": "vertex_ai/gemini-2.5-pro",
        "vertex_project_env": "GOOGLE_CLOUD_PROJECT",
        "vertex_location": "us-central1",
    },
    "gemma4": {
        "model_id": "gemini/gemma-4-26b-a4b-it",
        "api_key_env": "GEMINI_API_KEY",
    },
    "gpt5-mini": {
        "model_id": "openai/gpt-5-mini-2025-08-07",
        "api_key_env": "OPENAI_API_KEY",
    },
    "gpt4o": {
        # Older but well-rounded OpenAI model — faster than GPT-5 series and cheaper per token.
        "model_id": "openai/gpt-4o-2024-08-06",
        "api_key_env": "OPENAI_API_KEY",
    },
    "gpt51": {
        # GPT-5.1 flagship, reasoning.effort defaults to "none" (fast by default).
        # Supports reasoning.effort: none / low / medium / high.
        # "low" enables minimal reasoning — trades some latency for better
        # tool-calling decisions / multilingual handling.
        "model_id": "openai/gpt-5.1-2025-11-13",
        "api_key_env": "OPENAI_API_KEY",
        "reasoning_effort": "low",
    },
    "ollama-cloud": {
        # Model resolved at runtime from OLLAMA_CLOUD_MODEL env var (default: llama3.1:8b)
        "model_prefix": "ollama_chat/",
        "model_env": "OLLAMA_CLOUD_MODEL",
        "model_default": "llama3.1:8b",
        "api_key_env": "OLLAMA_API_KEY",
        "api_base": _OLLAMA_CLOUD_API_BASE,
    },
}


def _resolve_model_id(model_name: str, config: dict) -> str:
    """Resolve the LiteLLM model ID, supporting env-var-based dynamic model names."""
    if "model_env" in config:
        model = os.environ.get(config["model_env"], config["model_default"])
        return f"{config['model_prefix']}{model}"
    return config["model_id"]


def chat_with_model(
    user_message: str,
    session_id: str,
    model_name: str,
    verbose: bool = True,
) -> tuple[str, list[dict]]:
    """Run a query through the specified LLM using LiteLLM.

    Args:
        user_message: The natural language query from the user
        session_id: Session identifier (unused by LiteLLM path, kept for API parity)
        model_name: One of the keys in _MODEL_CONFIG
        verbose: When True (default), print each tool call live to stdout so
            the eval progress looks like the CLI's on_tool_call output.

    Returns:
        Tuple of (text response, tool_calls_detail).
        tool_calls_detail is a list of dicts with keys: tool, args, result_preview.
    """
    if model_name not in _MODEL_CONFIG:
        valid = ", ".join(sorted(_MODEL_CONFIG))
        raise ToolCallError(f"Unknown model '{model_name}'. Valid options: {valid}")

    config = _MODEL_CONFIG[model_name]
    api_key_env = config.get("api_key_env")
    vertex_project_env = config.get("vertex_project_env")

    if vertex_project_env:
        if not os.environ.get(vertex_project_env):
            raise ToolCallError(f"Missing required environment variable: {vertex_project_env}")
    elif api_key_env and not os.environ.get(api_key_env):
        raise ToolCallError(f"Missing required environment variable: {api_key_env}")

    model_id = _resolve_model_id(model_name, config)
    extra_body = config.get("extra_body", {})
    tool_calls_detail: list[dict] = []
    tool_schemas = get_openai_tool_schemas()

    messages: list[dict] = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": user_message},
    ]

    transient_retry_count = 0
    MAX_TRANSIENT_RETRIES = 5
    while True:
        try:
            kwargs: dict = {
                "model": model_id,
                "messages": messages,
                "tools": tool_schemas,
                "tool_choice": "auto",
                "timeout": 120,
            }
            if extra_body:
                kwargs["extra_body"] = extra_body
            reasoning_effort = config.get("reasoning_effort")
            if reasoning_effort:
                # LiteLLM normalizes this top-level kwarg per provider:
                # OpenAI → passes through; Vertex Gemini → maps to thinkingBudget.
                kwargs["reasoning_effort"] = reasoning_effort
            if vertex_project_env:
                # Vertex AI path — ADC handles auth, project/location are explicit.
                kwargs["vertex_project"] = os.environ[vertex_project_env]
                kwargs["vertex_location"] = config.get("vertex_location", "us-central1")
            if "api_base" in config:
                kwargs["api_base"] = config["api_base"]
                # Explicitly pass API key for providers with custom api_base
                if api_key_env and (key := os.environ.get(api_key_env)):
                    kwargs["api_key"] = key
            response = litellm.completion(**kwargs)
            # Successful call — reset transient retry counter.
            transient_retry_count = 0
        except LiteLLMRateLimitError as e:
            m = re.search(r"try again in (\d+(?:\.\d+))s", str(e))
            wait = float(m.group(1)) + 2 if m else 20.0
            time.sleep(wait)
            continue
        except (
            LiteLLMServiceUnavailableError,
            LiteLLMTimeout,
            LiteLLMConnectionError,
        ) as e:
            # Transient provider-side errors (503, timeouts, connection drops).
            # Exponential backoff: 5s, 10s, 20s, 40s, 80s. Fail hard after 5 tries.
            transient_retry_count += 1
            if transient_retry_count > MAX_TRANSIENT_RETRIES:
                raise ToolCallError(
                    f"Transient error persisted after {MAX_TRANSIENT_RETRIES} retries: {e}"
                ) from e
            wait = 5 * (2 ** (transient_retry_count - 1))
            time.sleep(wait)
            continue

        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            return msg.content or "", tool_calls_detail

        # Execute tool calls and feed results back
        messages.append(
            {"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls}
        )

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)

            # Coerce string values to expected Python types
            fn = getattr(_tools, fn_name, None)
            if fn is not None:
                import inspect as _inspect

                for param_name, param in _inspect.signature(fn).parameters.items():
                    if param_name in fn_args and isinstance(fn_args[param_name], str):
                        annotation = param.annotation
                        if annotation is int or annotation == "int":
                            try:
                                fn_args[param_name] = int(fn_args[param_name])
                            except (ValueError, TypeError):
                                pass

            if verbose:
                args_preview = json.dumps(fn_args, ensure_ascii=False)
                if len(args_preview) > 120:
                    args_preview = args_preview[:120] + "..."
                print(f"    → {fn_name}({args_preview})", flush=True)

            try:
                result = getattr(_tools, fn_name)(**fn_args)
            except Exception as e:
                result = {"error": str(e)}

            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) > 4000:
                result_str = result_str[:4000] + "... [truncated]"

            # Short preview for the returned tool_calls_detail (saved to results.json)
            result_preview = result_str[:500] + ("..." if len(result_str) > 500 else "")
            tool_calls_detail.append(
                {
                    "tool": fn_name,
                    "args": fn_args,
                    "result_preview": result_preview,
                }
            )

            if verbose:
                one_line = result_preview.replace("\n", " ")[:160]
                print(f"      ← {one_line}", flush=True)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                }
            )
