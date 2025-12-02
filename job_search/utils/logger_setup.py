import logging
from pathlib import Path
from typing import Optional


def parse_log_level(level: str | int) -> int:
    """
    Преобразует строковое или числовое значение уровня логирования в числовой код logging.

    Args:
        level (str | int): Уровень логирования. Может быть строкой
            ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL") — регистр не важен,
            или числом (например, logging.DEBUG = 10).

    Returns:
        int: Числовой уровень логирования, совместимый с logging.

    Raises:
        ValueError: Если передан недопустимый уровень.
    """

    if isinstance(level, int):
        return level

    level = level.upper()
    levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    if level not in levels:
        raise ValueError(f"Invalid log level: {level}")

    return levels[level]


def get_logger(
    name: str,
    log_file: Optional[str] = None,
    fmt: str = "[%(asctime)s] %(levelname)s - %(name)s - %(funcName)s - %(message)s",
    level: str = "INFO",
) -> logging.Logger:
    """
    Создаёт и возвращает логгер с консольным и файловым выводом.

    :param name: Имя логгера (обычно __name__).
    :param log_file: Имя файла для логов (например, "app.log").
    :param fmt: Формат лог-сообщений.
    :param level: Уровень логирования ("DEBUG", "INFO", "ERROR" и т.д.).
    :return: Настроенный объект logging.Logger.
    """

    logger = logging.getLogger(name)
    logger.setLevel(parse_log_level(level))
    logger.handlers.clear()

    formatter = logging.Formatter(fmt)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        logs_dir = Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / log_file

        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
