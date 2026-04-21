from ghibli import github_api


def search_repositories(
    q: str,
    sort: str = "stars",
    order: str = "desc",
    per_page: int = 10,
) -> dict | list:
    """Search GitHub repositories by keyword, language, or topic.

    Args:
        q: Search query (e.g., "python machine learning", "language:python stars:>1000")
        sort: Sort by stars, forks, help-wanted-issues, or updated (default: stars)
        order: Sort order asc or desc (default: desc)
        per_page: Number of results per page, max 100 (default: 10)
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("search_repositories", args)


def get_repository(owner: str, repo: str) -> dict | list:
    """Get details about a specific GitHub repository.

    Args:
        owner: Repository owner username or organisation name
        repo: Repository name
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("get_repository", args)


def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 10,
) -> dict | list:
    """List issues for a GitHub repository.

    Args:
        owner: Repository owner username or organisation name
        repo: Repository name
        state: Filter issues by state: open, closed, or all (default: open)
        per_page: Number of results per page, max 100 (default: 10)
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("list_issues", args)


def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 10,
) -> dict | list:
    """List pull requests for a GitHub repository.

    Args:
        owner: Repository owner username or organisation name
        repo: Repository name
        state: Filter PRs by state: open, closed, or all (default: open)
        per_page: Number of results per page, max 100 (default: 10)
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("list_pull_requests", args)


def get_user(username: str) -> dict | list:
    """Get public profile information for a GitHub user.

    Args:
        username: GitHub username
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("get_user", args)


def list_releases(
    owner: str,
    repo: str,
    per_page: int = 10,
) -> dict | list:
    """List releases for a GitHub repository.

    Args:
        owner: Repository owner username or organisation name
        repo: Repository name
        per_page: Number of results per page, max 100 (default: 10)
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("list_releases", args)
