from typing import Any

from job_search.filters.preview_renderer import FilterPreviewRenderer


def test_salary_preview_full_range(mock_io: dict[str, Any]) -> None:
    """Проверяет формирование строки зарплаты при указанных нижней и верхней границах и валюты."""

    answers = {"salary_from": 100, "salary_to": 200, "currency": "USD"}
    r = FilterPreviewRenderer(answers, mock_io)

    result = r._salary_preview()
    assert result == "💰 Зарплата: от 100 до 200 в валюте USD"


def test_salary_preview_only_from(mock_io: dict[str, Any]) -> None:
    """Проверяет формирование строки зарплаты, когда задан только salary_from."""

    answers = {"salary_from": 150, "salary_to": None, "currency": "EUR"}
    r = FilterPreviewRenderer(answers, mock_io)

    result = r._salary_preview()
    assert result == "💰 Зарплата: от 150 в валюте EUR"


def test_salary_preview_only_to(mock_io: dict[str, Any]) -> None:
    """Проверяет формирование строки зарплаты, когда задан только salary_to."""

    answers = {"salary_from": None, "salary_to": 500, "currency": "RUB"}
    r = FilterPreviewRenderer(answers, mock_io)

    result = r._salary_preview()
    assert result == "💰 Зарплата: до 500 в валюте RUB"


def test_salary_preview_no_values(mock_io: dict[str, Any]) -> None:
    """Проверяет, что при отсутствии значений зарплаты возвращается пустая строка."""

    answers = {"salary_from": None, "salary_to": None, "currency": "USD"}
    r = FilterPreviewRenderer(answers, mock_io)

    result = r._salary_preview()
    assert result == ""


def test_contains_preview_both(mock_io: dict[str, Any]) -> None:
    """Проверяет формирование строки, когда заданы ключевые слова и в названии, и в описании."""

    answers = {"contains_name": "Python", "contains_description": "backend"}
    r = FilterPreviewRenderer(answers, mock_io)

    result = r._contains_preview()
    assert result == "🔍 Название содержит: Python\n📝 Описание содержит: backend"


def test_contains_preview_only_name(mock_io: dict[str, Any]) -> None:
    """Проверяет формирование строки, когда задано только ключевое слово в названии."""

    answers = {"contains_name": "Django", "contains_description": None}
    r = FilterPreviewRenderer(answers, mock_io)

    result = r._contains_preview()
    assert result == "🔍 Название содержит: Django"


def test_contains_preview_only_description(mock_io: dict[str, Any]) -> None:
    """Проверяет формирование строки, когда задано только ключевое слово в описании."""

    answers = {"contains_name": None, "contains_description": "asyncio"}
    r = FilterPreviewRenderer(answers, mock_io)

    result = r._contains_preview()
    assert result == "📝 Описание содержит: asyncio"


def test_contains_preview_empty(mock_io: dict[str, Any]) -> None:
    """Проверяет, что при отсутствии ключевых слов возвращается пустая строка."""

    answers = {"contains_name": None, "contains_description": None}
    r = FilterPreviewRenderer(answers, mock_io)

    result = r._contains_preview()
    assert result == ""


def test_url_preview_single(mock_io: dict[str, Any]) -> None:
    """Проверяет вывод одиночной ссылки."""

    answers = {"url": "https://example.com"}
    r = FilterPreviewRenderer(answers, mock_io)

    r._url_contains_preview()
    assert mock_io["outputs"][-1] == "🔗 Ссылка: https://example.com"


def test_url_preview_list(mock_io: dict[str, Any]) -> None:
    """Проверяет вывод списка ссылок."""

    answers = {"url": ["a.com", "b.com"]}
    r = FilterPreviewRenderer(answers, mock_io)

    r._url_contains_preview()
    assert mock_io["outputs"][-3:] == [
        "🔗 Ссылки:",
        "- a.com",
        "- b.com",
    ]


def test_url_preview_none(mock_io: dict[str, Any]) -> None:
    """Проверяет, что при отсутствии ссылок вывод не производится."""

    answers = {"url": None}
    r = FilterPreviewRenderer(answers, mock_io)

    r._url_contains_preview()
    assert mock_io["outputs"] == []


def test_alternate_url_single(mock_io: dict[str, Any]) -> None:
    """Проверяет вывод одиночной альтернативной ссылки."""

    answers = {"alternate_url": "alt.com"}
    r = FilterPreviewRenderer(answers, mock_io)

    r._alternate_url_preview()
    assert mock_io["outputs"][-1] == "🔁 Альтернативная ссылка: alt.com"


def test_alternate_url_list(mock_io: dict[str, Any]) -> None:
    """Проверяет вывод списка альтернативных ссылок."""

    answers = {"alternate_url": ["x.com", "y.com"]}
    r = FilterPreviewRenderer(answers, mock_io)

    r._alternate_url_preview()
    assert mock_io["outputs"][-3:] == [
        "🔁 Альтернативные ссылки:",
        "- x.com",
        "- y.com",
    ]


def test_alternate_url_none(mock_io: dict[str, Any]) -> None:
    """Проверяет, что при отсутствии альтернативных ссылок вывод не производится."""

    answers = {"alternate_url": None}
    r = FilterPreviewRenderer(answers, mock_io)

    r._alternate_url_preview()
    assert mock_io["outputs"] == []


def test_render_empty_filter(mock_io: dict[str, Any]) -> None:
    """Проверяет поведение render(), когда фильтр полностью пуст."""

    answers = {"salary_from": None, "salary_to": None, "currency": None}
    r = FilterPreviewRenderer(answers, mock_io)

    r.render()

    assert mock_io["outputs"][-1] == "Фильтр пока не задан. Вы можете вернуться и указать параметры."


def test_render_full(mock_io: dict[str, Any]) -> None:
    """Проверяет полный рендер фильтра со всеми заполненными параметрами."""

    answers = {
        "salary_from": 100,
        "salary_to": 200,
        "currency": "USD",
        "contains_name": "Python",
        "contains_description": "backend",
        "url": ["a.com"],
        "alternate_url": "alt.com",
    }

    r = FilterPreviewRenderer(answers, mock_io)
    r.render()

    out = mock_io["outputs"]

    assert "📋 Предварительный обзор фильтра:" in out
    assert "💰 Зарплата: от 100 до 200 в валюте USD" in out
    assert any("🔍 Название содержит: Python" in line for line in out)
    assert any("📝 Описание содержит: backend" in line for line in out)
    assert "🔗 Ссылки:" in out
    assert "- a.com" in out
    assert "🔁 Альтернативная ссылка: alt.com" in out
