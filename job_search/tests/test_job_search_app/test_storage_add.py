"""
Тесты добавления вакансий в архив.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from job_search.models.job_search_app import JobSearchApp
from job_search.models.vacancy import Vacancy


@patch("job_search.storage.json_saver.JSONVacancyStorage.add_vacancy")
def test_storage_add_from_results(
    mock_add: MagicMock, app: JobSearchApp, io: dict[str, Any], vacancy: Vacancy
) -> None:
    """Добавление вакансии из результатов."""

    app.vacancies = [vacancy]
    app.current_page = 1
    app.page_size = 10

    io["input"].side_effect = ["1"]

    step = app.step_storage_add_from_results()
    mock_add.assert_called_once()
    assert step == "storage_entry"
