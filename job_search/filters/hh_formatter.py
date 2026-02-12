from math import ceil, floor
from typing import Any, Dict, Optional

from job_search.filters.filter_formatters import BaseFilterFormatter
from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)


class HHFilterFormatter(BaseFilterFormatter):
    """Форматирует фильтры для вакансий HH."""

    def build_from(self, answers: Dict[str, Any]) -> Optional[Dict]:
        """
        Собирает итоговый фильтр вакансий из отдельных блоков:
        salary, keywords, links.

        :param answers: Словарь с исходными данными
        :return: Словарь фильтра или None, если все блоки пусты
        """

        logger.debug("Словарь с сырыми входными данными: %r", answers)

        filter_block: Dict[str, Any] = {}

        # salary block
        try:
            salary_block = self._format_salary_block(answers)
            if salary_block:
                filter_block.update(salary_block)
                logger.info("Добавлен блок salary: %r", salary_block)
            else:
                logger.debug("Блок salary отсутствует или пуст.")
        except Exception as e:
            logger.warning("Ошибка при формировании salary_block: %s", e)

        # keywords block
        try:
            keywords_block = self._format_keywords(answers)
            if keywords_block:
                filter_block.update(keywords_block)
                logger.info("Добавлен блок keywords: %r", keywords_block)
            else:
                logger.debug("Блок keywords отсутствует или пуст.")
        except Exception as e:
            logger.warning("Ошибка при формировании keywords_block: %s", e)

        # links block
        try:
            links_block = self._format_links(answers)
            if links_block:
                filter_block.update(links_block)
                logger.info("Добавлен блок links: %r", links_block)
            else:
                logger.debug("Блок links отсутствует или пуст.")
        except Exception as e:
            logger.warning("Ошибка при формировании links_block: %s", e)

        # Итог
        if not filter_block:
            logger.info("Итоговый фильтр пуст, возвращаем None.")
            return None

        logger.info("Сформированный итоговый фильтр: %r", filter_block)
        return filter_block

    @staticmethod
    def _format_salary_block(answers: Dict[str, Any]) -> Optional[Dict]:
        """
        Форматирует блок зарплаты для HH API.
        Извлекает salary_from, salary_to, currency из answers,
        выполняет валидацию, округление и нормализацию.

        :param answers: Словарь с сырыми данными для фильтра.
        :return: * словарь, где:
                    - ключи: salary_from, salary_to, currency (при условии, что данные поля есть в
                      переданном словаре)
                    - значения: {'оператор сравнения': 'значение'}
                * или None, если блок пуст.
        """

        raw_from = answers.get("salary_from")
        raw_to = answers.get("salary_to")
        raw_currency = answers.get("currency")

        logger.debug("Сырые входные данные по зарплате — от: %r, до: %r, валюта: %r", raw_from, raw_to, raw_currency)

        salary_block: Dict[str, Any] = {}

        salary_from_value: Optional[int] = None
        salary_to_value: Optional[int] = None

        if isinstance(raw_from, (int, float)):
            try:
                salary_from_value = floor(raw_from)
                salary_block["salary_from"] = {"gte": salary_from_value}
                logger.debug("Поле фильтра 'salary_from' успешно обработано: %r", salary_from_value)
            except Exception as e:
                logger.warning("Не удалось обработать salary_from=%r: %s", raw_from, e)

        if isinstance(raw_to, (int, float)):
            try:
                salary_to_value = ceil(raw_to)
                salary_block["salary_to"] = {"lte": salary_to_value}
                logger.debug("Поле фильтра 'salary_to' успешно обработано: %r", salary_to_value)
            except Exception as e:
                logger.warning("Не удалось обработать salary_to=%r: %s", raw_to, e)

        if salary_from_value is not None and salary_to_value is not None and salary_from_value > salary_to_value:
            logger.warning("Минимальная зарплата (%r) больше максимальной (%r)", salary_from_value, salary_to_value)

        if raw_currency is not None:
            if isinstance(raw_currency, str) and raw_currency.strip():
                normalized_currency = raw_currency.strip().upper()
                salary_block["currency"] = {"eq": normalized_currency}
                logger.debug("Поле фильтра 'currency' успешно обработано: %r", normalized_currency)
            else:
                logger.warning("Некорректное значение валюты: %r", raw_currency)

        if not salary_block:
            logger.debug("Блок зарплаты пуст, пропускаем.")
            return None

        logger.info("Сформированный блок зарплаты: %r", salary_block)
        return salary_block

    @staticmethod
    def _format_keywords(answers: Dict[str, Any]) -> Optional[Dict]:
        """
        Форматирует блок ключевых слов для фильтрации вакансий.

        Извлекает contains_name и contains_description из answers,
        выполняет валидацию и нормализацию.

        :param answers: Словарь с сырыми данными для фильтра.
        :return: * словарь, где:
                    - ключи: name_vacancy, description (если заданы)
                    - значения: {оператор сравнения: значение}
                 * или None, если блок пуст.
        """

        raw_name = answers.get("contains_name")
        raw_desc = answers.get("contains_description")

        logger.debug("Сырые входные данные по имени: %r и описанию: %r вакансии.", raw_name, raw_desc)

        keywords_block: Dict[str, Any] = {}

        # Ниже работа с полем name_vacancy
        if isinstance(raw_name, str):
            if raw_name.strip():
                normalized_name = raw_name.strip().lower()
                keywords_block["name_vacancy"] = {"contains": normalized_name}
                logger.debug("Поле фильтра 'name_vacancy' успешно обработано: %r", normalized_name)
            else:
                logger.debug("Поле 'name_vacancy' пустое (состоит из пробелов), пропускаем.")

        elif isinstance(raw_name, (list, tuple, set)):
            raw_names = list(raw_name)
            logger.debug("Сырой список с названиями вакансий: %r", raw_names)

            normalized_names = [name.strip().lower() for name in raw_names if isinstance(name, str) and name.strip()]
            logger.debug("Список с name_vacancy после нормализации: %r", normalized_names)

            if normalized_names:
                keywords_block["name_vacancy"] = {"in": normalized_names}
                logger.debug("Поле фильтра 'name_vacancy' успешно обработано: %r", normalized_names)

            else:
                logger.debug("Список name_vacancy пуст или содержит только пробелы, пропускаем.")

        elif raw_name is None:
            logger.debug("Поле 'name_vacancy' не задано.")

        else:
            logger.warning(
                "Имя вакансии должно быть либо строкой, либо списком/кортежем/множеством, а получено: %s",
                type(raw_name).__name__,
            )

        # Ниже работа с полем description
        if isinstance(raw_desc, str):
            if raw_desc.strip():
                normalized_desc = raw_desc.strip().lower()
                keywords_block["description"] = {"contains": normalized_desc}
                logger.debug("Поле фильтра 'description' успешно обработано: %r", normalized_desc)
            else:
                logger.debug("Поле 'description' пустое (состоит из пробелов), пропускаем.")

        elif raw_desc is None:
            logger.debug("Поле 'description' не задано.")

        else:
            logger.warning("Описание вакансии должно быть строкой, а получено: %s", type(raw_desc).__name__)

        # Итог
        if not keywords_block:
            logger.debug("Блок keywords пуст, пропускаем.")
            return None

        logger.info("Сформированный блок keywords: %r", keywords_block)
        return keywords_block

    @staticmethod
    def _format_links(answers: Dict[str, Any]) -> Optional[Dict]:
        """
        Форматирует блок ссылок для фильтрации вакансий.

        Извлекает url и alternate_url из answers,
        выполняет валидацию и нормализацию.

        :param answers: Словарь с сырыми данными для фильтра.
        :return: * словарь, где:
                    - ключи: url_vacancy, alternate_url (если заданы)
                    - значения: {оператор сравнения: значение}
                 * или None, если блок пуст.
        """

        raw_url = answers.get("url")
        raw_alt = answers.get("alternate_url")

        logger.debug("Сырые входные данные по ссылкам: url=%r, alternate_url=%r", raw_url, raw_alt)

        url_block: Dict[str, Any] = {}

        # Работа с url_vacancy
        if isinstance(raw_url, str):
            if raw_url.strip():
                if raw_url.strip().lower().startswith("http"):
                    normalized_url = raw_url.strip().lower()
                    url_block["url_vacancy"] = {"eq": normalized_url}
                    logger.debug("Поле фильтра 'url_vacancy' успешно обработано: %r", normalized_url)
                else:
                    logger.warning("Ошибка: ссылка url_vacancy имеет неправильный формат: %r", raw_url)
            else:
                logger.debug("Поле 'url_vacancy' пустое (состоит из пробелов), пропускаем.")

        elif isinstance(raw_url, (list, tuple, set)):
            raw_urls = list(raw_url)
            logger.debug("Сырой список ссылок url_vacancy: %r", raw_urls)

            normalized_urls = [
                u.strip().lower()
                for u in raw_urls
                if isinstance(u, str) and u.strip() and u.strip().lower().startswith("http")
            ]
            logger.debug("Список url_vacancy после нормализации: %r", normalized_urls)

            if normalized_urls:
                url_block["url_vacancy"] = {"in": normalized_urls}
                logger.debug("Поле фильтра 'url_vacancy' успешно обработано: %r", normalized_urls)
            else:
                logger.debug("Список url_vacancy пуст или содержит только невалидные элементы, пропускаем.")

        elif raw_alt is None:
            logger.debug("Поле 'url_vacancy' не задано.")

        else:
            logger.warning(
                "Поле 'url_vacancy' должно быть строкой или коллекцией строк, а получено: %s", type(raw_url).__name__
            )

        # Работа с alternate_url
        if isinstance(raw_alt, str):
            if raw_alt.strip():
                if raw_alt.strip().lower().startswith("http"):
                    normalized_alt = raw_alt.strip().lower()
                    url_block["alternate_url"] = {"eq": normalized_alt}
                    logger.debug("Поле фильтра 'alternate_url' успешно обработано: %r", normalized_alt)
                else:
                    logger.warning("Ошибка: ссылка alternate_url имеет неправильный формат: %r", raw_alt)
            else:
                logger.debug("Поле 'alternate_url' пустое (состоит из пробелов), пропускаем.")

        elif isinstance(raw_alt, (list, tuple, set)):
            raw_alts = list(raw_alt)
            logger.debug("Сырой список ссылок alternate_url: %r", raw_alts)

            normalized_alts = [
                u.strip().lower()
                for u in raw_alts
                if isinstance(u, str) and u.strip() and u.strip().lower().startswith("http")
            ]
            logger.debug("Список alternate_url после нормализации: %r", normalized_alts)

            if normalized_alts:
                url_block["alternate_url"] = {"in": normalized_alts}
                logger.debug("Поле фильтра 'alternate_url' успешно обработано: %r", normalized_alts)
            else:
                logger.debug("Список alternate_url пуст или содержит только невалидные элементы, пропускаем.")

        elif raw_alt is None:
            logger.debug("Поле 'alternate_url' не задано.")

        else:
            logger.warning(
                "Поле 'alternate_url' должно быть строкой или коллекцией строк, а получено: %s", type(raw_alt).__name__
            )

        # Итог
        if not url_block:
            logger.debug("Блок ссылок пуст, пропускаем.")
            return None

        logger.info("Сформированный блок ссылок: %r", url_block)
        return url_block
