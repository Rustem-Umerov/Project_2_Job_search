from typing import Any, Dict

import pytest

from job_search.utils.vacancy_fields_validators import (
    FilterCancelled,
    norm_int,
    norm_str,
    validate_currency,
    validate_list,
    validate_name_and_description,
    validate_salary,
    validate_url,
    validate_user_input,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("10", 10),
        ("10.5", 10.5),
        ("  20  ", 20),
        ("0", 0),
        ("-5", -5),
    ],
)
def test_validate_salary_valid(io_mock_simple: Dict[str, Any], raw: str, expected: float | int) -> None:
    """Корректно преобразует строку в число."""

    assert validate_salary(io_mock_simple, raw) == expected


@pytest.mark.parametrize("bad", ["abc", "10,5", "", " "])
def test_validate_salary_invalid(io_mock_simple: Dict[str, Any], bad: str) -> None:
    """При ошибке возвращает None и пишет сообщение."""

    result = validate_salary(io_mock_simple, bad)
    assert result is None
    assert "❌ Ошибка" in io_mock_simple["outputs"][0]


@pytest.mark.parametrize(
    "raw, allowed, expected",
    [
        ("usd", {"USD", "EUR"}, "USD"),
        (" eur ", {"USD", "EUR"}, "EUR"),
    ],
)
def test_validate_currency_valid(raw: str, allowed: set[str], expected: str) -> None:
    """Корректно принимает допустимую валюту."""

    assert validate_currency(raw, allowed) == expected


@pytest.mark.parametrize("raw", ["abc", "rub", "", " "])
def test_validate_currency_invalid(raw: str) -> None:
    """Недопустимая валюта → None."""

    assert validate_currency(raw, {"USD", "EUR"}) is None


def test_validate_name_and_description_ok(io_mock_simple: Dict[str, Any]) -> None:
    """Корректный ввод возвращает ('ok', значение)."""

    status, value = validate_name_and_description(io=io_mock_simple, raw_input="Python Dev", step="name")
    assert status == "ok"
    assert value == "Python Dev"


def test_validate_name_and_description_skip(io_mock_simple: Dict[str, Any]) -> None:
    """Пустая строка → skip."""

    status, value = validate_name_and_description(io=io_mock_simple, raw_input="", step="name")
    assert status == "skip"
    assert value is None
    assert "не указано" in io_mock_simple["outputs"][0]


def test_validate_name_and_description_spaces(io_mock_simple: Dict[str, Any]) -> None:
    """Строка из пробелов → error."""

    status, value = validate_name_and_description(io=io_mock_simple, raw_input="   ", step="name")
    assert status == "error"
    assert value is None
    assert "не может состоять только из пробелов" in io_mock_simple["outputs"][0]


def test_validate_name_and_description_back(io_mock_simple: Dict[str, Any]) -> None:
    """'назад' → back."""

    status, value = validate_name_and_description(io=io_mock_simple, raw_input="назад", step="name")
    assert status == "back"
    assert value is None
    assert "возвращаетесь" in io_mock_simple["outputs"][0]


def test_validate_name_and_description_cancel(io_mock_simple: Dict[str, Any]) -> None:
    """'отмена' → исключение FilterCancelled."""

    with pytest.raises(FilterCancelled):
        validate_name_and_description(io=io_mock_simple, raw_input="отмена", step="name")
    assert "отменена" in io_mock_simple["outputs"][0]


def test_validate_user_input_ok(io_mock_simple: Dict[str, Any]) -> None:
    """Корректный ввод → ok."""

    status, value = validate_user_input(io=io_mock_simple, user_input="Python", step="name")
    assert status == "ok"
    assert value == "Python"


def test_validate_user_input_skip(io_mock_simple: Dict[str, Any]) -> None:
    """Пустая строка → skip."""

    status, value = validate_user_input(io=io_mock_simple, user_input="", step="name")
    assert status == "skip"
    assert value is None


def test_validate_user_input_back_first_step(io_mock_simple: Dict[str, Any]) -> None:
    """На первом шаге 'назад' → back с предупреждением."""

    status, value = validate_user_input(io=io_mock_simple, user_input="назад", step="name", first_step=True)
    assert status == "back"
    assert value is None
    assert "первом шаге" in io_mock_simple["outputs"][0]


def test_validate_user_input_back(io_mock_simple: Dict[str, Any]) -> None:
    """На втором шаге 'назад' → back."""

    status, value = validate_user_input(io=io_mock_simple, user_input="назад", step="name", first_step=False)
    assert status == "back"
    assert value is None


def test_validate_user_input_cancel(io_mock_simple: Dict[str, Any]) -> None:
    """'отмена' → исключение."""

    with pytest.raises(FilterCancelled):
        validate_user_input(io=io_mock_simple, user_input="отмена", step="name")


def test_validate_url_valid(io_mock_simple: Dict[str, Any]) -> None:
    """Корректные URL → список."""

    urls = validate_url(io=io_mock_simple, user_input="http://a.com, https://b.com", step="urls")
    assert urls == ["http://a.com", "https://b.com"]


def test_validate_url_empty(io_mock_simple: Dict[str, Any]) -> None:
    """Пустой ввод → None."""

    assert validate_url(io=io_mock_simple, user_input=" ,  ", step="urls") is None
    assert "не содержит" in io_mock_simple["outputs"][0]


def test_validate_url_invalid(io_mock_simple: Dict[str, Any]) -> None:
    """URL без http → None."""

    assert validate_url(io=io_mock_simple, user_input="a.com, http://ok", step="urls") is None
    assert "должны начинаться" in io_mock_simple["outputs"][0]


def test_validate_list_valid() -> None:
    """Корректный список словарей → True."""

    assert validate_list([{"a": 1}, {"b": 2}]) is True


@pytest.mark.parametrize("bad", [None, 123, "abc"])
def test_validate_list_not_list(bad: Any) -> None:
    """Не список → False."""

    assert validate_list(bad) is False


def test_validate_list_empty() -> None:
    """Пустой список → False."""

    assert validate_list([]) is False


def test_validate_list_wrong_elements() -> None:
    """Элементы не словари → False."""

    assert validate_list([1, 2, 3]) is False


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("10", 10),
        (10, 10),
        (" 20 ", 20),
    ],
)
def test_norm_int_valid(raw: str | int, expected: int) -> None:
    """Корректно преобразует строку или число в int."""

    assert norm_int(raw) == expected


@pytest.mark.parametrize("bad", ["abc", {}, [], None])
def test_norm_int_invalid(bad: Any) -> None:
    """Некорректные значения → None."""

    assert norm_int(bad) is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("hello", "hello"),
        ("  hi  ", "hi"),
    ],
)
def test_norm_str_valid(raw: str, expected: str) -> None:
    """Обрезает пробелы и возвращает строку."""

    assert norm_str(raw) == expected


def test_norm_str_lower() -> None:
    """lower=True приводит строку к нижнему регистру."""

    assert norm_str(" HeLLo ", lower=True) == "hello"


@pytest.mark.parametrize("bad", ["   ", "", None, 123])
def test_norm_str_invalid(bad: Any) -> None:
    """Пустые строки и неверные типы → None."""

    assert norm_str(bad) is None
