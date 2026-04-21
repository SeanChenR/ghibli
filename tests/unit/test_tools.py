from unittest.mock import patch

from ghibli.tools import (
    get_repository,
    get_user,
    list_issues,
    list_pull_requests,
    list_releases,
    search_repositories,
)


# --- 1.1: all 6 functions importable ---

def test_all_six_tools_importable():
    assert search_repositories is not None
    assert get_repository is not None
    assert list_issues is not None
    assert list_pull_requests is not None
    assert get_user is not None
    assert list_releases is not None


# --- 1.2: search_repositories calls execute ---

def test_search_repositories_calls_execute():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = {"total_count": 0, "items": []}
        search_repositories(q="python", sort="stars")
    call_args = mock_exec.call_args[0]
    assert call_args[0] == "search_repositories"
    assert call_args[1]["q"] == "python"
    assert call_args[1]["sort"] == "stars"


# --- 1.3: get_repository calls execute ---

def test_get_repository_calls_execute():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = {}
        get_repository(owner="torvalds", repo="linux")
    call_args = mock_exec.call_args[0]
    assert call_args[0] == "get_repository"
    assert call_args[1] == {"owner": "torvalds", "repo": "linux"}
