from typing import Any
from unittest.mock import MagicMock

import pytest

from job_search.api.types import VacancyResult
from job_search.models.job_search_app import JobSearchApp
from job_search.models.vacancy import Vacancy


@pytest.fixture
def io() -> dict[str, Any]:
    """Моковый ввод/вывод."""

    return {
        "input": MagicMock(),
        "output": MagicMock(),
    }


@pytest.fixture
def app(io: dict[str, Any]) -> JobSearchApp:
    """Экземпляр приложения с моковым IO."""

    return JobSearchApp(io=io)


@pytest.fixture
def vacancy() -> Vacancy:
    """Одна тестовая вакансия."""

    return Vacancy(
        name_vacancy="Python Dev",
        url_vacancy="http://example.com",
        salary_from=100,
        salary_to=200,
        currency="RUR",
        description="Test vacancy",
        alternate_url=None,
    )


@pytest.fixture
def vacancy_result(vacancy: Vacancy) -> VacancyResult:
    """Результат API с одной вакансией."""

    return VacancyResult(
        vacancies=[vacancy.to_dict()],
        total_count=1,
        total_pages=1,
        page_size=10,
        current_page=0,
    )
