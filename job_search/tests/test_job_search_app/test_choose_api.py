"""
Тесты выбора API.
"""

from typing import Any

from job_search.models.job_search_app import JobSearchApp


def test_choose_api_select_hh(app: JobSearchApp, io: dict[str, Any]) -> None:
    """Проверяет выбор HeadHunter API."""

    io["input"].side_effect = ["1"]
    step = app.step_choose_api()
    assert step == "search"
    assert app.selected_api is not None
