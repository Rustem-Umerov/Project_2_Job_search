"""
Тесты API‑пагинации (next_api_page, prev_api_page).
"""

from typing import Any

from job_search.models.job_search_app import JobSearchApp


def test_next_api_page(app: JobSearchApp, io: dict[str, Any]) -> None:
    """Переход на следующую API‑страницу."""

    app.api_current_page = 0
    app.api_total_pages = 3
    app.api_query_params = {"page": 0}

    step = app.step_next_api_page()
    assert step == "search_one_page"
    assert app.api_current_page == 1


def test_prev_api_page(app: JobSearchApp, io: dict[str, Any]) -> None:
    """Переход на предыдущую API‑страницу."""

    app.api_current_page = 2
    app.api_total_pages = 3
    app.api_query_params = {"page": 2}

    step = app.step_prev_api_page()
    assert step == "search_one_page"
    assert app.api_current_page == 1
