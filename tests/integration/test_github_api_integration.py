import pytest

from ghibli.github_api import execute


@pytest.mark.integration
def test_search_repositories_live():
    result = execute("search_repositories", {"q": "python", "per_page": 3})
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 3
