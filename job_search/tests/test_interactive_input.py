from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from job_search.filters.interactive_input import InteractiveFilterInput
from job_search.utils.exceptions import FilterCancelled


@pytest.fixture
def mock_io() -> dict[str, Any]:
    """Создаёт мокк ввода/вывода для тестов."""

    outputs = []

    def fake_print(msg: str = "") -> None:
        outputs.append(msg)

    inputs: list[Any] = []

    def fake_input(prompt: str = "") -> Any:
        outputs.append(prompt)
        if not inputs:
            raise RuntimeError("Нет подготовленных входных данных для fake_input")
        return inputs.pop(0)

    return {"input": fake_input, "output": fake_print, "inputs": inputs, "outputs": outputs}


@pytest.fixture
def mock_formatter() -> MagicMock:
    """Мокк форматтера."""

    fmt = MagicMock()
    fmt.build_from.return_value = {"ok": True}
    return fmt


@pytest.fixture
def mock_validators() -> Generator[dict[str, MagicMock], None, None]:
    with (
        patch("job_search.filters.interactive_input.validate_user_input") as v_user,
        patch("job_search.filters.interactive_input.validate_salary") as v_salary,
        patch("job_search.filters.interactive_input.validate_currency") as v_curr,
        patch("job_search.filters.interactive_input.validate_name_and_description") as v_name,
        patch("job_search.filters.interactive_input.validate_url") as v_url,
    ):

        yield {
            "validate_user_input": v_user,
            "validate_salary": v_salary,
            "validate_currency": v_curr,
            "validate_name_and_description": v_name,
            "validate_url": v_url,
        }


@pytest.fixture
def interactive(mock_formatter: MagicMock, mock_io: dict[str, Any]) -> InteractiveFilterInput:
    return InteractiveFilterInput(formatter=mock_formatter, allowed_currencies={"USD", "EUR", "RUB"}, io=mock_io)


