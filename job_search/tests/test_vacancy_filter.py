from typing import Optional
from unittest.mock import patch

import pytest

from job_search.filters.vacancy_filter import (
    VacancyFilter,
    check_value,
    normalize_filter,
)
from job_search.models.vacancy import Vacancy


class FakeVacancy(Vacancy):
    """Простой объект вакансии для тестов."""

    def __init__(
        self,
        name_vacancy: str = "",
        url_vacancy: str = "",
        alternate_url: str = "",
        description: str = "",
        currency: str = "",
        salary_from: Optional[int] = None,
        salary_to: Optional[int] = None,
    ) -> None:
        super().__init__(
            name_vacancy=name_vacancy,
            url_vacancy=url_vacancy,
            alternate_url=alternate_url,
            salary_from=salary_from,
            salary_to=salary_to,
            currency=currency,
            description=description,
        )


@patch("job_search.filters.vacancy_filter.ALLOWED_FIELDS", {"name_vacancy", "currency", "salary_from", "salary_to"})
def test_match_simple_eq() -> None:
    """Проверяет успешное совпадение вакансии по простому полю eq."""

    vacancy = FakeVacancy(name_vacancy="Python Developer")
    vf = VacancyFilter({"name_vacancy": "Python Developer"})

    assert vf.match(vacancy) is True


@patch("job_search.filters.vacancy_filter.ALLOWED_FIELDS", {"name_vacancy"})
def test_match_simple_eq_fail() -> None:
    """Проверяет, что match() возвращает False при несовпадении поля."""

    vacancy = FakeVacancy(name_vacancy="Java Developer")
    vf = VacancyFilter({"name_vacancy": "Python Developer"})

    assert vf.match(vacancy) is False


@patch("job_search.filters.vacancy_filter.ALLOWED_FIELDS", {"name_vacancy"})
def test_match_unknown_field_skipped() -> None:
    """Проверяет, что неизвестное поле пропускается и не ломает фильтрацию."""

    vacancy = FakeVacancy(name_vacancy="Python Developer")
    vf = VacancyFilter({"unknown_field": "X", "name_vacancy": "Python Developer"})

    assert vf.match(vacancy) is True


@patch("job_search.filters.vacancy_filter.ALLOWED_FIELDS", {"salary_from", "salary_to"})
def test_match_salary_gte() -> None:
    """Проверяет фильтрацию по зарплате с оператором gte."""

    vacancy = FakeVacancy(salary_from=200)

    # Плоский словарь — как после normalize_filter
    vf = VacancyFilter({"salary_from": {"gte": 150}})

    assert vf.match(vacancy) is True


@patch("job_search.filters.vacancy_filter.ALLOWED_FIELDS", {"description"})
def test_match_contains() -> None:
    """Проверяет оператор contains для текстовых полей."""

    vacancy = FakeVacancy(description="Senior Python Developer")
    vf = VacancyFilter({"description": {"contains": "python"}})

    assert vf.match(vacancy) is True


@patch("job_search.filters.vacancy_filter.ALLOWED_FIELDS", {"currency"})
def test_match_in_operator() -> None:
    """Проверяет оператор in для списков."""

    vacancy = FakeVacancy(currency="USD")
    vf = VacancyFilter({"currency": {"in": ["EUR", "USD"]}})

    assert vf.match(vacancy) is True


def test_apply_operator_eq() -> None:
    """Проверяет оператор eq."""

    assert VacancyFilter._apply_operator("eq", 10, 10) is True
    assert VacancyFilter._apply_operator("eq", 10, 5) is False


def test_apply_operator_gte() -> None:
    """Проверяет оператор gte."""

    assert VacancyFilter._apply_operator("gte", 10, 5) is True
    assert VacancyFilter._apply_operator("gte", 3, 5) is False


def test_apply_operator_lte() -> None:
    """Проверяет оператор lte."""

    assert VacancyFilter._apply_operator("lte", 5, 10) is True
    assert VacancyFilter._apply_operator("lte", 20, 10) is False


def test_apply_operator_contains() -> None:
    """Проверяет оператор contains."""

    assert VacancyFilter._apply_operator("contains", "Hello World", "world") is True
    assert VacancyFilter._apply_operator("contains", "Hello", "bye") is False


def test_apply_operator_in() -> None:
    """Проверяет оператор in."""

    assert VacancyFilter._apply_operator("in", "USD", ["USD", "EUR"]) is True
    assert VacancyFilter._apply_operator("in", "GBP", ["USD", "EUR"]) is False


def test_apply_operator_unknown() -> None:
    """Проверяет, что неизвестный оператор возвращает False."""

    assert VacancyFilter._apply_operator("xxx", 1, 1) is False


@patch("job_search.filters.vacancy_filter.ALLOWED_FIELDS", {"name_vacancy", "currency"})
def test_normalize_filter_simple() -> None:
    """Проверяет нормализацию простых полей."""

    raw = {"name_vacancy": "Python", "currency": "USD"}
    result = normalize_filter(raw)

    assert result == raw


@patch("job_search.filters.vacancy_filter.ALLOWED_FIELDS", {"salary_from", "salary_to"})
def test_normalize_filter_salary_block() -> None:
    """Проверяет разбор salary-блока в salary_from и salary_to."""

    raw = {"salary": {"salary_from": "100", "salary_to": "200"}}
    result = normalize_filter(raw)

    assert result == {"salary_from": 100.0, "salary_to": 200.0}


def test_normalize_filter_wrong_type() -> None:
    """Проверяет, что normalize_filter выбрасывает TypeError при неверном типе."""

    with pytest.raises(TypeError):
        normalize_filter("not a dict")  # type: ignore


def test_check_value_none() -> None:
    """Проверяет, что None возвращает None."""

    assert check_value(None, "salary_from") is None


def test_check_value_numeric() -> None:
    """Проверяет, что числовые значения конвертируются в float."""

    assert check_value(150, "salary_from") == 150.0


def test_check_value_string_numeric() -> None:
    """Проверяет конвертацию строки в число."""

    assert check_value("200", "salary_to") == 200.0


def test_check_value_string_invalid() -> None:
    """Проверяет, что некорректная строка возвращает None."""

    assert check_value("abc", "salary_from") is None


def test_check_value_dict_valid_operator() -> None:
    """Проверяет обработку словаря с допустимым оператором."""

    assert check_value({"gte": "300"}, "salary_from") == 300.0


def test_check_value_dict_invalid_operator() -> None:
    """Проверяет, что словарь с недопустимым оператором возвращает None."""

    assert check_value({"xxx": "100"}, "salary_from") is None


def test_check_value_unsupported_type() -> None:
    """Проверяет, что неподдерживаемый тип возвращает None."""

    assert check_value([1, 2, 3], "salary_from") is None
