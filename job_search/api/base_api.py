from abc import ABC, abstractmethod
from typing import Any


class VacancyAPI(ABC):
    """
    Базовый интерфейс для всех сервисов вакансий.
    Обеспечивает единую сигнатуру для работы с разными API.
    """

    @abstractmethod
    def get_vacancies(self, keyword: str, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Возвращает список вакансий по ключевому слову.
        params могут содержать фильтры (регион, количество на страницу и т.д.).
        """

        pass

    @abstractmethod
    def _connect(self, **kwargs: Any) -> dict[str, Any]:
        """
        Приватный метод для подключения к АПИ.
        Возвращает распарсенный JSON.
        """

        pass
