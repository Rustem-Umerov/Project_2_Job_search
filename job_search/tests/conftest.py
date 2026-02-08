from pathlib import Path
from typing import Any
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


# @pytest.fixture
# def sample_vacancy() -> Vacancy:
#     """Пример вакансии."""
#
#     return Vacancy(
#         name_vacancy="Python Dev",
#         url_vacancy="http://example.com",
#         alternate_url="http://alt.example.com",
#         salary_from=100,
#         salary_to=200,
#         currency="RUR",
#         description="Требования"
#     )
