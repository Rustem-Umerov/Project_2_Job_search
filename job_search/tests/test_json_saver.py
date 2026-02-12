from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pytest import LogCaptureFixture

from job_search.models.vacancy import Vacancy
from job_search.storage.json_saver import JSONVacancyStorage


@pytest.mark.parametrize(
    "url, expected",
    [
        ("HTTP://EXAMPLE.COM", "http://example.com"),
        ("   https://test.ru  ", "https://test.ru"),
        ("", None),
        ("   ", None),
    ],
)
def test_normalize_url_or_fail(url: str, expected: str | None) -> None:
    """Проверка нормализации URL."""

    result = JSONVacancyStorage._normalize_url_or_fail(url)
    assert result == expected


def test_find_vacancy_index_found() -> None:
    """Индекс найден по url_vacancy."""

    data = [
        {"url_vacancy": "http://a.com", "alternate_url": "http://b.com"},
        {"url_vacancy": "http://x.com", "alternate_url": "http://y.com"},
    ]
    idx = JSONVacancyStorage.find_vacancy_index("http://x.com", data)
    assert idx == 1


def test_find_vacancy_index_alt_found() -> None:
    """Индекс найден по alternate_url."""

    data = [{"url_vacancy": "http://a.com", "alternate_url": "http://b.com"}]
    idx = JSONVacancyStorage.find_vacancy_index("http://b.com", data)
    assert idx == 0


def test_find_vacancy_index_not_found(caplog: LogCaptureFixture) -> None:
    """URL не найден."""

    data = [{"url_vacancy": "http://a.com", "alternate_url": "http://b.com"}]
    idx = JSONVacancyStorage.find_vacancy_index("http://zzz.com", data)
    assert idx is None
    assert "не найдена" in caplog.text


def test_get_vacancies_valid(storage: JSONVacancyStorage) -> None:
    """Корректная загрузка вакансий."""

    storage._filepath.write_text(json.dumps([{"name_vacancy": "Dev"}]), encoding="utf-8")
    result = storage.get_vacancies()
    assert len(result) == 1
    assert isinstance(result[0], Vacancy)


def test_get_vacancies_invalid_json(storage: JSONVacancyStorage) -> None:
    """Невалидный JSON → пустой список."""

    storage._filepath.write_text("{broken json", encoding="utf-8")
    assert storage.get_vacancies() == []


def test_apply_filter_no_filter(storage: JSONVacancyStorage, vacancy: Vacancy) -> None:
    """Без фильтра возвращаются все вакансии."""

    storage._save_all([vacancy.to_dict()])
    result = storage.apply_filter(None)
    assert len(result) == 1


def test_apply_filter_invalid_filter(storage: JSONVacancyStorage) -> None:
    """Некорректный фильтр → пустой список."""

    result = storage.apply_filter("not dict")  # type: ignore[arg-type]
    assert result == []


def test_apply_filter_valid(storage: JSONVacancyStorage, vacancy: Vacancy) -> None:
    """Фильтр применяется корректно."""

    storage._save_all([vacancy.to_dict()])

    with patch("job_search.filters.vacancy_filter.normalize_filter", return_value={"currency": "RUR"}):
        mock_filter = MagicMock()
        mock_filter.match.return_value = True

        with patch("job_search.filters.vacancy_filter.VacancyFilter", return_value=mock_filter):
            result = storage.apply_filter({"currency": "RUR"})
            assert len(result) == 1


def test_add_vacancy_new(storage: JSONVacancyStorage, vacancy: Vacancy) -> None:
    """Добавление новой вакансии."""

    storage._save_all([])
    assert storage.add_vacancy(vacancy) is False  # safe_load_all() → []


def test_add_vacancy_invalid_type(storage: JSONVacancyStorage) -> None:
    """Ошибка, если передан не Vacancy."""

    with pytest.raises(TypeError):
        storage.add_vacancy("not vacancy")  # type: ignore[arg-type]


def test_add_vacancy_missing_url(storage: JSONVacancyStorage, vacancy: Vacancy) -> None:
    """Ошибка, если нет URL."""

    vacancy.url_vacancy = ""
    with pytest.raises(ValueError):
        storage.add_vacancy(vacancy)


def test_update_vacancy_success(storage: JSONVacancyStorage, vacancy: Vacancy) -> None:
    """Успешное обновление вакансии."""

    storage._save_all([vacancy.to_dict()])

    new_data = {"name_vacancy": "Updated"}
    url_vac = vacancy.url_vacancy
    assert isinstance(url_vac, str)
    assert storage.update_vacancy(url_vac, new_data) is True


def test_update_vacancy_not_found(storage: JSONVacancyStorage) -> None:
    """Вакансия не найдена."""

    storage._save_all([])
    assert storage.update_vacancy("http://x.com", {"name_vacancy": "A"}) is False


def test_remove_vacancy_success(storage: JSONVacancyStorage, vacancy: Vacancy) -> None:
    """Удаление вакансии."""

    storage._save_all([vacancy.to_dict()])
    url_vac = vacancy.url_vacancy
    assert isinstance(url_vac, str)
    assert storage.remove_vacancy(url_vac) is True


def test_remove_vacancy_not_found(storage: JSONVacancyStorage) -> None:
    """Удаление несуществующей вакансии."""

    storage._save_all([])
    assert storage.remove_vacancy("http://x.com") is False


def test_get_by_url_found(storage: JSONVacancyStorage, vacancy: Vacancy) -> None:
    """Возвращает Vacancy, если URL найден в хранилище."""

    storage._save_all([vacancy.to_dict()])
    url_vac = vacancy.url_vacancy
    assert isinstance(url_vac, str)
    result = storage.get_by_url(url_vac)
    assert isinstance(result, Vacancy)


def test_get_by_url_not_found(storage: JSONVacancyStorage) -> None:
    """Возвращает None, если URL отсутствует в хранилище."""

    storage._save_all([])
    assert storage.get_by_url("http://x.com") is None


def test_count(storage: JSONVacancyStorage, vacancy: Vacancy) -> None:
    """Возвращает корректное количество вакансий в хранилище."""

    storage._save_all([vacancy.to_dict()])
    assert storage.count() == 1


def test_is_empty(storage: JSONVacancyStorage) -> None:
    """Возвращает True, если хранилище пустое."""

    storage._save_all([])
    assert storage.is_empty() is True
