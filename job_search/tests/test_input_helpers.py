from typing import Any, Dict, List, Optional

import pytest

from job_search.utils.input_helpers import (
    ask_choice,
    ask_int,
    ask_yes_no,
    next_step,
    render_menu,
    render_vacancies_page,
)


@pytest.mark.parametrize(
    "user_input, expected",
    [
        (["y"], True),
        (["yes"], True),
        (["д"], True),
        (["да"], True),
        (["n"], False),
        (["no"], False),
        (["н"], False),
        (["нет"], False),
        (["отмена"], None),
    ],
)
def test_ask_yes_no_valid(io_mock: Dict[str, Any], user_input: List[str], expected: Optional[bool]) -> None:
    """Корректно обрабатывает валидные ответы."""

    io_mock["queue"].extend(user_input)
    assert ask_yes_no(io_mock, "Вопрос?") == expected


def test_ask_yes_no_invalid_then_valid(io_mock: Dict[str, Any]) -> None:
    """При неверном вводе повторяет вопрос, пока не получит корректный ответ."""

    io_mock["queue"].extend(["???", "да"])
    result = ask_yes_no(io_mock, "Вопрос?")
    assert result is True
    assert "Ошибка" in io_mock["outputs"][0]


@pytest.mark.parametrize(
    "inputs, expected",
    [
        (["10"], 10),
        (["0"], 0),
        (["отмена"], None),
    ],
)
def test_ask_int_basic(io_mock: Dict[str, Any], inputs: List[str], expected: Optional[int]) -> None:
    """Корректно обрабатывает базовые случаи."""

    io_mock["queue"].extend(inputs)
    assert ask_int(io_mock, "Введите число:") == expected


def test_ask_int_invalid_then_valid(io_mock: Dict[str, Any]) -> None:
    """Повторяет запрос при нечисловом вводе."""

    io_mock["queue"].extend(["abc", "15"])
    result = ask_int(io_mock, "Введите число:")
    assert result == 15
    assert "Ошибка" in io_mock["outputs"][0]


def test_ask_int_min_max(io_mock: Dict[str, Any]) -> None:
    """Проверяет границы min/max."""

    io_mock["queue"].extend(["1", "50"])
    result = ask_int(io_mock, "Введите число:", min_value=10, max_value=100)
    assert result == 50
    assert "не меньше" in io_mock["outputs"][0]


def test_ask_choice_valid(io_mock: Dict[str, Any]) -> None:
    """Корректно выбирает пункт меню."""

    menu = {1: ("A", "step_a"), 2: ("B", "step_b")}
    io_mock["queue"].extend(["2"])
    assert ask_choice(io_mock, menu) == 2


def test_ask_choice_invalid_then_valid(io_mock: Dict[str, Any]) -> None:
    """Повторяет запрос при неверном вводе."""

    menu = {1: ("A", "step_a"), 2: ("B", "step_b")}
    io_mock["queue"].extend(["x", "3", "1"])
    result = ask_choice(io_mock, menu)
    assert result == 1
    assert "Ошибка" in io_mock["outputs"][0]


def test_next_step_valid(io_mock: Dict[str, Any]) -> None:
    """Возвращает корректный шаг при валидном выборе."""

    menu = {1: ("A", "step_a")}
    result = next_step(io=io_mock, menu=menu, choice=1)
    assert result == "step_a"
    assert "A" in io_mock["outputs"][0]


def test_next_step_invalid(io_mock: Dict[str, Any]) -> None:
    """Возвращает default при неверном выборе."""

    menu = {1: ("A", "step_a")}
    result = next_step(io=io_mock, menu=menu, choice=99)
    assert result == "main_menu"
    assert "⚠️" in io_mock["outputs"][0]


def test_render_menu(io_mock: Dict[str, Any]) -> None:
    """Корректно выводит пункты меню."""

    menu = {1: ("A", "step_a"), 2: ("B", "step_b")}
    render_menu(io=io_mock, menu=menu)

    assert "1. A" in io_mock["outputs"]
    assert "2. B" in io_mock["outputs"]


def test_render_vacancies_page_basic(io_mock: Dict[str, Any]) -> None:
    """Корректно выводит страницу вакансий и возвращает диапазон."""

    vacancies = ["Vac1", "Vac2", "Vac3"]
    start, end = render_vacancies_page(
        io=io_mock,
        vacancies=vacancies,
        current_page=1,
        page_size=2,
        total_vacancies=3,
        global_offset=0,
    )

    assert start == 0
    assert end == 2
    assert "Vac1" in "".join(io_mock["outputs"])
    assert "Vac2" in "".join(io_mock["outputs"])


def test_render_vacancies_page_empty(io_mock: Dict[str, Any]) -> None:
    """Если вакансий нет — выводит сообщение и возвращает (0, 0)."""

    start, end = render_vacancies_page(
        io=io_mock,
        vacancies=[],
        current_page=1,
        page_size=5,
        total_vacancies=0,
        global_offset=0,
    )

    assert start == 0
    assert end == 0
    assert "Список пуст" in io_mock["outputs"][0]
