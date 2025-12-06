from typing import Any, Mapping, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, RequestException, Timeout
from urllib3.util.retry import Retry

from job_search.api.base_api import VacancyAPI
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

        return session

    def get_vacancies(self, keyword: str, **kwargs: Any) -> list[dict[str, Any]]:
        """
        Получает список вакансий по ключевому слову.

        Args:
            keyword (str): Поисковый запрос (обязательный, не может быть пустым).
            **kwargs: Дополнительные параметры:
                - area (int): Регион поиска (по умолчанию 1).
                - per_page (int): Количество вакансий на страницу (по умолчанию 20).

        Returns:
            list[dict[str, Any]]: Список вакансий.

        Raises:
            ValueError: Если keyword пустой.
            RuntimeError: Если в ответе API отсутствует ключ "items" или он не является списком.
        """
        if not keyword.strip():
            logger.error("Пустой keyword передан в get_vacancies")
            raise ValueError("The keyword must not be empty.")

        area = kwargs.pop("area", 1)
        per_page = kwargs.pop("per_page", 20)

        logger.debug(f"Параметры поиска: keyword='{keyword}', area={area}, per_page={per_page}")

        params = {"text": keyword, "area": area, "per_page": per_page}

        connect_kwargs = {
            **kwargs,
            "endpoint": "vacancies",
            "params": params,
        }

        logger.info(f"Отправка запроса к API: endpoint='vacancies', params={params}")
        response_data: dict[str, Any] = self._connect(**connect_kwargs)

        items: Optional[list[dict[str, Any]]] = response_data.get("items")

        if not isinstance(items, list):
            logger.error(f"Некорректный формат 'items' в ответе API: {items}")
            raise RuntimeError("Expected 'items' to be a list in API response")

        logger.info(f"Получено {len(items)} вакансий")
        return items

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
            return result
        except ValueError as e:
            logger.exception("Invalid JSON from hh.ru")
            raise RuntimeError("Failed to parse JSON") from e
