"""
Тесты обновления вакансий.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from job_search.models.job_search_app import JobSearchApp
from job_search.models.vacancy import Vacancy


@patch("job_search.storage.json_saver.JSONVacancyStorage.update_vacancy")
def test_storage_update_save(mock_update: MagicMock, app: JobSearchApp, io: dict[str, Any], vacancy: Vacancy) -> None:
    """Сохранение обновлённой вакансии."""

    app.current_vacancy = vacancy
    app.vacancy_new_data = vacancy.to_dict()
    app.old_url = vacancy.url_vacancy

    mock_update.return_value = True

    step = app.step_storage_update_save()
    assert step == "storage_update"
    assert app.current_vacancy is None
