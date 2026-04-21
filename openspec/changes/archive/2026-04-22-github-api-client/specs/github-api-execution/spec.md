## ADDED Requirements

### Requirement: execute function accepts tool_name and args and returns parsed JSON

The function `execute(tool_name: str, args: dict) -> dict | list` in `src/ghibli/github_api.py` SHALL look up `tool_name` in an internal mapping table `_TOOL_MAP` that maps each of the 6 supported tool names to an endpoint template and HTTP method. It SHALL build the full URL as `https://api.github.com{endpoint}`, substituting any path parameters from `args` (e.g., `owner`, `repo`), pass remaining `args` as query parameters, and return the parsed JSON body as a Python `dict` or `list`.

The 6 supported tool names and their endpoints are:
- `search_repositories` → `GET /search/repositories`
- `get_repository` → `GET /repos/{owner}/{repo}`
- `list_issues` → `GET /repos/{owner}/{repo}/issues`
- `list_pull_requests` → `GET /repos/{owner}/{repo}/pulls`
- `get_user` → `GET /users/{username}`
- `list_releases` → `GET /repos/{owner}/{repo}/releases`

#### Scenario: search_repositories returns parsed dict

- **WHEN** `execute("search_repositories", {"q": "python", "sort": "stars"})` is called
- **THEN** the function sends `GET https://api.github.com/search/repositories?q=python&sort=stars` and returns a `dict`

#### Scenario: get_repository substitutes path parameters

- **WHEN** `execute("get_repository", {"owner": "torvalds", "repo": "linux"})` is called
- **THEN** the function sends `GET https://api.github.com/repos/torvalds/linux` with no extra query params

### Requirement: Unknown tool_name raises ToolCallError

When `tool_name` is not one of the 6 supported names, the function SHALL raise `ToolCallError` with a message identifying the unknown tool name.

#### Scenario: Unknown tool raises ToolCallError

- **WHEN** `execute("delete_everything", {})` is called
- **THEN** `ToolCallError` is raised with a message containing `"delete_everything"`

### Requirement: GITHUB_TOKEN used for authentication when available

The function SHALL read `GITHUB_TOKEN` from environment variables. When the token is present, the request SHALL include the header `Authorization: Bearer <token>`. When the token is absent, the request is sent without authentication.

#### Scenario: Token present adds Authorization header

- **WHEN** `GITHUB_TOKEN` is set in the environment and `execute()` is called
- **THEN** the outgoing HTTP request includes `Authorization: Bearer <token>` header

#### Scenario: Missing token sends unauthenticated request

- **WHEN** `GITHUB_TOKEN` is not set in the environment
- **THEN** no `Authorization` header is sent and the request proceeds normally

### Requirement: User-Agent header always set

Every request to the GitHub API SHALL include the header `User-Agent: ghibli/0.1.0`. GitHub's API rejects requests without a User-Agent.

#### Scenario: User-Agent header present on all requests

- **WHEN** any `execute()` call is made
- **THEN** the outgoing HTTP request contains `User-Agent: ghibli/0.1.0`

### Requirement: HTTP 4xx and 5xx responses raise GitHubAPIError

When the GitHub API responds with a 4xx or 5xx status code, the function SHALL raise `GitHubAPIError` with the HTTP status code stored in `error.status_code`.

#### Scenario: 404 response raises GitHubAPIError with status_code 404

- **WHEN** the GitHub API returns HTTP 404
- **THEN** `GitHubAPIError` is raised with `error.status_code == 404`

#### Scenario: 403 rate limit response raises GitHubAPIError

- **WHEN** the GitHub API returns HTTP 403
- **THEN** `GitHubAPIError` is raised with `error.status_code == 403`

#### Scenario: 500 server error raises GitHubAPIError

- **WHEN** the GitHub API returns HTTP 500
- **THEN** `GitHubAPIError` is raised with `error.status_code == 500`

### Requirement: Request timeout set to 10 seconds

Every HTTP request SHALL have a timeout of 10 seconds. If the request exceeds the timeout, `GitHubAPIError` SHALL be raised with a message indicating a timeout.

#### Scenario: Timeout raises GitHubAPIError

- **WHEN** the GitHub API does not respond within 10 seconds
- **THEN** `GitHubAPIError` is raised with a message containing `"timeout"`
