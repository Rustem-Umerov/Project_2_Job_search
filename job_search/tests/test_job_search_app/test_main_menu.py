"""
Тесты главного меню.
"""

from typing import Any

from job_search.models.job_search_app import JobSearchApp


def test_main_menu_exit(app: JobSearchApp, io: dict[str, Any]) -> None:
    """Проверяет, что пункт 'Выход' возвращает 'exit'."""

    io["input"].side_effect = ["4"]
    assert app.step_main_menu() == "exit"
