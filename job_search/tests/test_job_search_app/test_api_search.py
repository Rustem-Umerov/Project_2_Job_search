"""
Тесты поиска вакансий через API.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from job_search.api.types import VacancyResult
from job_search.models.job_search_app import JobSearchApp


def test_search_one_page_success(app: JobSearchApp, io: dict[str, Any], vacancy_result: VacancyResult) -> None:
    """Успешный поиск одной страницы."""

    app.selected_api = MagicMock()
    app.selected_api.get_vacancies.return_value = vacancy_result

    io["input"].side_effect = [
        "python",  # keyword
        "нет",  # регион
        "нет",  # зарплата
        "2",  # режим: по одной странице
        "нет",  # не указывать per_page
        "нет",  # не указывать номер страницы
        "0",  # номер страницы по умолчанию
    ]

    step = app.step_search()
    assert step == "search_one_page"

    step = app.step_search_one_page()
    assert step == "show_api_vacancies"
    assert len(app.api_page_vacancies) == 1


@patch("job_search.api.head_hunter_api.HeadHunterAPI.get_vacancies")
def test_search_one_page_empty(mock_api: MagicMock, app: JobSearchApp, io: dict[str, Any]) -> None:
    """Пустой результат API вызывает повторный выбор."""

    mock_api.return_value = VacancyResult(
        vacancies=[],
        total_count=0,
        total_pages=0,
        page_size=10,
        current_page=0,
    )

    app.selected_api = MagicMock()
    app.selected_api.get_vacancies = mock_api

    io["input"].side_effect = [
        "python",  # keyword
        "нет",  # регион
        "нет",  # зарплата
        "2",  # режим: по одной странице
        "нет",  # не указывать per_page
        "нет",  # не указывать номер страницы
        "0",  # номер страницы
        "1",  # выбор в меню после пустого результата
    ]

    app.step_search()
    step = app.step_search_one_page()

    assert step in ("search", "main_menu")
