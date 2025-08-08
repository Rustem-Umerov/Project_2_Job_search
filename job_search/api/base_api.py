from abc import ABC, abstractmethod
from typing import Any


class VacancyAPI(ABC):
    """Абстрактный базовый класс, описывающий интерфейс для всех API-сервисов.

    Абстрактные методы:
        Публичный метод get_vacancies, для получения вакансий.
        Приватный метод _connect для подключения к АПИ.
    """

    @abstractmethod
    def get_vacancies(self, keyword: str, **kwargs: Any) -> list[dict[str, Any]]:
        """Публичный метод для получения вакансий, который принимает поисковый запрос и, возможно, другие параметры."""

        pass

    @abstractmethod
    def _connect(self) -> None:
        """Приватный метод для подключения к АПИ"""

        pass
