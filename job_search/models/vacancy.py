from typing import Any

from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)


ALLOWED_FIELDS = [
    "name_vacancy",
    "url_vacancy",
    "alternate_url",
    "salary_from",
    "salary_to",
    "currency",
    "description",
]


class Vacancy:
    """
    Класс для создания объектов из вакансий полученных от АПИ.
    """

    __slots__ = ("name_vacancy", "url_vacancy", "alternate_url", "salary_from", "salary_to", "currency", "description")

    def __init__(
        self,
        name_vacancy: str,
        url_vacancy: str,
        alternate_url: str,
        salary_from: int | None,
        salary_to: int | None,
        currency: str,
        description: str,
    ) -> None:
        """
        Инициализация настройки атрибутов класса Vacancy.

        :param name_vacancy: Название вакансии.
        :param url_vacancy: Ссылка на вакансии.
        :param salary_from: Минимальная заработная плата по вакансии.
        :param salary_to: Максимальная заработная плата по вакансии.
        :param currency: Валюта заработной платы по вакансии.
        :param description: Описание (или требование) вакансии.
        """

        self.name_vacancy = name_vacancy
        self.url_vacancy = url_vacancy
        self.alternate_url = alternate_url
        self.salary_from = salary_from
        self.salary_to = salary_to
        self.currency = currency
        self.description = description

    def __str__(self) -> str:
        """
        Возвращает строковое представление объекта Vacancy.
        Формат включает название вакансии, зарплату, ссылку и краткое описание.

        Пример:
        Python Developer — от 120 000 до 180 000 RUR
        Ссылка: https://hh.ru/vacancy/123456
        Описание: Требуется опыт работы с Django. Ответственность за разработку backend.

        :return: Строка с краткой информацией о вакансии.
        """

        return (
            f"{self.name_vacancy} — {self.salary_str}\n"
            f"Ссылка: {self.url_vacancy}\n"
            f"Описание: {self.description}"
        )

    def __repr__(self) -> str:
        """
        Возвращает строковое представление объекта Vacancy для отладки.
        Формат включает ключевые поля: название, зарплату и ссылку.

        Пример:
        Vacancy(name='Python Developer', salary='от 120 000 до 180 000 RUR', url='https://hh.ru/vacancy/123456')

        :return: Строка, описывающая объект в техническом формате.
        """

        return f"Vacancy(name={self.name_vacancy!r}, salary={self.salary_str!r}, " f"url={self.url_vacancy!r})"

    def __eq__(self, other: object) -> bool:
        """
        Сравнивает вакансии по заработной плате.
        Использует get_salary_value() для правильного определения зарплаты.

        :param other: Объект класса Vacancy.
        :return: Булево значение (True/False)
        """

        if not isinstance(other, Vacancy):
            return NotImplemented

        return self.get_salary_value() == other.get_salary_value()

    def __lt__(self, other: object) -> bool:
        """
        Сравнение вакансий по средней зарплате.
        Использует get_salary_value() для правильного определения зарплаты.

        :param other: Объект класса Vacancy.
        :return: Булево значение (True/False)
        """

        if not isinstance(other, Vacancy):
            return NotImplemented

        return self.get_salary_value() < other.get_salary_value()

    def get_salary_value(self) -> int:
        """
        Возвращает числовое значение зарплаты для сравнения.
        Если указаны обе границы — возвращает среднее.
        Если указана одна — возвращает её.
        Если ничего не указано — возвращает 0.
        """

        if self.salary_from and self.salary_to:
            return (self.salary_from + self.salary_to) // 2
        return self.salary_from or self.salary_to or 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Vacancy":
        """
        Создаёт экземпляр Vacancy из словаря, полученного от hh.ru API.

        Извлекает ключевые поля (название, ссылка, зарплата, описание) и обрабатывает их.
        Если какие-либо поля отсутствуют, подставляет значения по умолчанию.

        :param data: (dict) Словарь с данными вакансии от API.
        :return: Новый экземпляр класса Vacancy.
        """

        # Название вакансии
        name_vacancy = (data.get("name") or "Название не указано").strip()

        # API-ссылка на вакансию (для логики)
        raw_url = data.get("url")
        url_vacancy = raw_url.strip() if isinstance(raw_url, str) else ""

        # Человекочитаемая ссылка (для отображения)
        raw_alt_url = data.get("alternate_url")
        alternate_url = raw_alt_url.strip() if isinstance(raw_alt_url, str) else ""

        description_parts = [
            data.get("snippet", {}).get("requirement"),
            data.get("snippet", {}).get("responsibility"),
        ]
        description_parts = [part.strip() for part in description_parts if isinstance(part, str) and part.strip()]
        description = " ".join(description_parts) if description_parts else "Описание не указано"

        salary = data.get("salary")
        salary_from, salary_to, currency = cls._parse_salary(salary_data=salary)

        return cls(name_vacancy, url_vacancy, alternate_url, salary_from, salary_to, currency, description)

    @staticmethod
    def _parse_salary(salary_data: dict | None) -> tuple[int | None, int | None, str]:
        """
        Приватный метод для извлечения информации о заработной плате из словаря API hh.ru.

        Возвращает:
        - минимальную зарплату (salary_from)
        - максимальную зарплату (salary_to)
        - валюту зарплаты (currency)

        Метод устойчив к отсутствующим или некорректным данным:
        - если salary_data отсутствует или не является словарём, возвращаются значения по умолчанию
        - если ключи 'from', 'to' или 'currency' отсутствуют,
        соответствующие значения будут None или "Валюта не указана"

        :param salary_data: Словарь с данными о зарплате или None
        :return: Кортеж (salary_from, salary_to, currency)
        """

        # ниже указал дефолтные значения.
        salary_from = None
        salary_to = None
        currency = "Валюта не указана"

        # если salary_data не словарь, а, например, None, то возвращаю дефолтные значения.
        if not isinstance(salary_data, dict):
            return salary_from, salary_to, currency

        # если salary_data это словарь, то значения берутся из словаря.
        salary_from = salary_data.get("from")
        salary_to = salary_data.get("to")
        currency = salary_data.get("currency", "Валюта не указана")

        return salary_from, salary_to, currency

    @property
    def salary_str(self) -> str:
        """
        Формирует строковое представление заработной платы на основе атрибутов salary_from, salary_to и currency.

        Примеры:
        - "от 80 000 до 120 000 RUR"
        - "от 100 000 RUR"
        - "до 150 000 USD"
        - "Зарплата не указана" — если ни одна граница не указана

        :return: Отформатированная строка с информацией о зарплате
        """

        if self.salary_from is not None and self.salary_to is not None:
            formatted_from = f"{self.salary_from:,}".replace(",", " ")
            formatted_to = f"{self.salary_to:,}".replace(",", " ")

            salary_str = f"от {formatted_from} до {formatted_to} {self.currency or 'Валюта не указана'}"

        elif self.salary_from is not None:
            formatted_from = f"{self.salary_from:,}".replace(",", " ")

            salary_str = f"от {formatted_from} {self.currency or 'Валюта не указана'}"

        elif self.salary_to is not None:
            formatted_to = f"{self.salary_to:,}".replace(",", " ")

            salary_str = f"до {formatted_to} {self.currency or 'Валюта не указана'}"

        else:
            salary_str = "Зарплата не указана"

        return salary_str

    @classmethod
    def from_list(cls, data: list[dict], strict: bool = False) -> list["Vacancy"]:
        """
        Преобразует список словарей с данными вакансий в список объектов класса Vacancy.

        Метод устойчив к ошибкам и работает в двух режимах:
        - strict=True: выбрасывает исключение при первой ошибке
        - strict=False: пропускает ошибочные записи, логирует их и продолжает обработку

        Все ошибки и пропущенные элементы логируются через стандартный логгер.

        :param data: Список словарей, каждый из которых должен соответствовать структуре,
                     ожидаемой методом from_dict().
        :param strict: Флаг режима обработки ошибок. Если True — метод выбрасывает исключение при первой ошибке.
        :return: Список успешно созданных объектов Vacancy.
        :raises TypeError: Если входной аргумент не является списком.
        :raises ValueError: Если strict=True и возникает ошибка при обработке словаря.
        """

        if not isinstance(data, list):
            logger.error(f"Ожидался список, но получено: {type(data).__name__}")
            raise TypeError("Ожидается список словарей")

        obj_list_result = []
        skipped = 0
        skipped_items = []

        for index, cls_obj in enumerate(data):
            if not isinstance(cls_obj, dict):
                logger.warning(f"[{index}] Пропущен элемент: не словарь → {cls_obj}")
                skipped += 1
                continue

            try:
                obj_list_result.append(cls.from_dict(cls_obj))
            except (TypeError, KeyError, ValueError) as e:
                if strict:
                    logger.error(f"[{index}] Ошибка в данных при strict=True: {e}")
                    raise ValueError(f"Ошибка в данных: {e}")

                logger.warning(f"Ошибка при обработке вакансии: {e} | Данные: {cls_obj}")
                skipped += 1
                skipped_items.append(cls_obj)
                continue

        logger.info(
            f"Преобразование списка словарей с вакансиями в список объектов класса Vacancy завершено.\n"
            f"Успешно обработано: {len(obj_list_result)}.\n"
            f"Количество пропущенных словарей: {skipped}.\n"
            f"Список с пропущенными словарями: {skipped_items}."
        )
        return obj_list_result
