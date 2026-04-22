import json
import os

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from ghibli import sessions, tools
from ghibli.exceptions import ToolCallError
from ghibli.tools import (
    get_repository,
    get_user,
    list_issues,
    list_pull_requests,
    list_releases,
    search_repositories,
)

_TOOLS = [
    search_repositories,
    get_repository,
    list_issues,
    list_pull_requests,
    get_user,
    list_releases,
]

_SYSTEM_PROMPT = """\
You are ghibli, a GitHub assistant that answers questions using the GitHub API.

## Typo correction
Before calling any tool, silently correct obvious typos in repository names, \
organization names, and programming language names. For example:
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
  and mention this is an approximation. GitHub Search API does not have a \
  trending endpoint.

## Contradictory or impossible conditions
If a query is logically impossible (e.g. a repo with 1 million stars but \
0 commits), explain why the condition cannot be satisfied rather than \
attempting a search you know will return nothing.

## Language
Always reply in the same language the user wrote in.
"""


def chat(user_message: str, session_id: str, json_output: bool) -> str:
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
                model="gemini-2.5-flash",
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
