import base64
from unittest.mock import patch

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


# --- 1.1: all 13 functions importable ---

def test_all_thirteen_tools_importable():
    assert search_repositories is not None
    assert get_repository is not None
    assert list_issues is not None
    assert list_pull_requests is not None
    assert get_user is not None
    assert list_releases is not None
    assert get_languages is not None
    assert list_contributors is not None
    assert list_commits is not None
    assert search_code is not None
    assert search_users is not None
    assert search_issues is not None
    assert get_readme is not None


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


# --- extended tools ---

def test_get_languages_calls_execute():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = {"Python": 500000, "HTML": 1000}
        result = get_languages(owner="pallets", repo="flask")
    assert mock_exec.call_args[0][0] == "get_languages"
    assert mock_exec.call_args[0][1] == {"owner": "pallets", "repo": "flask"}
    assert result == {"Python": 500000, "HTML": 1000}


def test_list_contributors_calls_execute():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = [{"login": "yyx990803", "contributions": 2583}]
        list_contributors(owner="vuejs", repo="vue", per_page=5)
    assert mock_exec.call_args[0][0] == "list_contributors"
    args = mock_exec.call_args[0][1]
    assert args["owner"] == "vuejs"
    assert args["repo"] == "vue"
    assert args["per_page"] == 5


def test_list_commits_with_author_filter():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = [{"sha": "abc123"}]
        list_commits(owner="vuejs", repo="vue", author="yyx990803", per_page=3)
    args = mock_exec.call_args[0][1]
    assert args["owner"] == "vuejs"
    assert args["repo"] == "vue"
    assert args["author"] == "yyx990803"
    assert args["per_page"] == 3


def test_list_commits_omits_none_optional_params():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = []
        list_commits(owner="torvalds", repo="linux")
    args = mock_exec.call_args[0][1]
    assert "sha" not in args
    assert "author" not in args


def test_search_code_calls_execute():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = {"total_count": 5, "items": []}
        search_code(q="asyncio.run language:python")
    assert mock_exec.call_args[0][0] == "search_code"
    assert mock_exec.call_args[0][1]["q"] == "asyncio.run language:python"


def test_search_users_calls_execute():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = {"total_count": 19, "items": []}
        search_users(q="followers:>10000 language:go", per_page=5)
    args = mock_exec.call_args[0][1]
    assert args["q"] == "followers:>10000 language:go"
    assert args["per_page"] == 5


def test_search_issues_calls_execute():
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = {"total_count": 298, "items": []}
        search_issues(q="is:issue label:good-first-issue language:rust is:open")
    assert mock_exec.call_args[0][0] == "search_issues"


def test_get_readme_decodes_base64_content():
    raw_text = "# Flask\nA lightweight WSGI web application framework."
    encoded = base64.b64encode(raw_text.encode()).decode()
    fake_response = {
        "name": "README.md",
        "path": "README.md",
        "size": len(raw_text),
        "encoding": "base64",
        "content": encoded,
    }
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = fake_response
        result = get_readme(owner="pallets", repo="flask")
    assert isinstance(result, dict)
    assert result["content"] == raw_text
    assert result["name"] == "README.md"
    assert result["truncated"] is False


def test_get_readme_truncates_long_content():
    raw_text = "x" * 4000
    encoded = base64.b64encode(raw_text.encode()).decode()
    fake_response = {"name": "README.md", "path": "README.md", "size": 4000,
                     "encoding": "base64", "content": encoded}
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = fake_response
        result = get_readme(owner="owner", repo="repo")
    assert isinstance(result, dict)
    assert len(result["content"]) == 3000
    assert result["truncated"] is True


def test_get_readme_returns_raw_response_when_not_base64():
    fake_response = {"message": "Not Found"}
    with patch("ghibli.tools.github_api.execute") as mock_exec:
        mock_exec.return_value = fake_response
        result = get_readme(owner="owner", repo="nonexistent")
    assert result == {"message": "Not Found"}
