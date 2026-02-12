from typing import Any, Optional

from job_search.models.vacancy import ALLOWED_FIELDS, Vacancy
from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)

ALLOWED_OPERATORS = ["eq", "gte", "lte", "contains", "in"]

ALLOWED_SALARY_OPERATORS = {"salary_from": {"eq", "gte"}, "salary_to": {"eq", "lte"}}


class VacancyFilter:
    """
    Класс для фильтрации объектов Vacancy по заданным условиям.
    """

    def __init__(self, filter_dict: dict) -> None:
        """
        Инициализирует объект фильтрации вакансий.

        :param filter_dict: Словарь с условиями фильтрации. Ключи — поля вакансии,
                            значения — ожидаемые значения или операторы.
        :raises ValueError: Если переданный фильтр не является словарём.
        """

        if not isinstance(filter_dict, dict):
            logger.error("Параметры фильтрации должны быть словарём.")
            raise ValueError("Фильтр должен быть словарём.")

        self.filter = filter_dict

    def match(self, vacancy: Vacancy) -> bool:
        """
        Проверяет, соответствует ли вакансия всем условиям фильтра.
        """

        logger.debug(f"Начинаем фильтрацию вакансии: {vacancy}")

        for key, value in self.filter.items():
            logger.debug(f"Проверяем поле: '{key}' с фильтром: {value}")

            if key not in ALLOWED_FIELDS:
                logger.warning(f"Поле '{key}' не входит в список разрешённых. Пропускаем.")
                continue

            method = getattr(self, f"_match_{key}", None)
            if method is None:
                logger.warning(f"Метод фильтрации для поля '{key}' не найден. Пропускаем.")
                continue

            if not method(vacancy):
                logger.info(f"Вакансия не прошла фильтрацию по полю '{key}'.")

                return False

        logger.info(f"Вакансия '{vacancy}' успешно прошла все фильтры.")
        return True

    def _match_name_vacancy(self, vacancy: Vacancy) -> bool:
        """Фильтрация по названию вакансии."""

        return self._match_field("name_vacancy", vacancy)

    def _match_url_vacancy(self, vacancy: Vacancy) -> bool:
        """Фильтрация по url вакансии."""

        return self._match_field("url_vacancy", vacancy)

    def _match_alternate_url(self, vacancy: Vacancy) -> bool:
        """Фильтрация по alternate_url вакансии."""

        return self._match_field("alternate_url", vacancy)

    def _match_description(self, vacancy: Vacancy) -> bool:
        """Фильтрация по описанию вакансии."""

        return self._match_field("description", vacancy)

    def _match_currency(self, vacancy: Vacancy) -> bool:
        """Фильтрация по валюте вакансии."""

        return self._match_field("currency", vacancy)

    def _match_salary(self, vacancy: Vacancy) -> bool:
        """Фильтрация по заработной плате вакансии."""

        for salary_field in ["salary_from", "salary_to"]:
            if salary_field not in self.filter:
                continue
            value = self.filter[salary_field]
            actual = getattr(vacancy, salary_field, None)

            logger.debug(f"Проверка зарплаты: поле '{salary_field}', значение = {actual}, фильтр = {value}")

            if isinstance(value, dict):
                for op, expected in value.items():
                    if op not in ALLOWED_OPERATORS:
                        logger.warning(f"Оператор '{op}' не поддерживается. Пропускаем.")
                        continue
                    if not self._apply_operator(op, actual, expected):
                        logger.info(f"Зарплата не прошла фильтр: {salary_field} {op} {expected} → {actual}")
                        return False
            else:
                if not self._apply_operator("eq", actual, value):
                    logger.info(f"Зарплата не равна ожидаемой: {actual} != {value}")
                    return False

        logger.debug(f"Проверка зарплаты: поле '{salary_field}' успешно прошло.")
        return True

    def _match_field(self, field: str, vacancy: Vacancy) -> bool:
        """
        Универсальный метод сравнения для простых полей.
        """

        value = self.filter.get(field)
        actual = getattr(vacancy, field, None)
        logger.debug(f"Сравниваем поле '{field}': значение вакансии = {actual}, фильтр = {value}")

        if isinstance(value, dict):
            for op, expected in value.items():
                if op not in ALLOWED_OPERATORS:
                    logger.warning(f"Оператор '{op}' не поддерживается. Пропускаем.")
                    continue

                if not self._apply_operator(op, actual, expected):
                    logger.info(f"Оператор '{op}' не прошёл: {actual} vs {expected}")
                    return False
        else:
            if not self._apply_operator("eq", actual, value):
                logger.info(f"Сравнение по равенству не прошло: {actual} != {value}")
                return False

        logger.debug(f"Сравнение поле '{field}' успешно прошло. Значение вакансии = {actual}, фильтр = {value}")
        return True

    @staticmethod
    def _apply_operator(op: str, actual: Any, expected: Any) -> bool:
        """
        Проверяет, соответствует ли значение из вакансии заданному условию фильтрации.

        :param op: Оператор сравнения (один из: "eq", "gte", "lte", "contains", "in").
        :param actual: Значение из объекта Vacancy, которое нужно проверить.
        :param expected: Значение из фильтра, с которым нужно сравнить.
        :return: True, если условие выполнено; False — в противном случае.
        """

        logger.debug(f"Применяем оператор '{op}': actual = {actual}, expected = {expected}")

        if op == "eq":  # eq: точное совпадение
            return bool(actual == expected)

        elif op == "gte":  # gte: больше или равно, если значение не None
            return actual is not None and actual >= expected

        elif op == "lte":  # lte: меньше или равно, если значение не None
            return actual is not None and actual <= expected

        elif op == "contains":  # contains: подстрока содержится в строке
            if isinstance(actual, str) and isinstance(expected, str):
                return expected.lower().strip() in actual.lower().strip()
            return False

        elif op == "in":  # in: значение входит в список/множество
            if isinstance(expected, (list, set, tuple)):
                return actual in expected

        logger.warning(f"Неизвестный оператор '{op}'. Возвращаем False.")
        return False  # если оператор неизвестен — вернуть False


