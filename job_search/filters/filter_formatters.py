from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseFilterFormatter(ABC):
    """
    Абстрактный класс для форматирования фильтра под конкретный API.
    """

    @abstractmethod
    def build_from(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Преобразует словарь answers в формат, ожидаемый конкретным API.
        """
        pass
