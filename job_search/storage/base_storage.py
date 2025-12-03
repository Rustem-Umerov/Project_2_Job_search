from abc import ABC, abstractmethod
from typing import Optional

from job_search.models.vacancy import Vacancy


class VacancyStorage(ABC):
    """
    Абстрактный базовый класс для хранилищ вакансий.

    Определяет интерфейс для добавления, удаления и получения вакансий.
    Реализации могут использовать разные форматы хранения (JSON, CSV, БД и т.д.),
    но должны соблюдать этот контракт.
    """

    @abstractmethod
    def add_vacancy(self, vacancy: Vacancy) -> bool:
        """
        Добавляет вакансию в хранилище.

        Если вакансия с таким URL уже существует — реализация может игнорировать добавление
        или обновить существующую запись.

        :param vacancy: Объект класса Vacancy, содержащий данные о вакансии.
        """

        pass

    @abstractmethod
    def remove_vacancy(self, url: str) -> bool:
        """
        Удаляет вакансию из хранилища по её URL.

        Если вакансия с указанным URL не найдена — реализация может проигнорировать удаление
        или выбросить исключение.

        :param url: Уникальная ссылка на вакансию.
        """

        pass

    @abstractmethod
    def get_vacancies(self) -> list[Vacancy]:
        """
        Возвращает список всех вакансий из хранилища без фильтрации.
        :return: Список объектов Vacancy.
        """
        pass

    @abstractmethod
    def apply_filter(self, filter_dict: Optional[dict] = None) -> list[Vacancy]:
        """
        Применяет фильтр к вакансиям в хранилище.

        Фильтр — это словарь с ключами, соответствующими атрибутам вакансии
        (например, "currency", "salary_from").

        :param filter_dict: Словарь с условиями фильтрации (опционально).
        :return: Список объектов Vacancy, соответствующих фильтру.
        """
        pass
