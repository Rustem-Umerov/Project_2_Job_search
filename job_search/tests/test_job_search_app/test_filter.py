"""
Тесты фильтра.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from job_search.models.job_search_app import JobSearchApp


@patch("job_search.filters.interactive_input.InteractiveFilterInput.run")
def test_filter_apply(mock_run: MagicMock, app: JobSearchApp, io: dict[str, Any]) -> None:
    """Применение фильтра."""

    mock_run.return_value = {"salary_from": 100}

    io["input"].side_effect = ["3"]

    app.step_filter()
    assert app.filter == {"salary_from": 100}
