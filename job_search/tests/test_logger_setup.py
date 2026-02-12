import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from job_search.utils.logger_setup import get_logger, parse_log_level


@pytest.mark.parametrize(
    "input_level, expected",
    [
        ("DEBUG", logging.DEBUG),
        ("debug", logging.DEBUG),
        ("Info", logging.INFO),
        ("warning", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("critical", logging.CRITICAL),
        (10, 10),
        (50, 50),
    ],
)
def test_parse_log_level_valid(input_level: str | int, expected: int) -> None:
    """Корректно преобразует строковые и числовые уровни логирования."""

    assert parse_log_level(input_level) == expected


@pytest.mark.parametrize("bad_level", ["WRONG", "bad", "123abc", "", "none"])
def test_parse_log_level_invalid(bad_level: str) -> None:
    """Выбрасывает ValueError при некорректном уровне логирования."""

    with pytest.raises(ValueError):
        parse_log_level(bad_level)


def test_get_logger_basic() -> None:
    """
    Smoke‑тест: логгер создаётся, уровень устанавливается,
    и хотя бы один handler присутствует.
    """

    logger = get_logger("test_logger_basic", level="DEBUG")

    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) >= 1


def test_get_logger_console_handler_format() -> None:
    """
    Проверяет, что у логгера есть StreamHandler с корректным уровнем и форматтером.
    """

    logger = get_logger("test_logger_format", level="INFO")

    stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    assert len(stream_handlers) == 1

    handler = stream_handlers[0]
    assert handler.level == logging.DEBUG
    assert isinstance(handler.formatter, logging.Formatter)


def test_get_logger_with_file_handler(temp_logs_dir: Path) -> None:
    """
    Проверяет, что при указании log_file создаётся FileHandler.
    Путь к logs/ мокируется, чтобы не писать в реальную файловую систему.
    """

    fake_logs_dir = temp_logs_dir / "logs"
    fake_logs_dir.mkdir()

    with patch("job_search.utils.logger_setup.Path") as mock_path:
        # Настраиваем Path(__file__).resolve().parent.parent / "logs"
        mock_path.return_value.resolve.return_value.parent.parent.__truediv__.return_value = fake_logs_dir

        logger = get_logger("test_logger_file", log_file="test.log", level="INFO")

        file_handlers = [h for h in logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1

        handler = file_handlers[0]
        assert handler.level == logging.DEBUG
        assert handler.baseFilename.endswith("test.log")


def test_get_logger_clears_previous_handlers() -> None:
    """
    Проверяет, что get_logger очищает старые handlers перед добавлением новых.
    """

    logger = get_logger("test_logger_cleanup", level="INFO")
    initial_handlers_count = len(logger.handlers)

    # Добавляем фейковый handler вручную
    logger.addHandler(logging.NullHandler())
    assert len(logger.handlers) == initial_handlers_count + 1

    # Повторный вызов get_logger должен очистить handlers
    logger2 = get_logger("test_logger_cleanup", level="INFO")
    assert len(logger2.handlers) == initial_handlers_count


def test_get_logger_invalid_level() -> None:
    """
    Проверяет, что get_logger пробрасывает ошибку parse_log_level.
    """

    with pytest.raises(ValueError):
        get_logger("test_logger_invalid", level="WRONG")