def test_start_outputs_expected_text(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода start"""

    interactive.start()
    out = "\n".join(mock_io["outputs"])
    assert "🔍 Сейчас мы соберём фильтр" in out
    assert "Чтобы вернуться на шаг назад" in out
    assert "📋 Доступные поля фильтра" in out
    assert "💡 Примеры ввода" in out
    assert "Начнём с минимальной зарплаты" in out


def test_ask_salary_from_ok(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary_from"""

    mock_io["inputs"].extend(["100000"])
    mock_validators["validate_user_input"].return_value = ("ok", "100000")
    mock_validators["validate_salary"].return_value = 100000

    interactive.ask_salary_from()

    assert interactive._answers["salary_from"] == 100000


def test_ask_salary_from_skip(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary_from"""

    mock_io["inputs"].extend([""])
    mock_validators["validate_user_input"].return_value = ("skip", None)

    result = interactive.ask_salary_from()

    assert result is None
    assert "salary_from" not in interactive._answers


def test_ask_salary_from_back_ignored_on_first_step(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary_from"""

    mock_io["inputs"].extend(["назад", "100"])
    mock_validators["validate_user_input"].side_effect = [
        ("back", None),
        ("ok", "100"),
    ]
    mock_validators["validate_salary"].return_value = 100

    interactive.ask_salary_from()

    assert interactive._answers["salary_from"] == 100


def test_ask_salary_from_invalid_number(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary_from"""

    mock_io["inputs"].extend(["abc", "200"])
    mock_validators["validate_user_input"].side_effect = [
        ("ok", "abc"),
        ("ok", "200"),
    ]
    mock_validators["validate_salary"].side_effect = [None, 200]

    interactive.ask_salary_from()

    assert interactive._answers["salary_from"] == 200


def test_ask_salary_to_ok(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary_to"""

    interactive._answers["salary_from"] = 100
    mock_io["inputs"].extend(["200"])
    mock_validators["validate_user_input"].return_value = ("ok", "200")
    mock_validators["validate_salary"].return_value = 200

    result = interactive.ask_salary_to()

    assert result is None
    assert interactive._answers["salary_to"] == 200


def test_ask_salary_to_skip(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary_to"""

    mock_io["inputs"].extend([""])
    mock_validators["validate_user_input"].return_value = ("skip", None)

    result = interactive.ask_salary_to()

    assert result is None
    assert "salary_to" not in interactive._answers


def test_ask_salary_to_back(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary_to"""

    mock_io["inputs"].extend(["назад"])
    mock_validators["validate_user_input"].return_value = ("back", None)

    result = interactive.ask_salary_to()

    assert result == "back"


def test_ask_salary_to_less_than_from(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary_to"""

    interactive._answers["salary_from"] = 300
    mock_io["inputs"].extend(["200", "400"])
    mock_validators["validate_user_input"].side_effect = [
        ("ok", "200"),
        ("ok", "400"),
    ]
    mock_validators["validate_salary"].side_effect = [200, 400]

    interactive.ask_salary_to()

    assert interactive._answers["salary_to"] == 400


def test_ask_currency_ok(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_currency"""

    mock_io["inputs"].extend(["usd"])
    mock_validators["validate_user_input"].return_value = ("ok", "usd")
    mock_validators["validate_currency"].return_value = "USD"

    result = interactive.ask_currency()

    assert result is None
    assert interactive._answers["currency"] == "USD"


def test_ask_currency_skip(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_currency"""

    mock_io["inputs"].extend([""])
    mock_validators["validate_user_input"].return_value = ("skip", None)

    result = interactive.ask_currency()

    assert result is None
    assert "currency" not in interactive._answers


def test_ask_currency_back(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_currency"""

    mock_io["inputs"].extend(["назад"])
    mock_validators["validate_user_input"].return_value = ("back", None)

    result = interactive.ask_currency()

    assert result == "back"


def test_ask_currency_invalid(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_currency"""

    mock_io["inputs"].extend(["XXX", "usd"])
    mock_validators["validate_user_input"].side_effect = [
        ("ok", "XXX"),
        ("ok", "usd"),
    ]
    mock_validators["validate_currency"].side_effect = [None, "USD"]

    interactive.ask_currency()

    assert interactive._answers["currency"] == "USD"


def test_ask_description_ok(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_description"""

    mock_io["inputs"].extend(["Python удалёнка"])
    mock_validators["validate_name_and_description"].return_value = ("ok", "Python удалёнка")

    result = interactive.ask_description()

    assert result is None
    assert interactive._answers["contains_description"] == "Python удалёнка"


def test_ask_description_skip(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_description"""

    mock_io["inputs"].extend([""])
    mock_validators["validate_name_and_description"].return_value = ("skip", None)

    result = interactive.ask_description()

    assert result is None
    assert "contains_description" not in interactive._answers


def test_ask_description_back(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_description"""

    mock_io["inputs"].extend(["назад"])
    mock_validators["validate_name_and_description"].return_value = ("back", None)

    result = interactive.ask_description()

    assert result == "back"


def test_ask_description_error_retry(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_description"""

    mock_io["inputs"].extend(["!!!", "Python"])
    mock_validators["validate_name_and_description"].side_effect = [
        ("error", None),
        ("ok", "Python"),
    ]

    interactive.ask_description()

    assert interactive._answers["contains_description"] == "Python"


def test_ask_name_vacancy_ok(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_name_vacancy"""

    mock_io["inputs"].extend(["Data Engineer"])
    mock_validators["validate_name_and_description"].return_value = ("ok", "Data Engineer")

    result = interactive.ask_name_vacancy()

    assert result is None
    assert interactive._answers["contains_name"] == "Data Engineer"


def test_ask_name_vacancy_skip(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_name_vacancy"""

    mock_io["inputs"].extend([""])
    mock_validators["validate_name_and_description"].return_value = ("skip", None)

    result = interactive.ask_name_vacancy()

    assert result is None
    assert "contains_name" not in interactive._answers


def test_ask_name_vacancy_back(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_name_vacancy"""

    mock_io["inputs"].extend(["назад"])
    mock_validators["validate_name_and_description"].return_value = ("back", None)

    result = interactive.ask_name_vacancy()

    assert result == "back"


def test_ask_url_single(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_url"""

    mock_io["inputs"].extend(["https://example.com"])
    mock_validators["validate_user_input"].return_value = ("ok", "https://example.com")
    mock_validators["validate_url"].return_value = ["https://example.com"]

    result = interactive.ask_url()

    assert result is None
    assert interactive._answers["url"] == "https://example.com"


def test_ask_url_list(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_url"""

    mock_io["inputs"].extend(["https://a.com, https://b.com"])
    mock_validators["validate_user_input"].return_value = ("ok", "https://a.com, https://b.com")
    mock_validators["validate_url"].return_value = ["https://a.com", "https://b.com"]

    interactive.ask_url()

    assert interactive._answers["url"] == ["https://a.com", "https://b.com"]


def test_ask_url_skip(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_url"""

    mock_io["inputs"].extend([""])
    mock_validators["validate_user_input"].return_value = ("skip", None)

    result = interactive.ask_url()

    assert result is None
    assert "url" not in interactive._answers


def test_ask_url_back(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_url"""

    mock_io["inputs"].extend(["назад"])
    mock_validators["validate_user_input"].return_value = ("back", None)

    result = interactive.ask_url()

    assert result == "back"


def test_ask_alternate_url_ok(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_alternate_url"""

    mock_io["inputs"].extend(["https://alt.com"])
    mock_validators["validate_user_input"].return_value = ("ok", "https://alt.com")
    mock_validators["validate_url"].return_value = ["https://alt.com"]

    result = interactive.ask_alternate_url()

    assert result is None
    assert interactive._answers["alternate_url"] == "https://alt.com"


def test_ask_use_alternate_url_yes(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода ask_use_alternate_url"""

    mock_io["inputs"].extend(["да"])

    result = interactive.ask_use_alternate_url()

    assert result is True


def test_ask_use_alternate_url_no(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода ask_use_alternate_url"""

    mock_io["inputs"].extend(["нет"])

    result = interactive.ask_use_alternate_url()

    assert result is False


def test_ask_use_alternate_url_back(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода ask_use_alternate_url"""

    mock_io["inputs"].extend(["назад"])

    result = interactive.ask_use_alternate_url()

    assert result == "back"


def test_ask_use_alternate_url_cancel(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода ask_use_alternate_url"""

    mock_io["inputs"].extend(["отмена"])

    with pytest.raises(FilterCancelled):
        interactive.ask_use_alternate_url()


def test_preview_uses_renderer(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода preview"""

    with patch("job_search.filters.interactive_input.FilterPreviewRenderer") as renderer_cls:
        renderer = renderer_cls.return_value
        interactive.preview()
        renderer_cls.assert_called_once()
        renderer.render.assert_called_once()


def test_confirm_apply(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_formatter: MagicMock
) -> None:
    """Тест для метода confirm"""

    mock_io["inputs"].extend(["да"])
    interactive._answers.update({"salary_from": 100})

    result = interactive.confirm()

    mock_formatter.build_from.assert_called_once_with(interactive._answers)
    assert result == {"ok": True}


def test_confirm_cancel(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода confirm"""

    mock_io["inputs"].extend(["отмена"])

    with pytest.raises(FilterCancelled):
        interactive.confirm()


def test_confirm_change_then_back(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода confirm"""

    mock_io["inputs"].extend(["изменить", "назад", "да"])
    with (
        patch.object(interactive, "_change_filter", return_value="back") as chg,
        patch.object(interactive._formatter, "build_from", return_value={"ok": True}) as bf,
    ):
        result = interactive.confirm()
        chg.assert_called_once()
        bf.assert_called_once()
        assert result == {"ok": True}


def test_change_filter_back(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода _change_filter"""

    mock_io["inputs"].extend(["назад"])

    result = interactive._change_filter()

    assert result == "back"


def test_change_filter_invalid_choice_then_ok_and_no_more(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any]
) -> None:
    """Тест для метода _change_filter"""

    mock_io["inputs"].extend(["9", "1", "нет"])
    with patch.object(interactive, "ask_salary") as ask_salary, patch.object(interactive, "preview") as preview:
        result = interactive._change_filter()
        ask_salary.assert_called_once()
        preview.assert_called_once()
        assert result is None


def test_change_filter_again_yes(interactive: InteractiveFilterInput, mock_io: dict[str, Any]) -> None:
    """Тест для метода _change_filter"""

    mock_io["inputs"].extend(["1", "да", "1", "нет"])
    with patch.object(interactive, "ask_salary") as ask_salary, patch.object(interactive, "preview") as preview:
        result = interactive._change_filter()
        assert ask_salary.call_count == 2
        preview.assert_called_once()
        assert result is None


def test_ask_salary_with_bounds_triggers_currency(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary"""

    mock_io["inputs"].extend(["100", "200", "usd"])
    mock_validators["validate_user_input"].side_effect = [
        ("ok", "100"),
        ("ok", "200"),
        ("ok", "usd"),
    ]
    mock_validators["validate_salary"].side_effect = [100, 200]
    mock_validators["validate_currency"].return_value = "USD"

    interactive.ask_salary()

    assert interactive._answers["salary_from"] == 100
    assert interactive._answers["salary_to"] == 200
    assert interactive._answers["currency"] == "USD"


def test_ask_salary_without_bounds_does_not_ask_currency(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода ask_salary"""

    mock_io["inputs"].extend(["", ""])
    mock_validators["validate_user_input"].side_effect = [
        ("skip", None),
        ("skip", None),
    ]

    interactive.ask_salary()

    assert interactive._answers.get("currency") is None


def test_reset_clears_answers(interactive: InteractiveFilterInput) -> None:
    """Тест для метода reset"""

    interactive._answers["salary_from"] = 100
    interactive.reset()
    assert interactive._answers == {}


def test_run_full_happy_path(
    interactive: InteractiveFilterInput,
    mock_io: dict[str, Any],
    mock_validators: dict[str, MagicMock],
    mock_formatter: MagicMock,
) -> None:
    """Тест для метода run"""

    # последовательность шагов:
    # salary_from, salary_to, currency, description, name, url, use_alt, confirm, confirm
    mock_io["inputs"].extend(
        [
            "100",  # salary_from
            "200",  # salary_to
            "usd",  # currency
            "описание",  # description
            "название",  # name
            "https://example.com",  # url
            "нет",  # use_alternate_url
            "да",  # confirm #1
            "да",  # confirm #2 (run вызывает confirm дважды)
        ]
    )

    # универсальный мок — работает только для шагов, где есть step
    def fake_validate_user_input(*args: Any, **kwargs: Any) -> tuple[str, str]:
        step = kwargs.get("step")
        if step is None:
            # confirm() не должен вызывать validate_user_input
            raise AssertionError("validate_user_input вызван в confirm()")

        user_input = kwargs.get("user_input") or args[1]
        return "ok", user_input

    mock_validators["validate_user_input"].side_effect = fake_validate_user_input

    mock_validators["validate_salary"].side_effect = [100, 200]
    mock_validators["validate_currency"].return_value = "USD"
    mock_validators["validate_name_and_description"].side_effect = [
        ("ok", "описание"),
        ("ok", "название"),
    ]
    mock_validators["validate_url"].return_value = ["https://example.com"]

    with patch("job_search.filters.preview_renderer.FilterPreviewRenderer") as renderer_cls:
        renderer = renderer_cls.return_value
        renderer.render.return_value = None

        result = interactive.run()

    assert result == {"ok": True}
    mock_formatter.build_from.assert_called_once()
    assert interactive._answers["salary_from"] == 100
    assert interactive._answers["salary_to"] == 200
    assert interactive._answers["currency"] == "USD"
    assert interactive._answers["contains_description"] == "описание"
    assert interactive._answers["contains_name"] == "название"
    assert interactive._answers["url"] == "https://example.com"


def test_run_cancel_during_step(
    interactive: InteractiveFilterInput, mock_io: dict[str, Any], mock_validators: dict[str, MagicMock]
) -> None:
    """Тест для метода run"""

    mock_io["inputs"].extend([""])
    # смоделируем, что validate_user_input выбрасывает FilterCancelled
    mock_validators["validate_user_input"].side_effect = FilterCancelled("cancel")

    result = interactive.run()

    assert result is None
