import json
import os
import re
import sys
import time
from typing import Callable

import litellm
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from litellm.exceptions import APIConnectionError as LiteLLMConnectionError
from litellm.exceptions import RateLimitError as LiteLLMRateLimitError

from ghibli import sessions, tools
from ghibli.exceptions import ToolCallError
from ghibli.prompt import get_system_prompt
from ghibli.tool_schema import get_openai_tool_schemas
from ghibli.tools import (
    get_languages,
    get_readme,
    get_repository,
    get_user,
    list_commits,
    list_contributors,
    list_issues,
    list_pull_requests,
    list_releases,
    search_code,
    search_issues,
    search_repositories,
    search_users,
)

_TOOLS = [
    search_repositories,
    get_repository,
    list_issues,
    list_pull_requests,
    get_user,
    list_releases,
    get_languages,
    list_contributors,
    list_commits,
    search_code,
    search_users,
    search_issues,
    get_readme,
]

_OLLAMA_CLOUD_API_BASE = "https://ollama.com"


def _safe_invoke_callback(
    cb: Callable[[str, dict], None] | None,
    name: str,
    args: dict,
) -> None:
    """Invoke a tool-dispatch callback; swallow + log any exception so caller survives."""
    if cb is None:
        return
    try:
        cb(name, dict(args))
    except Exception as e:
        print(f"on_tool_call callback error: {e}", file=sys.stderr)


def _chat_litellm(
    user_message: str,
    session_id: str,
    model_id: str,
    api_key: str,
    provider_label: str,
    api_base: str | None = None,
    on_tool_call: Callable[[str, dict], None] | None = None,
) -> str:
    """Chat via LiteLLM (shared by Ollama Cloud and OpenAI paths)."""
    tool_schemas = get_openai_tool_schemas()

    prior_turns = sessions.get_turns(session_id)
    messages: list[dict] = [{"role": "system", "content": get_system_prompt()}]
    for t in prior_turns:
        messages.append({"role": t["role"], "content": json.loads(t["content_json"])})
    messages.append({"role": "user", "content": user_message})

    while True:
        try:
            kwargs: dict = {
                "model": model_id,
                "messages": messages,
                "tools": tool_schemas,
                "tool_choice": "auto",
                "timeout": 120,
                "api_key": api_key,
            }
            if api_base:
                kwargs["api_base"] = api_base
            response = litellm.completion(**kwargs)
        except LiteLLMRateLimitError as e:
            m = re.search(r"try again in (\d+(?:\.\d+))s", str(e))
            wait = float(m.group(1)) + 2 if m else 20.0
            time.sleep(wait)
            continue
        except LiteLLMConnectionError as e:
            raise ToolCallError(f"{provider_label} connection error: {e}") from e

        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            final_text = msg.content or ""
            sessions.append_turn(session_id, "user", user_message)
            sessions.append_turn(session_id, "assistant", final_text)
            return final_text

        messages.append(
            {"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls}
        )

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            _safe_invoke_callback(on_tool_call, fn_name, fn_args)
            try:
                result = getattr(tools, fn_name)(**fn_args)
            except Exception as e:
                result = {"error": str(e)}
            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) > 8000:
                result_str = result_str[:8000] + "... [truncated]"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                }
            )


def chat(
    user_message: str,
    session_id: str,
    json_output: bool,
    model: str | None = None,
    *,
    on_tool_call: Callable[[str, dict], None] | None = None,
) -> str:
    ghibli_model = model or os.environ.get("GHIBLI_MODEL")
    if ghibli_model is None:
        raise ToolCallError(
            "No model specified. Pass `model=<id>` to chat(), set GHIBLI_MODEL, "
            "or use the CLI's --model / picker to resolve one."
        )

    # Route to Ollama Cloud when GHIBLI_MODEL=ollama:<model-slug>
    if ghibli_model.startswith("ollama:"):
        ollama_model = ghibli_model[len("ollama:") :]
        api_key = os.environ.get("OLLAMA_API_KEY")
        if not api_key:
            raise ToolCallError(
                "OLLAMA_API_KEY is required for Ollama Cloud mode. "
                "Get yours at https://ollama.com/settings/keys"
            )
        return _chat_litellm(
            user_message,
            session_id,
            model_id=f"ollama_chat/{ollama_model}",
            api_key=api_key,
            provider_label="Ollama Cloud",
            api_base=_OLLAMA_CLOUD_API_BASE,
            on_tool_call=on_tool_call,
        )

    # Route to OpenAI when GHIBLI_MODEL=openai:<model>
    if ghibli_model.startswith("openai:"):
        openai_model = ghibli_model[len("openai:") :]
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ToolCallError(
                "OPENAI_API_KEY is required for OpenAI mode. "
                "Get yours at https://platform.openai.com/api-keys"
            )
        return _chat_litellm(
            user_message,
            session_id,
            model_id=f"openai/{openai_model}",
            api_key=api_key,
            provider_label="OpenAI",
            on_tool_call=on_tool_call,
        )

    # Route Gemma (and other Gemini-hosted open-weight variants) via LiteLLM with `gemma:` prefix
    if ghibli_model.startswith("gemma:"):
        gemma_slug = ghibli_model[len("gemma:") :]
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ToolCallError(
                "GEMINI_API_KEY is required for `gemma:` LiteLLM mode. "
                "Get yours at https://aistudio.google.com/app/apikey"
            )
        return _chat_litellm(
            user_message,
            session_id,
            model_id=f"gemini/{gemma_slug}",
            api_key=api_key,
            provider_label="Gemma",
            on_tool_call=on_tool_call,
        )

    # --- Gemini native SDK path ---
    api_key = os.environ.get("GEMINI_API_KEY")
    vertex_project = os.environ.get("GOOGLE_CLOUD_PROJECT")

    if not api_key and not vertex_project:
        raise ToolCallError(
            "Gemini authentication not configured: "
            "set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT"
        )

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client(
            vertexai=True,
            project=vertex_project,
            location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )

    prior_turns = sessions.get_turns(session_id)
    contents: list = [
        {
            "role": "model" if t["role"] == "assistant" else t["role"],
            "parts": [{"text": json.loads(t["content_json"])}],
        }
        for t in prior_turns
    ]
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    while True:
        try:
            response = client.models.generate_content(
                model=ghibli_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=get_system_prompt(),
                    tools=_TOOLS,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )
        except genai_errors.APIError as e:
            raise ToolCallError(f"Gemini API error: {e.message}") from e

        if not response.function_calls:
            final_text = response.text
            sessions.append_turn(session_id, "user", user_message)
            sessions.append_turn(session_id, "assistant", final_text)
            return final_text

        contents.append(response.candidates[0].content)

        tool_parts = []
        for fc in response.function_calls:
            _safe_invoke_callback(on_tool_call, fc.name, dict(fc.args))
            try:
                result = getattr(tools, fc.name)(**fc.args)
            except Exception as e:
                result = {"error": str(e)}
            tool_parts.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )
        contents.append(types.Content(role="tool", parts=tool_parts))
