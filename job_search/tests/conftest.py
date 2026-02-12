from pathlib import Path
from typing import Any, Callable, cast
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from job_search.models.vacancy import Vacancy
from job_search.storage.json_saver import JSONVacancyStorage


@pytest.fixture
def mock_io() -> dict[str, Any]:
    """Создаёт мокк ввода/вывода для тестов."""

    outputs: list[str] = []

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
def vacancy() -> Vacancy:
    """Базовая вакансия для тестов."""

    return Vacancy(
        name_vacancy="Python Dev",
        url_vacancy="http://example.com",
        alternate_url="http://alt.example.com",
        salary_from=100000,
        salary_to=150000,
        currency="RUR",
        description="Требования: опыт 3 года",
    )


@pytest.fixture
def salary_dict() -> dict:
    """Пример salary блока из API."""

    return {"from": 100000, "to": 150000, "currency": "RUR"}


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Временная директория для тестов."""
    return tmp_path


@pytest.fixture
def storage(temp_dir: Path) -> JSONVacancyStorage:
    """Создаёт хранилище в temp_dir."""

    with patch("job_search.storage.json_saver.Path") as mock_path:
        path_mock = MagicMock()
        mock_path.return_value = path_mock

        # Path("...").resolve() → temp_dir
        path_mock.resolve.return_value = temp_dir

        # Path("...").parent → temp_dir
        type(path_mock).parent = PropertyMock(return_value=temp_dir)

        # Path("...").with_suffix(".json") → temp_dir / "vacancies.json"
        path_mock.with_suffix.side_effect = lambda suffix: temp_dir / ("vacancies" + suffix)

        s = JSONVacancyStorage("vacancies.json")
        s._data_dir = temp_dir
        s._filepath = temp_dir / "vacancies.json"
        # noinspection PyProtectedMember
        s._filepath.write_text("[]", encoding="utf-8")
        return s


@pytest.fixture
def vacancy_factory() -> Callable[..., Vacancy]:
    """Фабрика для быстрого создания объектов Vacancy с нужными полями."""

    def _make(**kwargs: Any) -> Vacancy:
        defaults: dict[str, Any] = dict(
            name_vacancy="Test Vacancy",
            url_vacancy="http://example.com",
            salary_from=None,
            salary_to=None,
        )
        defaults.update(kwargs)
        return Vacancy(**cast(dict[str, Any], defaults))

    return _make


@pytest.fixture
def io_mock() -> dict[str, Any]:
    """
    Фикстура создаёт словарь io с моками input/output.
    Input — возвращает значения из очереди.
    Output — записывает вывод в список.
    """

    outputs: list[str] = []
    queue: list[str] = []

    def fake_input(_: str) -> str:
        return queue.pop(0)

    def fake_output(msg: str) -> None:
        outputs.append(msg)

    return {"input": fake_input, "output": fake_output, "queue": queue, "outputs": outputs}


@pytest.fixture
def temp_logs_dir(tmp_path: Path) -> Path:
    """
    Временная директория для логов.
    Используется при тестировании get_logger с log_file.
    """

    return tmp_path


@pytest.fixture
def io_mock_simple() -> dict[str, Any]:
    """
    Создаёт io-объект с моками input/output.
    output сохраняет сообщения в список outputs.
    """

    outputs: list[str] = []

    def fake_output(msg: str) -> None:
        outputs.append(msg)

    return {"output": fake_output, "outputs": outputs}