def normalize_filter(raw_filter: dict) -> dict:
    """
    Преобразует входящий фильтр в стандартный формат, понятный VacancyFilter.
    Например, разбивает 'salary' на 'salary_from' и 'salary_to'.
    """

    logger.debug(f"Исходный фильтр: {raw_filter}")

    if not isinstance(raw_filter, dict):
        logger.error("Фильтр должен быть словарем.")

        raise TypeError("Фильтр должен быть словарем.")

    result_filter = {}
    for field in ALLOWED_FIELDS:
        value = raw_filter.get(field)
        if value is not None:
            result_filter[field] = value

    salary_block = raw_filter.get("salary")
    if isinstance(salary_block, dict):
        for salary_key in ["salary_from", "salary_to"]:
            value = salary_block.get(salary_key)

            validated = check_value(value, salary_key)
            if validated is not None and salary_key not in result_filter:
                result_filter[salary_key] = validated

    logger.debug(f"Нормализованный фильтр: {result_filter}")
    return result_filter


def check_value(value: Any, field_name: str) -> Optional[float]:
    """
    Проверяет и преобразует значение поля salary_from или salary_to в числовой формат.
    Возвращает float, если значение допустимо, иначе None.

    :param value: Значение, которое нужно проверить
    :param field_name: Имя поля (salary_from или salary_to) — используется для логирования
    :return: float или None
    """

    if value is None:
        logger.debug(f"Значение '{field_name}' отсутствует.")
        return None

    if isinstance(value, (int, float)):
        logger.debug(f"Значение '{field_name}' уже числовое: {value}")
        return float(value)

    if isinstance(value, str):
        try:
            converted = float(value.strip())
            logger.debug(f"Значение '{field_name}' — строка, успешно преобразована в число: {converted}")
            return converted
        except ValueError:
            logger.warning(f"Значение '{field_name}' — строка, но не удалось преобразовать в число: {value}")
            return None

    if isinstance(value, dict):
        for key in value:
            if key in ALLOWED_SALARY_OPERATORS.get(field_name, set()):
                raw = value[key]
                try:
                    converted = float(raw.strip()) if isinstance(raw, str) else float(raw)
                    logger.debug(
                        f"Значение '{field_name}' — словарь с оператором '{key}', преобразовано в число: {converted}"
                    )
                    return converted

                except (ValueError, TypeError):
                    logger.warning(
                        f"Значение '{field_name}' — словарь с оператором '{key}', но преобразование не удалось: {raw}"
                    )
                    return None

        logger.warning(f"Значение '{field_name}' — словарь, но не содержит допустимых операторов: {value}")
        return None

    logger.warning(f"Значение '{field_name}' имеет неподдерживаемый тип: {type(value).__name__}")
    return None
