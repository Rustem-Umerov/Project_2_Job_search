"""
Тесты пагинации результатов поиска.
"""

from typing import Any

from job_search.models.job_search_app import JobSearchApp
from job_search.models.vacancy import Vacancy


def test_show_results_next_page(app: JobSearchApp, io: dict[str, Any], vacancy: Vacancy) -> None:
    """Переход на следующую страницу результатов."""

    app.vacancies = [vacancy] * 15
    app.page_size = 10
    app.current_page = 1

    io["input"].side_effect = ["3"]

    step = app.step_show_results()
    assert step == "next_show_results"
