"""
Тесты добавления вакансий.
"""

from typing import Any

from job_search.models.job_search_app import JobSearchApp
from job_search.models.vacancy import Vacancy


def test_add_one_vacancy(app: JobSearchApp, io: dict[str, Any], vacancy: Vacancy) -> None:
    """Добавление одной вакансии."""

    app.api_page_vacancies = [vacancy]
    app.api_total_vacancies = 1
    app.api_page_size = 10
    app.api_current_page = 0
    app.ui_page_size = 10

    io["input"].side_effect = ["1"]

    app.step_add_one_vacancy()
    assert len(app.vacancies) == 1


def test_add_page_vacancies(app: JobSearchApp, io: dict[str, Any], vacancy: Vacancy) -> None:
    """Добавление страницы вакансий."""

    app.api_page_vacancies = [vacancy, vacancy]
    app.api_total_vacancies = 2
    app.ui_page_size = 10

    app.step_add_page_vacancies()
    assert len(app.vacancies) == 1  # дубликаты не добавляются
