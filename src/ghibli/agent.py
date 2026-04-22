import json
import os
import re
import time

import litellm
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from litellm.exceptions import APIConnectionError as LiteLLMConnectionError
from litellm.exceptions import RateLimitError as LiteLLMRateLimitError

from ghibli import sessions, tools
from ghibli.exceptions import ToolCallError
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

_SYSTEM_PROMPT = """\
You are ghibli, a GitHub assistant that answers questions using the GitHub API.

## Typo correction
Before calling any tool, silently correct obvious typos in repository names, \
organisation names, and programming language names. For example:
- "pytohn" → "python", "javascrpit" → "javascript", "djangoo" → "django"
- "microsfot" → "microsoft", "reakt" → "react", "linus" (as a repo) → "linux"
If a corrected name produces a 404 error, inform the user of the correction \
you attempted.

## search_repositories — q is always required
The `q` parameter is mandatory for every call to search_repositories. \
Never call search_repositories() without q.
- For "most popular" / "best" queries with no specific keyword, use q="stars:>10000".
- For "interesting open source" queries, use q="stars:>1000 pushed:>2024-01-01".
- For "recent trending" / "最近很紅", use q="created:>2024-01-01 stars:>1000" \
  and mention this is an approximation.

## Tool selection — critical rules
Each tool has a strict scope. Using the wrong tool is always incorrect:
- list_issues / list_pull_requests: ONLY for a SPECIFIC repo (owner + repo required). \
  NEVER use for cross-repo searches.
- search_issues: For finding issues or PRs ACROSS multiple repos. \
  Use when no specific single repo is mentioned.
- get_repository: Returns repo metadata only — NOT README content, NOT full language breakdown.
- get_languages: For the FULL language breakdown (bytes per language). \
  Do NOT substitute get_repository.
- get_readme: Use when the user wants to READ the README content. \
  get_repository does not include README text.
- search_users: To FIND developers or organisations by criteria. \
  Do NOT use search_repositories for finding people.
- search_code: To find code PATTERNS or function usage across repos. \
  Do NOT use search_repositories when the user is asking about code content.

## Contradictory or impossible conditions
Do NOT call any tool for logically impossible queries — explain why instead:
- No public repository has more than 500,000 stars; "1 million stars" is impossible.
- Fork counts are almost always less than star counts (roughly 5–20% of stars). \
  A repository with forks exceeding stars by 100× or 1000× has never existed.
- Any other empirically impossible combination.
NOTE: stars being much greater than forks is COMPLETELY NORMAL and is NOT a contradiction.

## Language
Always reply in the same language the user wrote in.
"""


def _chat_ollama_cloud(user_message: str, session_id: str, model_name: str) -> str:
    """Chat via Ollama Cloud using LiteLLM. model_name is the bare model slug."""
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        raise ToolCallError(
            "OLLAMA_API_KEY is required for Ollama Cloud mode. "
            "Get yours at https://ollama.com/settings/keys"
        )

    model_id = f"ollama_chat/{model_name}"
    tool_schemas = get_openai_tool_schemas()

    prior_turns = sessions.get_turns(session_id)
    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for t in prior_turns:
        messages.append({"role": t["role"], "content": json.loads(t["content_json"])})
    messages.append({"role": "user", "content": user_message})

    while True:
        try:
            response = litellm.completion(
                model=model_id,
                messages=messages,
                tools=tool_schemas,
                tool_choice="auto",
                timeout=120,
                api_base=_OLLAMA_CLOUD_API_BASE,
                api_key=api_key,
            )
        except LiteLLMRateLimitError as e:
            m = re.search(r"try again in (\d+(?:\.\d+))s", str(e))
            wait = float(m.group(1)) + 2 if m else 20.0
            time.sleep(wait)
            continue
        except LiteLLMConnectionError as e:
            raise ToolCallError(f"Ollama Cloud connection error: {e}") from e

        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            final_text = msg.content or ""
            sessions.append_turn(session_id, "user", user_message)
            sessions.append_turn(session_id, "assistant", final_text)
            return final_text

        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            try:
                result = getattr(tools, fn_name)(**fn_args)
            except Exception as e:
                raise ToolCallError(f"{fn_name} failed: {e}") from e
            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) > 8000:
                result_str = result_str[:8000] + "... [truncated]"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })


def chat(user_message: str, session_id: str, json_output: bool) -> str:
    ghibli_model = os.environ.get("GHIBLI_MODEL", "gemini-2.5-flash")

    # Route to Ollama Cloud when GHIBLI_MODEL=ollama:<model-slug>
    if ghibli_model.startswith("ollama:"):
        ollama_model = ghibli_model[len("ollama:"):]
        return _chat_ollama_cloud(user_message, session_id, ollama_model)

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
                    system_instruction=_SYSTEM_PROMPT,
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
            try:
                result = getattr(tools, fc.name)(**fc.args)
            except Exception as e:
                raise ToolCallError(f"{fc.name} failed: {e}") from e
            tool_parts.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )
        contents.append(types.Content(role="tool", parts=tool_parts))
