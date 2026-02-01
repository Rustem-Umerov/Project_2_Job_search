from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)


class FilterPreviewRenderer:
    """
    Отвечает за формирование и вывод человекочитаемого обзора собранных параметров фильтра.
    Получает словарь ответов пользователя и абстракцию ввода/вывода.
    """

    def __init__(self, answers: dict, io: dict) -> None:
        """
        Инициализирует данные фильтра и механизм вывода информации.

        :param answers: Словарь с параметрами фильтра, собранными от пользователя.
        :param io: Словарь с функциями ввода/вывода. Обычно содержит {'input': input, 'output': print}.
        """

        # Сырые ответы пользователя.
        self._answers: dict = answers
        # Абстракция ввода/вывода.
        self._io = io

    def _salary_preview(self) -> str:
        """Формирует человекочитаемую строку о зарплате."""

        salary_from = self._answers.get("salary_from")
        salary_to = self._answers.get("salary_to")
        currency = self._answers.get("currency")

        logger.debug(
            "Формирование обзора зарплаты: salary_from=%s, salary_to=%s, currency=%s", salary_from, salary_to, currency
        )

        parts = []
        if salary_from is not None and salary_to is not None:
            parts.append(f"от {salary_from} до {salary_to}")
        elif salary_from is not None:
            parts.append(f"от {salary_from}")
        elif salary_to is not None:
            parts.append(f"до {salary_to}")

        if parts and currency:
            parts.append(f"в валюте {currency}")

        preview = f"💰 Зарплата: {' '.join(parts)}" if parts else ""
        logger.info("Обзор зарплаты сформирован: '%s'", preview)
        return preview

    def _contains_preview(self) -> str:
        """Формирует человекочитаемую строку о ключевых словах в названии и описании."""

        contains_description = self._answers.get("contains_description")
        contains_name = self._answers.get("contains_name")

        logger.debug(
            "Формирование обзора ключевых слов: contains_name=%s, contains_description=%s",
            contains_name,
            contains_description,
        )

        parts = []
        if contains_name:
            parts.append(f"🔍 Название содержит: {contains_name}")
        if contains_description:
            parts.append(f"📝 Описание содержит: {contains_description}")

        preview = "\n".join(parts)
        logger.info("Обзор ключевых слов сформирован: '%s'", preview)
        return preview

    def _url_contains_preview(self) -> None:
        """Выводит ссылки, если они заданы."""

        url = self._answers.get("url")
        logger.debug("Формирование обзора ссылок: url=%s", url)

        if not url:
            logger.info("Ссылки не заданы — блок ссылок не будет отображён.")
            return

        if isinstance(url, str):
            logger.info("Выведена одиночная ссылка: %s", url)
            self._io["output"](f"🔗 Ссылка: {url}")

        if isinstance(url, list):
            logger.info("Выведен список ссылок: %s", url)
            self._io["output"]("🔗 Ссылки:")
            for u in url:
                self._io["output"](f"- {u}")

    def _alternate_url_preview(self) -> None:
        """Выводит альтернативные ссылки, если они заданы."""

        alternate_url = self._answers.get("alternate_url")
        logger.debug("Формирование обзора альтернативных ссылок: alternate_url=%s", alternate_url)

        if not alternate_url:
            logger.info("Альтернативные ссылки не заданы — блок alternate URL не будет отображён.")
            return

        if isinstance(alternate_url, str):
            logger.info("Выведена одиночная альтернативная ссылка: %s", alternate_url)
            self._io["output"](f"🔁 Альтернативная ссылка: {alternate_url}")

        if isinstance(alternate_url, list):
            logger.info("Выведен список альтернативных ссылок: %s", alternate_url)
            self._io["output"]("🔁 Альтернативные ссылки:")
            for alt_u in alternate_url:
                self._io["output"](f"- {alt_u}")

    def render(self) -> None:
        """Выводит человекочитаемый обзор собранных фильтров."""

        logger.info("Начат рендер предварительного обзора фильтра.")

        self._io["output"]("")
        self._io["output"]("📋 Предварительный обзор фильтра:")
        self._io["output"]("")

        if not any(value is not None for value in self._answers.values()):
            logger.info("Фильтр пуст — ни один параметр не задан.")
            self._io["output"]("Фильтр пока не задан. Вы можете вернуться и указать параметры.")
            return

        salary_info = self._salary_preview()
        contains_info = self._contains_preview()

        if salary_info:
            logger.info("Выведен блок зарплаты.")
            self._io["output"](salary_info)
        else:
            logger.info("Блок зарплаты не выведен — параметры не заданы.")

        if contains_info:
            logger.info("Выведен блок ключевых слов.")
            self._io["output"](contains_info)
        else:
            logger.info("Блок ключевых слов не выведен — параметры не заданы.")

        self._url_contains_preview()
        self._alternate_url_preview()

        logger.info("Рендер фильтра завершён.")
