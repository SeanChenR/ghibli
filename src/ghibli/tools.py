import base64
from typing import Optional

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


def get_languages(owner: str, repo: str) -> dict | list:
    """Get the programming language breakdown (bytes of code) for a repository.

    Args:
        owner: Repository owner username or organisation name
        repo: Repository name
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("get_languages", args)


def list_contributors(
    owner: str,
    repo: str,
    per_page: int = 10,
) -> dict | list:
    """List contributors to a GitHub repository, sorted by number of commits.

    Args:
        owner: Repository owner username or organisation name
        repo: Repository name
        per_page: Number of results per page, max 100 (default: 10)
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("list_contributors", args)


def list_commits(
    owner: str,
    repo: str,
    sha: Optional[str] = None,
    author: Optional[str] = None,
    per_page: int = 10,
) -> dict | list:
    """List commits for a GitHub repository.

    Args:
        owner: Repository owner username or organisation name
        repo: Repository name
        sha: Branch name, tag, or commit SHA to start listing from (default: default branch)
        author: GitHub username to filter commits by author
        per_page: Number of results per page, max 100 (default: 10)
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("list_commits", args)


def search_code(
    q: str,
    per_page: int = 10,
) -> dict | list:
    """Search for code across all public GitHub repositories.

    Args:
        q: Search query, supports qualifiers like repo:owner/name, language:python,
           path:src, extension:py, filename:Dockerfile
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("search_code", args)


def search_users(
    q: str,
    sort: str = "followers",
    per_page: int = 10,
) -> dict | list:
    """Search for GitHub users and organisations.

    Args:
        q: Search query, supports qualifiers like type:org, language:python,
           location:taiwan, followers:>1000
        sort: Sort by followers, repositories, or joined (default: followers)
        per_page: Number of results per page, max 100 (default: 10)
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("search_users", args)


def search_issues(
    q: str,
    sort: str = "created",
    order: str = "desc",
    per_page: int = 10,
) -> dict | list:
    """Search for issues and pull requests across all public GitHub repositories.

    Args:
        q: Search query, supports qualifiers like is:issue, is:pr, is:open, is:closed,
           label:bug, label:good-first-issue, language:python, repo:owner/name,
           author:username, involves:username, milestone:name
        sort: Sort by created, updated, comments, or reactions (default: created)
        order: Sort order asc or desc (default: desc)
        per_page: Number of results per page, max 100 (default: 10)
    """
    args = {k: v for k, v in locals().items() if v is not None}
    return github_api.execute("search_issues", args)


def get_readme(owner: str, repo: str) -> dict | list:
    """Get the decoded README content of a GitHub repository.

    Args:
        owner: Repository owner username or organisation name
        repo: Repository name
    """
    result = github_api.execute("get_readme", {"owner": owner, "repo": repo})
    if isinstance(result, dict) and result.get("encoding") == "base64" and "content" in result:
        raw = base64.b64decode(result["content"].replace("\n", "")).decode("utf-8", errors="replace")
        return {
            "name": result.get("name"),
            "path": result.get("path"),
            "size": result.get("size"),
            "content": raw[:3000],
            "truncated": len(raw) > 3000,
        }
    return result
