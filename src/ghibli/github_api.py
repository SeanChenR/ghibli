import os
import re

import httpx

from ghibli.exceptions import GitHubAPIError, ToolCallError

_BASE_URL = "https://api.github.com"

_TOOL_MAP: dict[str, tuple[str, str]] = {
    "search_repositories": ("GET", "/search/repositories"),
    "get_repository": ("GET", "/repos/{owner}/{repo}"),
    "list_issues": ("GET", "/repos/{owner}/{repo}/issues"),
    "list_pull_requests": ("GET", "/repos/{owner}/{repo}/pulls"),
    "get_user": ("GET", "/users/{username}"),
    "list_releases": ("GET", "/repos/{owner}/{repo}/releases"),
    # Extended tools
    "get_languages": ("GET", "/repos/{owner}/{repo}/languages"),
    "list_contributors": ("GET", "/repos/{owner}/{repo}/contributors"),
    "list_commits": ("GET", "/repos/{owner}/{repo}/commits"),
    "search_code": ("GET", "/search/code"),
    "search_users": ("GET", "/search/users"),
    "search_issues": ("GET", "/search/issues"),
    "get_readme": ("GET", "/repos/{owner}/{repo}/readme"),
}

# Per-tool Accept header overrides (default: application/vnd.github+json)
_TOOL_ACCEPT: dict[str, str] = {
    "search_code": "application/vnd.github.text-match+json",
}

_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")


def execute(tool_name: str, args: dict) -> dict | list:
    if tool_name not in _TOOL_MAP:
        raise ToolCallError(f"Unknown tool: {tool_name}")

    method, endpoint_template = _TOOL_MAP[tool_name]
    remaining_args = dict(args)

    path_params = _PATH_PARAM_RE.findall(endpoint_template)
    endpoint = endpoint_template
    for param in path_params:
        endpoint = endpoint.replace(f"{{{param}}}", str(remaining_args.pop(param)))

    url = f"{_BASE_URL}{endpoint}"

    headers: dict[str, str] = {
        "User-Agent": "ghibli/0.1.0",
        "Accept": _TOOL_ACCEPT.get(tool_name, "application/vnd.github+json"),
        "X-GitHub-Api-Version": "2022-11-28",
    }

    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.request(
            method, url, params=remaining_args, headers=headers, timeout=10.0,
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise GitHubAPIError(str(e), status_code=e.response.status_code) from e
    except httpx.TimeoutException as e:
        raise GitHubAPIError("GitHub API request timeout", status_code=408) from e

    return response.json()
