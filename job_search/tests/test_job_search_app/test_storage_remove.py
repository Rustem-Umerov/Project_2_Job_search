"""
Тесты удаления вакансий.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from job_search.models.job_search_app import JobSearchApp
from job_search.models.vacancy import Vacancy


@patch("job_search.storage.json_saver.JSONVacancyStorage.safe_load_all")
@patch("job_search.storage.json_saver.JSONVacancyStorage.find_vacancy_index")
@patch("job_search.storage.json_saver.JSONVacancyStorage.save")
def test_storage_remove_confirm(
    mock_save: MagicMock,
    mock_find: MagicMock,
    mock_load: MagicMock,
    app: JobSearchApp,
    io: dict[str, Any],
    vacancy: Vacancy,
) -> None:
    """Удаление вакансии."""

    app.current_vacancy = vacancy
    app.storage_vacancies = [vacancy.to_dict()]
    app.vacancy_idx = 0

    mock_save.return_value = True

    step = app.step_storage_remove_confirm()
    assert step in ("storage_select_vacancy", "storage_menu", "main_menu")
