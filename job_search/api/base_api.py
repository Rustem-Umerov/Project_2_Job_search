from abc import ABC, abstractmethod
from typing import Any

from job_search.api.types import VacancyResult


class VacancyAPI(ABC):
    """
    Базовый интерфейс для всех сервисов вакансий.
    Обеспечивает единую сигнатуру для работы с разными API.
    """

    @abstractmethod
    def get_vacancies(self, keyword: str, **kwargs: Any) -> VacancyResult:
        """
        Возвращает список вакансий по ключевому слову и, по умолчанию, можно добавить дополнительные параметры.

        :param keyword: Ключевое слово
        :param kwargs: Словарь с дополнительными фильтрами (регион, количество на страницу и т.д.)
        :return: VacancyResult: объект Pydantic‑модели с результатами поиска.
        """

        pass

    @abstractmethod
    def get_all_vacancies(self, keyword: str, **kwargs: Any) -> VacancyResult:
        """
        Метод получает все вакансии по ключевому слову и, по умолчанию, можно добавить дополнительные параметры.

        :param keyword: Ключевое слово для поиска вакансий.
        :param kwargs: Дополнительные параметры запроса (например, регион, опыт).
        :return: VacancyResult: объект Pydantic‑модели с результатами поиска.
        """

        pass

    @abstractmethod
    def _connect(self, **kwargs: Any) -> dict[str, Any]:
        """
        Приватный метод для подключения к АПИ.
        Возвращает распарсенный JSON.
        """

        pass
