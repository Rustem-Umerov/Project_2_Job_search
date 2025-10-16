from typing import List

from job_search.models.vacancy import Vacancy
from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)


def sort_by_salary(list_vacancy: List[Vacancy], reverse: bool = True) -> List[Vacancy]:
    """
    Сортирует список вакансий по зарплате.

    Логика:
    - Использует функцию get_salary для вычисления ключа сортировки.
    - По умолчанию сортирует по убыванию (reverse=True).
    - Игнорирует объекты, не являющиеся Vacancy.

    Args:
        list_vacancy (List[Vacancy]): Список объектов для сортировки.
        reverse (bool): Направление сортировки (True = по убыванию).

    Returns:
        List[Vacancy]: Новый список вакансий, отсортированный по зарплате.

    Raises:
        ValueError: Если get_salary обнаружит некорректные данные в вакансии.

    Example:
        >>> vacancies = [Vacancy(salary_from=100, salary_to=200), Vacancy(salary_from=50)]
        >>> sort_by_salary(vacancies)
        [Vacancy(salary_from=100, salary_to=200), Vacancy(salary_from=50)]

    """

    logger.debug("Количество вакансии в сыром списке: %s", len(list_vacancy))

    logger.debug("Начинается фильтрация списка вакансий: остаются только объекты класса Vacancy.")
    valid_vacancies = [v for v in list_vacancy if isinstance(v, Vacancy)]
    logger.debug("Отфильтрованный список. Количество вакансии: %s", len(valid_vacancies))

    difference = len(list_vacancy) - len(valid_vacancies)
    if difference:
        logger.debug("Количество отфильтрованных объектов списка: %s", difference)

    logger.debug("Начинается сортировка вакансий по зарплате. reverse=%s", reverse)
    try:
        sorted_vacancies = sorted(valid_vacancies, key=get_salary, reverse=reverse)
        logger.debug("Сортировка завершена. Количество вакансий: %s", len(sorted_vacancies))
        return sorted_vacancies
    except ValueError as e:
        logger.error("Ошибка при вычислении зарплаты: %s", e, exc_info=True)
        raise


def get_salary(vacancy: Vacancy) -> int:
    """
    Возвращает числовое значение зарплаты для сортировки вакансий.

    Логика расчёта:
    - Если заданы оба поля salary_from и salary_to → берётся среднее арифметическое.
    - Если задано только одно из полей → используется оно.
    - Если оба поля отсутствуют → возвращается 0.

    Args:
        vacancy (Vacancy): Объект вакансии с полями salary_from и salary_to.

    Returns:
        int: Числовое значение зарплаты, всегда целое число.

    Raises:
        ValueError: Если поля зарплаты содержат некорректные данные (например, строку).

    Example:
        >>> get_salary(Vacancy(salary_from=100000, salary_to=200000))
        150000
    """

    logger.debug("Начинается вычисление зарплаты по вакансии.")

    salary_from = vacancy.salary_from
    salary_to = vacancy.salary_to
    logger.debug(
        "Сырые данные заработной платы по вакансии - salary_from: '%r' , salary_to: '%r'", salary_from, salary_to
    )

    # Проверка типов: если значение не None, оно должно быть числом
    if salary_from is not None and not isinstance(salary_from, (int, float)):
        logger.warning("Некорректное значение salary_from=%r в вакансии %r", salary_from, vacancy)
        raise ValueError(f"Некорректное значение salary_from: {salary_from}")
    if salary_to is not None and not isinstance(salary_to, (int, float)):
        logger.warning("Некорректное значение salary_to=%r в вакансии %r", salary_to, vacancy)
        raise ValueError(f"Некорректное значение salary_to: {salary_to}")

    # Основная логика
    if salary_from is not None and salary_to is not None:
        salary = int((salary_from + salary_to) / 2)
        logger.debug("В вакансии указаны salary_from и salary_to - средняя заработная плата: '%r'", salary)
        return salary

    elif salary_from is not None:
        logger.debug("В вакансии указано только salary_from = '%r'", int(salary_from))
        return int(salary_from)

    elif salary_to is not None:
        logger.debug("В вакансии указано только salary_to = '%r'", int(salary_to))
        return int(salary_to)
    else:
        logger.debug("В вакансии отсутствует информация по вакансии. По умолчанию зарплата = 0")
        return 0


def get_top_n_vacancies(vacancies: List["Vacancy"], n: int, reverse: bool = True) -> List["Vacancy"]:
    """
    Возвращает топ-N вакансий, отсортированных по зарплате.

    Логика:
    - Использует функцию sort_by_salary для упорядочивания списка.
    - По умолчанию сортирует по убыванию (reverse=True), чтобы вернуть вакансии с самыми высокими зарплатами.
    - Если список пустой → возвращается пустой список.
    - Если n <= 0 → возвращается пустой список.
    - Если n больше количества доступных вакансий → возвращаются все вакансии.

    Args:
        vacancies (List[Vacancy]): Список объектов для сортировки.
        n (int): Количество вакансий, которые нужно вернуть.
        reverse (bool, optional): Направление сортировки.
            True = по убыванию (по умолчанию).
            False = по возрастанию.

    Returns:
        List[Vacancy]: Новый список, содержащий топ-N вакансий.

    Raises:
        ValueError: Если sort_by_salary обнаружит некорректные данные в полях зарплаты.

    Example:
        >>> list_vacancies = [
        ...     Vacancy(salary_from=100000, salary_to=200000),
        ...     Vacancy(salary_from=50000, salary_to=70000),
        ...     Vacancy(salary_from=120000, salary_to=150000),
        ... ]
        >>> get_top_n_vacancies(vacancies, n=2)
        [Vacancy(salary_from=100000, salary_to=200000),
         Vacancy(salary_from=120000, salary_to=150000)]
    """

    logger.debug("Количество вакансии в сыром списке: %s", len(vacancies))

    if not vacancies:
        logger.warning("Ошибка: список с вакансиями пуст. Возвращается пустой список.")
        return []

    logger.debug("Необходимо вернуть топ %s вакансии", n)

    if n <= 0:
        logger.error("Ошибка: неверное количество вакансий для возврата = '%s'", n)
        return []

    try:
        sort_vacancies = sort_by_salary(vacancies, reverse=reverse)

        if n > len(sort_vacancies):
            logger.info(
                "Количество вакансий (%s) меньше, чем запрошено (%s). " "Будут возвращены все доступные вакансии.",
                len(sort_vacancies),
                n,
            )

        logger.debug("Список вакансий успешно отсортирован.")
        return sort_vacancies[:n]

    except ValueError as e:
        logger.error("Ошибка при сортировки вакансий: %s", e, exc_info=True)
        raise
