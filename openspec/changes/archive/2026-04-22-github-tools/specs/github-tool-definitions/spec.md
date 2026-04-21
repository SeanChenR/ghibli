## ADDED Requirements

### Requirement: Six GitHub tool functions defined in tools.py

The module `src/ghibli/tools.py` SHALL define exactly 6 Python functions with type annotations and docstrings that act as Gemini function declarations. Each function SHALL accept keyword arguments matching the GitHub API operation's parameters and call `github_api.execute(tool_name, args)` internally.

The 6 functions and their required parameters are:

| Function | Required params | Optional params |
|---|---|---|
| `search_repositories(q, sort, order, per_page)` | `q: str` | `sort: str = "stars"`, `order: str = "desc"`, `per_page: int = 10` |
| `get_repository(owner, repo)` | `owner: str`, `repo: str` | — |
| `list_issues(owner, repo, state, per_page)` | `owner: str`, `repo: str` | `state: str = "open"`, `per_page: int = 10` |
| `list_pull_requests(owner, repo, state, per_page)` | `owner: str`, `repo: str` | `state: str = "open"`, `per_page: int = 10` |
| `get_user(username)` | `username: str` | — |
| `list_releases(owner, repo, per_page)` | `owner: str`, `repo: str` | `per_page: int = 10` |

#### Scenario: search_repositories calls execute with correct tool_name

- **WHEN** `search_repositories(q="python", sort="stars")` is called
- **THEN** it calls `github_api.execute("search_repositories", {"q": "python", "sort": "stars", ...})` and returns the result

#### Scenario: get_repository calls execute with owner and repo

- **WHEN** `get_repository(owner="torvalds", repo="linux")` is called
- **THEN** it calls `github_api.execute("get_repository", {"owner": "torvalds", "repo": "linux"})` and returns the result

#### Scenario: All 6 functions are importable from tools module

- **WHEN** `from ghibli.tools import search_repositories, get_repository, list_issues, list_pull_requests, get_user, list_releases` is executed
- **THEN** all 6 names are successfully imported with no error
