"""LiteLLM multi-model chat interface for ghibli eval pipeline."""

from __future__ import annotations

import json
import os
import re
import time

import litellm
from litellm.exceptions import APIConnectionError as LiteLLMConnectionError
from litellm.exceptions import RateLimitError as LiteLLMRateLimitError

import ghibli.tools as _tools
from ghibli.prompt import get_system_prompt
from ghibli.tool_schema import get_openai_tool_schemas
from ghibli.exceptions import ToolCallError

# Fixed date so eval ground truth remains reproducible across runs.
_EVAL_DATE = "2026-04-22"

_OLLAMA_CLOUD_API_BASE = "https://ollama.com"

_MODEL_CONFIG: dict[str, dict] = {
    "gemini": {
        "model_id": "gemini/gemini-2.5-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "gemma4": {
        "model_id": "gemini/gemma-4-26b-a4b-it",
        "api_key_env": "GEMINI_API_KEY",
    },
    "gpt4o-mini": {
        "model_id": "openai/gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
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
) -> tuple[str, list[str]]:
    """Run a query through the specified LLM using LiteLLM and return (reply, tools_called).

    Args:
        user_message: The natural language query from the user
        session_id: Session identifier (unused by LiteLLM path, kept for API parity)
        model_name: One of "gemini", "gemma4", "gpt4o-mini", "ollama-cloud"

    Returns:
        Tuple of (text response, list of tool names called)
    """
    if model_name not in _MODEL_CONFIG:
        valid = ", ".join(sorted(_MODEL_CONFIG))
        raise ToolCallError(
            f"Unknown model '{model_name}'. Valid options: {valid}"
        )

    config = _MODEL_CONFIG[model_name]
    api_key_env = config.get("api_key_env")
    if api_key_env and not os.environ.get(api_key_env):
        raise ToolCallError(
            f"Missing required environment variable: {api_key_env}"
        )

    model_id = _resolve_model_id(model_name, config)
    extra_body = config.get("extra_body", {})
    tools_called: list[str] = []
    tool_schemas = get_openai_tool_schemas()

    messages: list[dict] = [
        {"role": "system", "content": get_system_prompt(date=_EVAL_DATE)},
        {"role": "user", "content": user_message},
    ]

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
            if "api_base" in config:
                kwargs["api_base"] = config["api_base"]
                # Explicitly pass API key for providers with custom api_base
                if api_key_env and (key := os.environ.get(api_key_env)):
                    kwargs["api_key"] = key
            response = litellm.completion(**kwargs)
        except LiteLLMRateLimitError as e:
            m = re.search(r"try again in (\d+(?:\.\d+))s", str(e))
            wait = float(m.group(1)) + 2 if m else 20.0
            time.sleep(wait)
            continue
        except LiteLLMConnectionError as e:
            raise ToolCallError(f"Connection error: {e}") from e

        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            return msg.content or "", tools_called

        # Execute tool calls and feed results back
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            tools_called.append(fn_name)

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

            try:
                result = getattr(_tools, fn_name)(**fn_args)
            except Exception as e:
                result = {"error": str(e)}

            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) > 4000:
                result_str = result_str[:4000] + "... [truncated]"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })
