import os

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from ghibli import tools
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


def chat(user_message: str, session_id: str, json_output: bool) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    vertex_project = os.environ.get("VERTEX_PROJECT")

    if not api_key and not vertex_project:
        raise ToolCallError(
            "Gemini authentication not configured: set GEMINI_API_KEY or VERTEX_PROJECT"
        )

    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        client = genai.Client(
            vertexai=True,
            project=vertex_project,
            location=os.environ.get("VERTEX_LOCATION", "us-central1"),
        )

    contents: list = [{"role": "user", "parts": [{"text": user_message}]}]

    while True:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=_TOOLS,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
            )
        except genai_errors.APIError as e:
            raise ToolCallError(f"Gemini API error: {e.message}") from e

        if not response.function_calls:
            return response.text

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
