from __future__ import annotations

from typing import Any

import pytest
from pytest import LogCaptureFixture

from job_search.models.vacancy import ALLOWED_FIELDS, Vacancy


@pytest.mark.parametrize(
    "salary_from, salary_to, currency, expected",
    [
        (100000, 150000, "RUR", "от 100 000 до 150 000 RUR"),
        (100000, None, "USD", "от 100 000 USD"),
        (None, 200000, "EUR", "до 200 000 EUR"),
        (None, None, None, "Зарплата не указана"),
    ],
)
def test_salary_str(salary_from: int | None, salary_to: int | None, currency: str | None, expected: str) -> None:
    """salary_str корректно форматирует зарплату."""
    v = Vacancy(salary_from=salary_from, salary_to=salary_to, currency=currency)
    assert v.salary_str == expected


@pytest.mark.parametrize(
    "salary_from, salary_to, expected",
    [
        (100, 200, 150),
        (100, None, 100),
        (None, 200, 200),
        (None, None, 0),
    ],
)
def test_get_salary_value(salary_from: int | None, salary_to: int | None, expected: int) -> None:
    """get_salary_value возвращает корректное числовое значение."""
    v = Vacancy(salary_from=salary_from, salary_to=salary_to)
    assert v.get_salary_value() == expected


def test_comparison_lt() -> None:
    """__lt__ сравнивает по средней зарплате."""

    v1 = Vacancy(salary_from=100, salary_to=200)
    v2 = Vacancy(salary_from=200, salary_to=300)
    assert v1 < v2


def test_comparison_eq() -> None:
    """__eq__ сравнивает по get_salary_value()."""

    v1 = Vacancy(salary_from=100, salary_to=200)
    v2 = Vacancy(salary_from=150, salary_to=150)
    assert v1 == v2


def test_str(vacancy: Vacancy) -> None:
    """__str__ возвращает человекочитаемую строку."""

    assert "Python Dev" in str(vacancy)
    assert "от 100 000 до 150 000 RUR" in str(vacancy)


def test_repr(vacancy: Vacancy) -> None:
    """__repr__ возвращает техническое представление."""

    r = repr(vacancy)
    assert "Vacancy(" in r
    assert "Python Dev" in r
    assert "100 000" in r


@pytest.mark.parametrize(
    "input_data, expected",
    [
        (None, (None, None, "Валюта не указана")),
        ("not dict", (None, None, "Валюта не указана")),
        ({"from": 100, "to": 200, "currency": "USD"}, (100, 200, "USD")),
        ({"from": None, "to": 200}, (None, 200, "Валюта не указана")),
    ],
)
def test_parse_salary(input_data: dict | None, expected: tuple) -> None:
    """_parse_salary корректно обрабатывает данные."""

    assert Vacancy._parse_salary(input_data) == expected


def test_from_dict_basic(salary_dict: dict) -> None:
    """from_dict создаёт корректный объект Vacancy."""

    data = {
        "name": "Python Developer",
        "url": "http://example.com",
        "alternate_url": "http://alt.example.com",
        "snippet": {"requirement": "Опыт 3 года", "responsibility": "Разработка"},
        "salary": salary_dict,
    }

    v = Vacancy.from_dict(data)

    assert v.name_vacancy == "Python Developer"
    assert v.url_vacancy == "http://example.com"
    assert v.alternate_url == "http://alt.example.com"
    assert v.salary_from == 100000
    assert v.salary_to == 150000
    assert v.currency == "RUR"
    assert v.description is not None
    assert "Опыт 3 года" in v.description


def test_from_dict_missing_fields() -> None:
    """from_dict корректно обрабатывает отсутствие полей."""

    v = Vacancy.from_dict({"name": None, "snippet": {}, "salary": None})
    assert v.name_vacancy == "Название не указано"
    assert v.description == "Описание не указано"
    assert v.salary_from is None
    assert v.salary_to is None


def test_from_list_success() -> None:
    """from_list корректно обрабатывает список словарей."""

    data: list[dict] = [{"name": "Dev", "snippet": {}, "salary": None}]
    result = Vacancy.from_list(data)
    assert len(result) == 1
    assert isinstance(result[0], Vacancy)


def test_from_list_skip_invalid(caplog: LogCaptureFixture) -> None:
    """from_list пропускает некорректные элементы при strict=False."""

    data: list[dict[str, Any]] = [
        {"name": "Dev"},
        "not dict",  # type: ignore[list-item]
        123,  # type: ignore[list-item]
    ]

    result = Vacancy.from_list(data)

    assert len(result) == 1
    assert "Пропущен элемент" in caplog.text


def test_from_list_strict_error() -> None:
    """
    from_list выбрасывает AttributeError при strict=True,
    если from_dict ломается на некорректных данных.
    """

    bad_item = {"name": 123, "snippet": 123, "salary": {"from": "bad"}}
    data: list[dict] = [bad_item]

    with pytest.raises(AttributeError):
        Vacancy.from_list(data, strict=True)


def test_details(vacancy: Vacancy) -> None:
    """details возвращает многострочное описание."""

    text = vacancy.details()
    assert "Название:" in text
    assert "Зарплата:" in text
    assert "Ссылка:" in text


def test_to_dict_basic(vacancy: Vacancy) -> None:
    """to_dict сериализует объект корректно."""

    d = vacancy.to_dict()

    for field in ALLOWED_FIELDS:
        assert field in d

    assert d["name_vacancy"] == "Python Dev"
    assert d["salary_from"] == 100000
    assert d["salary_to"] == 150000


def test_to_dict_salary_swap() -> None:
    """Если salary_from > salary_to — значения меняются местами."""

    v = Vacancy(salary_from=200, salary_to=100)
    d = v.to_dict()
    assert d["salary_from"] == 100
    assert d["salary_to"] == 200


def test_to_dict_description_default() -> None:
    """Описание нормализуется и подставляется дефолт."""

    v = Vacancy(description=None)
    d = v.to_dict()
    assert d["description"] == "Описание не указано"
