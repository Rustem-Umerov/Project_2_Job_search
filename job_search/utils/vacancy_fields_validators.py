from typing import Collection, Literal, Optional

from job_search.utils.exceptions import FilterCancelled
from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)


def validate_salary(io: dict, user_input: str) -> Optional[float]:
    """
    Преобразует ввод пользователя в число (float или int).
    Возвращает None, если ввод некорректен.

    :param io: Словарь с ключами "input" и "output"
    :param user_input: Строка, введённая пользователем
    :return: Число (float или int) или None при ошибке
    """

    try:
        result = float(user_input.strip())
        # Преобразуем в int, если число целое
        return int(result) if result.is_integer() else result
    except ValueError:
        logger.warning("Ошибка преобразования зарплаты: '%s' не является числом.", user_input)
        io["output"]("❌ Ошибка: зарплата должна быть числом. Попробуйте ещё раз.")
        return None


def validate_currency(user_input: str, allowed_currencies: Collection[str]) -> Optional[str]:
    """
    Проверяет, введенную пользователем, валюту.

    :param user_input: Строка, введённая пользователем
    :param allowed_currencies: Список допустимых валют
    :return: Строка валюты в верхнем регистре, если валюта допустима; иначе None
    """

    currency = user_input.strip().upper()
    logger.debug("Преобразованная валюта: '%s'", currency)

    if currency in allowed_currencies:
        return currency

    logger.warning("Недопустимая валюта: '%s'. Допустимые значения: %s", currency, allowed_currencies)
    return None


def validate_name_and_description(
    *, io: dict, raw_input: str, step: str
) -> tuple[Literal["ok", "skip", "error", "back"], Optional[str]]:
    """
    Проверяет, введенные пользователем название и описание вакансии.

    :param io: Словарь с ключами "input" и "output"
    :param raw_input: Строка, введённая пользователем
    :param step: Название шага(метода)
    :return: Название или описание если все проверки пройдены, иначе None
    """

    user_input = raw_input.strip()
    logger.debug("Ответ пользователя на шаг '%s': raw='%s', stripped='%s'", step, raw_input, user_input)

    if user_input.lower() == "отмена":
        logger.warning("Пользователь отменил сборку фильтра на шаге '%s'.", step)
        io["output"]("Сборка фильтра отменена.")
        raise FilterCancelled("Фильтр отменён пользователем.")

    if user_input.lower() == "назад":
        logger.info("Пользователь вернулся на шаг назад из шага '%s'.", step)
        io["output"]("Вы возвращаетесь на шаг назад.")
        return "back", None

    if raw_input == "":
        logger.info("Пользователь пропустил шаг '%s'.", step)
        io["output"](f"{step.capitalize()} не указано. Переходим к следующему шагу.")
        return "skip", None

    if user_input == "":
        logger.warning("Ввод состоит только из пробелов. %s не принято.", step.capitalize())
        io["output"](f"❌ {step.capitalize()} не может состоять только из пробелов. Попробуйте ещё раз.")
        return "error", None

    return "ok", user_input


def validate_user_input(
    *, io: dict, user_input: str, step: str, first_step: bool = False
) -> tuple[Literal["ok", "skip", "back"], Optional[str]]:
    """
    Стандартная проверка пользовательского ввода.

    :param io: Словарь с ключами "input" и "output"
    :param user_input: Строка, введённая пользователем
    :param step: Название шага(метода)
    :param first_step: Булево значение. Если первый шаг - True, если второй - False
    :return: Пользовательский ввод, если все проверки пройдены, иначе None
    """

    logger.debug("Ответ пользователя на шаг '%s': '%s'", step, user_input)

    if user_input.lower() == "отмена":
        logger.warning("Пользователь отменил сборку фильтра на шаге '%s'.", step)
        io["output"]("Сборка фильтра отменена")
        raise FilterCancelled("Фильтр отменён пользователем.")

    if user_input == "":
        logger.info("Пользователь пропустил шаг '%s'.", step)
        io["output"](f"{step.capitalize()} не указан. Переходим к следующему шагу.")
        return "skip", None

    if user_input.lower() == "назад":
        if first_step:
            logger.info("Пользователь попытался вернуться назад на первом шаге.")
            io["output"]("Вы уже на первом шаге. Назад идти некуда.")
            return "back", None

        logger.info("Пользователь вернулся на шаг назад из запроса '%s'.", step)
        io["output"]("Вы возвращаетесь на шаг назад.")
        return "back", None

    return "ok", user_input


def validate_url(*, io: dict, user_input: str, step: str) -> Optional[list[str]]:
    """
    Стандартная проверка пользовательского ввода ссылок на вакансии.

    :param io: Словарь с ключами "input" и "output"
    :param user_input: Строка, введённая пользователем
    :param step: Название шага(метода)
    :return: Список с url, если проверки пройдены, иначе None
    """

    urls = [url.strip() for url in user_input.split(",") if url.strip()]
    logger.debug("Обработанный список %s: %s", step, urls)

    if not urls:
        logger.warning("Ввод не содержит ни одного корректного %s.", step)
        io["output"](f"❌ Ввод не содержит ни одного корректного {step}. Попробуйте ещё раз.")
        return None

    if not all(url.startswith("http") for url in urls):
        logger.warning("Некорректный формат %s: не все URL начинаются с http/https. Ввод: %s", step, urls)
        io["output"](f"❌ Все {step} должны начинаться с http или https. Попробуйте ещё раз.")
        return None
    return urls


def validate_list(data: object, element_type: type = dict) -> bool:
    """
    Проверяет, что data — это непустой список словарей.
    Логирует ошибки при несоответствии.

    :param data: Объект, который должен быть списком вакансий.
    :param element_type: Тип элементов списка.
    :return: True, если список валиден; False — если нет.
    """

    if not isinstance(data, list):
        logger.error("Ожидался список, но получено: %s", {type(data).__name__})
        return False

    if not data:
        logger.info("Список пуст — операция невозможна")
        return False

    if not all(isinstance(v, element_type) for v in data):
        logger.warning("Некоторые элементы списка не являются словарями")
        return False
    return True


def norm_int(value: str | int) -> Optional[int]:
    """Преобразует в int, если возможно."""

    if isinstance(value, (str, int)):
        try:
            return int(value)
        except (TypeError, ValueError):
            logger.warning("Не удалось преобразовать значение '%s' в int", value)
            return None

    logger.error(
        "Переданное значение имеет не правильный тип: %s. Должен быть числовой или строковой тип.",
        type(value).__name__,
    )
    return None


def norm_str(value: object, *, lower: bool = False) -> Optional[str]:
    """Обрезает пробелы, пустое → None."""

    if isinstance(value, str):
        s = value.strip()
        if not s:
            logger.warning("Передана строка из пробельных символов.")
            return None
        if lower:
            logger.debug("Строка приведена к нижнему регистру.")
            return s.lower()
        return s

    logger.error("Переданное значение имеет не правильный тип: %s. Должна быть строка.", type(value).__name__)
    return None
