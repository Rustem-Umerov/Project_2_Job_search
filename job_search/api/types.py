from typing import Any, Optional

from pydantic import BaseModel


class VacancyResult(BaseModel):
    """
    Унифицированный формат результата поиска вакансий.
    Все API‑классы должны возвращать словарь этой структуры.
    """

    # Обязательные поля
    vacancies: list[dict[str, Any]]  # список вакансий
    total_count: int  # общее количество найденных вакансий
    total_pages: int  # количество страниц (0, если API не поддерживает пагинацию)

    # Опциональные поля
    page_size: Optional[int] = None  # количество вакансий на страницу
    current_page: Optional[int] = None  # номер текущей страницы
    metadata: Optional[dict[str, Any]] = None  # специфичные данные API (например, курсоры, лимиты)
