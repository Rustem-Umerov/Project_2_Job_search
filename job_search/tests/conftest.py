from typing import Any

import pytest

from job_search.models.vacancy import Vacancy


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
