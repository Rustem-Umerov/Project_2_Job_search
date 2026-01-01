from typing import Any, Mapping, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, RequestException, Timeout
from urllib3.util.retry import Retry

from job_search.api.base_api import VacancyAPI
from job_search.api.types import VacancyResult
from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)


class HeadHunterAPI(VacancyAPI):
    """Класс-наследник от абстрактного класса VacancyAPI.
    Реализует взаимодействие с API hh.ru для получения вакансий."""

    def __init__(self, base_url: str = "https://api.hh.ru", timeout: float = 5.0, max_retries: int = 3) -> None:
        """
        Инициализирует настройки HTTP-клиента.

        Args:
            base_url: Базовый URL API (без завершающего '/').
            timeout: Максимальное время ожидания ответа от сервера (сек).
            max_retries: Число автоматических повторных попыток при сбоях 5xx.
        """

        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = self._init_session(max_retries)

    @staticmethod
    def _init_session(max_retries: int) -> requests.Session:
        """
        Конфигурирует и возвращает requests.Session с политикой ретраев.

        Args:
            max_retries: Сколько раз пытаться повторно при ошибке 500, 502, 503, 504.

        Returns:
            Сессия requests со смонтированными адаптерами для ретраев.
        """

        session = requests.Session()
        retries = Retry(total=max_retries, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504))
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update({"HH-User-Agent": "Project_2_Job_search (rustem.umerov.00@yandex.ru)"})

        return session

    def get_vacancies(self, keyword: str, **kwargs: Any) -> VacancyResult:
        """
        Получает список вакансий по ключевому слову.

        Args:
            keyword (str): Поисковый запрос (обязательный, не может быть пустым).
            **kwargs: Дополнительные параметры:
                - area (int): Регион поиска (по умолчанию 1).
                - per_page (int): Количество вакансий на страницу (по умолчанию 20).
                - page (int): Номер страницы результатов (по умолчанию 0, первая страница).
                - only_with_salary (bool): Исключить вакансии без указания зарплаты.
                - salary (int): Минимальная зарплата для фильтрации.
                - currency (str): Валюта зарплаты (например, "RUR").
                - experience (str): Требуемый опыт работы (значения из справочника hh.ru).
                - employment (str): Тип занятости (например, "full", "part").
                - schedule (str): График работы (например, "remote", "fullDay").
                - search_field (str): Поле поиска (например, "name", "company_name").

        Returns:
            VacancyResult: объект Pydantic‑модели с результатами поиска.

        Raises:
            ValueError: Если keyword пустой.
            RuntimeError: Если в ответе API отсутствует ключ "items" или он не является списком.
        """

        if not keyword.strip():
            logger.error("Пустой keyword передан в get_vacancies")
            raise ValueError("The keyword must not be empty.")

        area = kwargs.pop("area", 1)
        per_page = kwargs.pop("per_page", 20)
        # нормализация per_page, если меньше 0, то 1, если больше 100, то 100
        per_page = min(max(int(per_page), 1), 100)
        page = kwargs.pop("page", 0)

        logger.debug(f"Параметры поиска: keyword='{keyword}', area={area}, per_page={per_page}, page={page}")

        params = {"text": keyword, "area": area, "per_page": per_page, "page": page}

        connect_kwargs = {
            **kwargs,
            "endpoint": "vacancies",
            "params": params,
        }

        logger.info(f"Отправка запроса к API: endpoint='vacancies', params={params}")
        response_data: dict[str, Any] = self._connect(**connect_kwargs)

        items: list[dict[str, Any]] = response_data.get("items", [])
        found: int = response_data.get("found", len(items))
        pages: int = response_data.get("pages", 0)

        if not isinstance(items, list):
            logger.error(f"Некорректный формат 'items' в ответе API: {items}")
            raise RuntimeError("Expected 'items' to be a list in API response")

        logger.info(f"Получено {len(items)} вакансий")
        return VacancyResult(
            vacancies=items, total_count=found, total_pages=pages, page_size=per_page, current_page=page, metadata=None
        )

    def get_all_vacancies(self, keyword: str, **kwargs: Any) -> VacancyResult:
        """
        Метод получает все вакансии по ключевому слову.
        Делает первый запрос, чтобы узнать количество страниц,
        а потом циклом проходит по оставшимся страницам и собирает все вакансии.

        Args:
            keyword (str): Ключевое слово для поиска вакансий.
            **kwargs (Any): Дополнительные параметры запроса (например, регион, опыт).

        Returns:
            VacancyResult: объект Pydantic‑модели с результатами поиска.
        """

        vacancies: list[dict[str, Any]] = []

        # первый запрос, чтобы узнать общее количество страниц
        first_response: VacancyResult = self.get_vacancies(keyword, page=0, per_page=100, **kwargs)
        vacancies.extend(first_response.vacancies)
        pages = first_response.total_pages

        # цикл по остальным страницам
        for page in range(1, pages):
            response = self.get_vacancies(keyword, page=page, per_page=100, **kwargs)
            vacancies.extend(response.vacancies)

        return VacancyResult(
            vacancies=vacancies,
            total_count=len(vacancies),
            total_pages=pages,
            page_size=first_response.page_size,
            current_page=None,
            metadata=None,
        )

    def _build_url(self, endpoint: str) -> str:
        """
        Собирает полный URL на основе базового и endpoint.

        Args:
            endpoint: Путь API без ведущего '/' (например, "vacancies").

        Returns:
            Полная строка URL.
        """

        base = self._base_url.rstrip("/") + "/"
        return urljoin(base, endpoint.lstrip("/"))

    def _connect(self, **kwargs: Any) -> dict[str, Any]:
        """
        Выполняет HTTP GET-запрос к API и возвращает распарсованный JSON-ответ.

        Args:
            **kwargs: Параметры запроса:
                - endpoint (str): Сегмент пути API (например, "vacancies").
                - params (Mapping): Параметры query string.

        Returns:
            dict[str, Any]: Распарсованный JSON-ответ от API.

        Raises:
            ValueError: Если 'endpoint' не является строкой или 'params' не является словарём.
            RequestException: Если произошла ошибка сети, таймаут или получен некорректный HTTP-статус.
            RuntimeError: Если ответ не удалось распарсить как JSON-объект или структура некорректна.
        """

        endpoint = kwargs.get("endpoint")
        params = kwargs.get("params")

        if not isinstance(endpoint, str):
            raise ValueError("Expected 'endpoint' as str in kwargs")

        if params is not None and not isinstance(params, Mapping):
            raise ValueError("Expected 'params' as Mapping[str, Any] or None")

        url = self._build_url(endpoint)

        response: Optional[requests.Response] = None
        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
        except Timeout as e:
            logger.error("hh.ru request timed out: %s", e)
            raise RequestException("Timeout while connecting to hh.ru") from e
        except HTTPError as e:
            status = response.status_code if response is not None else "unknown"
            logger.error("hh.ru returned bad status %s", status)
            raise RequestException(f"hh.ru HTTP {status}") from e
        except RequestException as e:
            logger.error("Error during request to hh.ru: %s", e)
            raise

        try:
            result = response.json()
            if not isinstance(result, dict):
                raise RuntimeError("Expected JSON object from hh.ru")
            if "errors" in result:
                logger.error(f"API вернул ошибки: {result['errors']}")
                raise RuntimeError(f"hh.ru API error: {result['errors']}")
            return result
        except ValueError as e:
            logger.exception("Invalid JSON from hh.ru")
            raise RuntimeError("Failed to parse JSON") from e
