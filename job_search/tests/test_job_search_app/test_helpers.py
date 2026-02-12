"""
Тесты вспомогательных методов.
"""

from job_search.models.job_search_app import JobSearchApp
from job_search.models.vacancy import Vacancy


def test_check_current_vacancy_ok(app: JobSearchApp, vacancy: Vacancy) -> None:
    """Проверка выбранной вакансии."""

    app.current_vacancy = vacancy
    status, ok = app._check_current_vacancy()
    assert status == "ok"
    assert ok is True
