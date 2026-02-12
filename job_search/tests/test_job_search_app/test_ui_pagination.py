"""
Тесты UI‑пагинации (next_ui_page, prev_ui_page).
"""

from typing import Any
from unittest.mock import patch

from job_search.models.job_search_app import JobSearchApp
from job_search.models.vacancy import Vacancy


def test_next_ui_page(app: JobSearchApp, io: dict[str, Any], vacancy: Vacancy) -> None:
    """Переход на следующую UI‑страницу."""

    # Подготавливаем данные
    app.api_page_vacancies = [vacancy] * 30
    app.api_total_vacancies = 30
    app.api_page_size = 10
    app.api_current_page = 0
    app.ui_page_size = 10
    app.api_mode = "one_page"

    # Первый вызов меню → next_ui_page
    # Второй вызов меню → main_menu (чтобы остановить цикл)
    with patch.object(app, "_menu_loop", side_effect=["next_ui_page", "main_menu"]):
        step = app.step_show_api_vacancies()

    # Проверяем, что переход выполнен
    assert app.ui_index == 10

    # Метод завершился корректно
    assert step == "main_menu"
