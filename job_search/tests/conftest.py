from typing import Any

import pytest


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
