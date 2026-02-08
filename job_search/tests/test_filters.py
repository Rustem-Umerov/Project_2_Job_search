from typing import Callable, List

import pytest

from job_search.models.vacancy import Vacancy
from job_search.utils.filters import (
    get_salary,
    get_top_n_vacancies,
    sort_by_salary,
)


@pytest.mark.parametrize(
    "salary_from, salary_to, expected",
    [
        (100, 200, 150),
        (100, None, 100),
        (None, 200, 200),
        (None, None, 0),
    ],
)
def test_get_salary_valid(
    vacancy_factory: Callable[..., Vacancy],
    salary_from: int | None,
    salary_to: int | None,
    expected: int,
) -> None:
    """Корректно вычисляет зарплату при валидных данных."""

    vacancy = vacancy_factory(salary_from=salary_from, salary_to=salary_to)
    assert get_salary(vacancy) == expected


@pytest.mark.parametrize(
    "salary_from, salary_to",
    [
        ("abc", 100),
        (100, "xyz"),
        ("bad", "data"),
    ],
)
def test_get_salary_invalid_types(
    vacancy_factory: Callable[..., Vacancy],
    salary_from: object,
    salary_to: object,
) -> None:
    """Выбрасывает ValueError при некорректных типах зарплаты."""

    vacancy = vacancy_factory(salary_from=salary_from, salary_to=salary_to)
    with pytest.raises(ValueError):
        get_salary(vacancy)


def test_sort_by_salary_basic(vacancy_factory: Callable[..., Vacancy]) -> None:
    """Сортирует вакансии по зарплате по убыванию."""

    v1 = vacancy_factory(salary_from=50)
    v2 = vacancy_factory(salary_from=100)
    v3 = vacancy_factory(salary_from=10)

    result: List[Vacancy] = sort_by_salary([v1, v2, v3])
    assert result == [v2, v1, v3]


def test_sort_by_salary_reverse_false(vacancy_factory: Callable[..., Vacancy]) -> None:
    """Сортирует вакансии по возрастанию при reverse=False."""

    v1 = vacancy_factory(salary_from=50)
    v2 = vacancy_factory(salary_from=100)

    result: List[Vacancy] = sort_by_salary([v1, v2], reverse=False)
    assert result == [v1, v2]


def test_sort_by_salary_filters_non_vacancy(vacancy_factory: Callable[..., Vacancy]) -> None:
    """Игнорирует объекты, не являющиеся Vacancy."""

    v1 = vacancy_factory(salary_from=100)
    v2 = "not a vacancy"

    result: List[Vacancy] = sort_by_salary([v1, v2])  # type: ignore[list-item]
    assert result == [v1]


def test_sort_by_salary_raises_on_invalid_salary(vacancy_factory: Callable[..., Vacancy]) -> None:
    """Пробрасывает ValueError, если get_salary падает."""

    v1 = vacancy_factory(salary_from="bad")  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        sort_by_salary([v1])


def test_get_top_n_basic(vacancy_factory: Callable[..., Vacancy]) -> None:
    """Возвращает топ-N вакансий по убыванию зарплаты."""

    v1 = vacancy_factory(salary_from=50)
    v2 = vacancy_factory(salary_from=200)
    v3 = vacancy_factory(salary_from=100)

    result: List[Vacancy] = get_top_n_vacancies([v1, v2, v3], n=2)
    assert result == [v2, v3]


def test_get_top_n_empty_list() -> None:
    """Если список пуст — возвращается пустой список."""

    assert get_top_n_vacancies([], n=3) == []


@pytest.mark.parametrize("n", [0, -1])
def test_get_top_n_invalid_n(
    vacancy_factory: Callable[..., Vacancy],
    n: int,
) -> None:
    """Если n <= 0 — возвращается пустой список."""

    v = vacancy_factory(salary_from=100)
    assert get_top_n_vacancies([v], n=n) == []


def test_get_top_n_n_greater_than_list(vacancy_factory: Callable[..., Vacancy]) -> None:
    """Если n больше количества вакансий — возвращаются все."""

    v1 = vacancy_factory(salary_from=100)
    v2 = vacancy_factory(salary_from=200)

    result: List[Vacancy] = get_top_n_vacancies([v1, v2], n=10)
    assert result == [v2, v1]


def test_get_top_n_raises_on_invalid_salary(vacancy_factory: Callable[..., Vacancy]) -> None:
    """Пробрасывает ValueError, если sort_by_salary падает."""

    v = vacancy_factory(salary_from="bad")  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        get_top_n_vacancies([v], n=1)
