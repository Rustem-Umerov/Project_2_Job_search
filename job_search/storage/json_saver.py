import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from job_search.filters.vacancy_filter import VacancyFilter, normalize_filter
from job_search.models.vacancy import ALLOWED_FIELDS, Vacancy
from job_search.storage.base_storage import VacancyStorage
from job_search.utils.logger_setup import get_logger
from job_search.utils.vacancy_fields_validators import norm_str, validate_list

logger = get_logger(__name__)


class JSONVacancyStorage(VacancyStorage):
    """
    Реализация хранилища вакансий на основе JSON-файла.

    Сохраняет, загружает, обновляет и удаляет вакансии, сериализованные в формате JSON.
    Поддерживает фильтрацию, атомарную запись, проверку целостности данных и защиту от повреждённого файла.

    Хранилище автоматически создаёт файл и директорию при инициализации, если они отсутствуют.
    Имя файла задаётся через конструктор, что позволяет сохранять выборки по разным ключевым словам.
    Все операции логируются, включая ошибки, успешные действия и отладочную информацию.

    Реализует контракт VacancyStorage:
    - add_vacancy: добавляет или обновляет вакансию
    - remove_vacancy: удаляет вакансию по URL
    - get_vacancies: возвращает список вакансий с возможной фильтрацией
    """

    def __init__(self, filename: str = "vacancies.json") -> None:
        """
        Инициализирует хранилище вакансий. Создаёт файл, если он отсутствует.

        :param filename: Имя JSON-файла, в котором будут храниться вакансии.
        """

        base_dir = Path(__file__).resolve().parent
        self._data_dir = base_dir.parent / "data"

        self._filename = filename
        self._filepath = self._data_dir / self._filename
        logger.debug(f"[VacancyStorage] Инициализация хранилища: путь к файлу — {self._filepath}")

        self._prepare_storage()

    def _prepare_storage(self) -> None:
        """
        Проверяет наличие директории и файла. Создаёт их при необходимости.
        """

        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            if not self._filepath.exists() or not self._is_valid_json():
                self._create_file_if_missing()

        except Exception as e:
            logger.error(f"[VacancyStorage] Ошибка при подготовке хранилища: {e}")
            raise

    def _create_file_if_missing(self) -> None:
        """
        Создаёт пустой JSON-файл для хранения вакансий.
        """

        try:
            with self._filepath.open("w", encoding="utf-8") as f:
                json.dump([], f)  # type: ignore[arg-type]
                logger.info(f"[VacancyStorage] JSON-файл: {self._filepath} - успешно создан")
        except IOError as e:
            logger.error(f"[VacancyStorage] Не удалось создать файл {self._filepath}: {e}")
            raise

    def _is_valid_json(self) -> bool:
        """
        Метод для проверки файла, поврежденный или нет.
        Если файл существует, но содержит невалидный JSON — это вызовет ошибку.

        :return: Bool (True/False)
        """

        try:
            with self._filepath.open("r", encoding="utf-8") as f:
                json.load(f)
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def get_vacancies(self) -> list[Vacancy]:
        """
        Загружает вакансии из JSON-файла.

        :return: Список объектов Vacancy.
        """

        try:
            with self._filepath.open("r", encoding="utf-8") as f:
                raw_vacancies = json.load(f)

                if not isinstance(raw_vacancies, list):
                    logger.error("Файл содержит не список, а другой тип данных.")
                    return []

                parsed_vacancies = []
                for idx, v in enumerate(raw_vacancies, start=1):
                    try:
                        parsed_vacancies.append(Vacancy(**v))
                    except TypeError as e:
                        logger.warning("Ошибка при создании Vacancy из записи #%d: %s. Данные: %r", idx, e, v)
                        continue

                return parsed_vacancies

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка при чтении файла вакансий: {e}")
            return []

    def apply_filter(self, filter_dict: Optional[dict] = None) -> list[Vacancy]:
        """
        Применяет фильтр к вакансиям в хранилище.

        Фильтр — это словарь с ключами, соответствующими атрибутам вакансии
        (например, "currency", "salary_from").

        :param filter_dict: Словарь с условиями фильтрации (опционально).
        :return: Список объектов Vacancy, соответствующих фильтру.
        """

        vacancies = self.get_vacancies()
        if not vacancies:
            return []

        if not filter_dict:
            return vacancies

        if not isinstance(filter_dict, dict):
            logger.error(f"Фильтр должен быть словарем, а получен {type(filter_dict).__name__}.")
            return []

        try:
            normalized_filter = normalize_filter(filter_dict)
            vacancy_filter = VacancyFilter(normalized_filter)
        except (TypeError, ValueError) as e:
            logger.error(f"Невозможно применить фильтр: {e}")
            return []

        filtered = [v for v in vacancies if vacancy_filter.match(v)]
        logger.debug(
            "apply_filter: применён фильтр %s, найдено %d вакансий из %d", filter_dict, len(filtered), len(vacancies)
        )
        return filtered

    def safe_load_all(self) -> list:
        """Безопасно загружает список вакансий, возвращает None при ошибке."""

        try:
            return self._load_all()
        except Exception as e:
            logger.exception("Ошибка при загрузке списка вакансий: %s.", e)
            return []

    def safe_save_all(self, list_vacancies: list) -> bool:
        """Безопасно сохраняет список вакансий, возвращает False при ошибке."""

        try:
            self._save_all(list_vacancies)
            return True
        except Exception as e:
            logger.exception("Ошибка при сохранении вакансий: %s", e)
            return False

    def add_vacancy(self, vacancy: Vacancy) -> bool:
        """
        Добавляет новую вакансию или обновляет существующую.
        Возвращает True, если файл был изменён (добавление или обновление),
        False — если изменений не было или возникла ошибка.

        :param vacancy: Объект класса Vacancy.
        """

        if not isinstance(vacancy, Vacancy):
            logger.error(f"Ошибка. Вакансия должна быть объектом класса Vacancy. Получено{type(vacancy).__name__}.")
            raise TypeError("Ошибка. Вакансия должна быть объектом класса Vacancy.")

        if (
            vacancy.url_vacancy is None
            or not vacancy.url_vacancy.strip()
            or vacancy.alternate_url is None
            or not vacancy.alternate_url.strip()
        ):
            logger.error("Ошибка. В вакансии отсутствует url_vacancy и alternate_url")
            raise ValueError("В вакансии отсутствует URL")

        vacancy_url = vacancy.url_vacancy
        vacancy_alternate_url = vacancy.alternate_url

        list_vacancies = self.safe_load_all()
        if not list_vacancies:
            return False

        if not isinstance(list_vacancies, list):
            logger.error("Формат данных некорректен — ожидался список")
            raise ValueError("Формат файла вакансий некорректен")

        try:
            vacancy_exists = self._exists(vacancy_url, vacancy_alternate_url)
        except Exception as e:
            logger.exception(f"Ошибка при проверке существования вакансии: {e}")
            return False

        if vacancy_exists:
            try:
                vacancy_dict = vacancy.to_dict()
            except Exception as e:
                logger.exception(f"Ошибка при сериализации вакансии для обновления: {e}.")
                return False

            try:
                update_vac = self.update_vacancy(vacancy_url, vacancy_dict)
            except Exception as e:
                logger.exception(f"Ошибка при обновлении вакансии: {e}.")
                return False

            if update_vac:
                logger.info(f"Вакансия '{vacancy_url}' обновлена")
                return True
            else:
                logger.info(f"Вакансия '{vacancy_url}' уже актуальна — обновление не требуется")
                return False

        try:
            vac_dict = vacancy.to_dict()
        except Exception as e:
            logger.exception(f"Ошибка при сериализации новой вакансии: {e}.")
            return False

        list_vacancies.append(vac_dict)

        if self.safe_save_all(list_vacancies):
            logger.info(f"Добавлена новая вакансия: {vacancy_url}")
            return True
        return False

    @staticmethod
    def _normalize_url_or_fail(url: str) -> Optional[str]:
        """
        Нормализует URL. Возвращает строку или None, если URL пустой/некорректный.
        """

        normalized_url = norm_str(url, lower=True)
        if not normalized_url:
            logger.warning("Передан пустой URL для поиска вакансии")
            return None
        return normalized_url

    def update_vacancy(self, url: str, new_data: dict) -> bool:
        """
        Обновляет вакансию по-заданному URL, если есть реальные изменения.
        Фильтрует входные данные, сравнивает с текущими значениями,
        сохраняет обновлённый список и логирует изменения.

        :param url: URL вакансии (может быть url_vacancy или alternate_url)
        :param new_data: Новые данные для обновления (частичный словарь)
        :return: True, если были изменения и они сохранены; False — если нет изменений или вакансия не найдена
        """

        normalized_url = self._normalize_url_or_fail(url)
        if not normalized_url:
            return False

        if not isinstance(new_data, dict):
            logger.error(f"Ошибка: новые данные должны быть словарём. Получено: {type(new_data).__name__}")
            return False

        list_vacancies = self.safe_load_all()
        if not list_vacancies:
            return False

        if not validate_list(list_vacancies, dict):
            return False

        index_vac = self.find_vacancy_index(normalized_url, list_vacancies)
        if index_vac is None:
            logger.warning(f"Вакансия с URL '{url}' не найдена")
            return False

        original_vacancy = list_vacancies[index_vac]

        filtered_dict = {
            field_name: value
            for field_name, value in new_data.items()
            if field_name in ALLOWED_FIELDS and value is not None and str(value).strip()
        }

        if not filtered_dict:
            logger.info(f"Нет валидных данных для обновления вакансии '{url}'")
            return False

        changes_made = {}
        for field_name, value in filtered_dict.items():
            if value != original_vacancy.get(field_name):
                original_vacancy[field_name] = value
                changes_made[field_name] = value

        if not changes_made:
            logger.info(f"Нет изменений для вакансии '{url}' — обновление не требуется.")
            return False

        if self.safe_save_all(list_vacancies):
            logger.info(f"Обновлена вакансия '{url}': изменены поля {changes_made}")
            logger.debug(f"Обновлённая вакансия: {original_vacancy}")
            return True
        return False

    def _save_all(self, items: list[dict]) -> None:
        """
        Атомарно сохраняет список словарей в хранилище.
        Использует временный файл и замену, чтобы избежать потери данных.

        :param items: Список словарей, который ты хочешь сохранить.
        """

        temp_path = self._filepath.with_suffix(".tmp")

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)  # type: ignore

            os.replace(temp_path, self._filepath)

            logger.info(
                f"Сохранено {len(items)} записей в файл '{self._filepath}'. "
                f"Размер: {os.path.getsize(self._filepath)} байт. "
                f"Время: {datetime.now().isoformat()}"
            )

        except Exception as e:
            logger.exception(f"Ошибка при сохранении данных: {e}")
            raise

    def save(self, items: list[dict]) -> None:
        """
        Публичный метод: сохраняет список вакансий в файл (атомарно).
        Вызывается из контроллера.
        """

        self._save_all(items)

    def clear(self) -> None:
        """
        Полностью очищает хранилище вакансий.
        """

        self._save_all([])
        logger.info("Хранилище вакансий очищено.")

    def _exists(self, url: str, alternate_url: str) -> bool:
        """
        Проверяет, существует ли вакансия с указанным URL или alternate_url в хранилище.
        Работает даже если ссылки перепутаны между полями.

        :param url: Основная ссылка на вакансию
        :param alternate_url: Альтернативная ссылка на вакансию
        :return: True, если вакансия существует, иначе False
        """

        list_vacancies = self._load_all()
        if not validate_list(list_vacancies, dict):
            return False

        # Проверяем основную ссылку
        if url and self.find_vacancy_index(url, list_vacancies) is not None:
            return True

        # Проверяем альтернативную ссылку
        if alternate_url and self.find_vacancy_index(alternate_url, list_vacancies) is not None:
            return True

        return False

    def _load_all(self) -> list[dict]:
        """
        Загружает список вакансий из JSON-файла.
        Гарантирует возврат list[dict], даже при ошибке чтения или повреждённом формате.
        """

        try:
            with self._filepath.open("r", encoding="utf-8") as f:
                data = json.load(f)

                if isinstance(data, list):
                    logger.debug(f"Загружено {len(data)} вакансий из файла {self._filepath}")
                    return data

                logger.error(f"Ошибка. Ожидался список, но получен {type(data).__name__} в файле {self._filepath}.")
                return []

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка при чтении файла {self._filepath}: {e}.")
            return []

    def load(self) -> list[dict]:
        """
        Публичный метод: загружает список вакансий из файла.
        Возвращает list[dict], даже если файл пустой или повреждён.
        """

        return self._load_all()

    def is_empty(self) -> bool:
        """
        Проверяет, пустое ли хранилище вакансий.
        :return: True, если вакансий нет; False — если есть.
        """

        return len(self._load_all()) == 0

    def count(self) -> int:
        """
        Возвращает количество вакансий в хранилище.
        :return: Количество вакансий (int).
        """

        return len(self._load_all())

    def remove_vacancy(self, url: str) -> bool:
        """
        Удаляет вакансию из хранилища по её URL.
        Возвращает True, если удаление прошло успешно; False — если возникла ошибка или вакансия не найдена.

        :param url: Уникальная ссылка на вакансию.
        :return: Bool — результат удаления.
        """

        normalized_url = self._normalize_url_or_fail(url)
        if not normalized_url:
            return False

        list_vacancies = self.safe_load_all()
        if not list_vacancies:
            return False

        if not validate_list(list_vacancies, dict):
            return False

        index_vac_for_del = self.find_vacancy_index(normalized_url, list_vacancies)
        if index_vac_for_del is None:
            logger.warning(f"Вакансия с URL '{url}' не найдена")
            return False

        removed_element = list_vacancies.pop(index_vac_for_del)
        logger.info(f"Вакансия '{url}' удалена из хранилища")
        logger.debug(f"Вакансия: '{removed_element}' удалена из хранилища")

        try:
            self._save_all(list_vacancies)
            return True

        except Exception as e:
            logger.exception(f"Ошибка при сохранений вакансий: {e}.")
            return False

    @staticmethod
    def find_vacancy_index(url: str, list_vacancies: list[dict]) -> Optional[int]:
        """
        Возвращает индекс вакансии с заданным URL (url_vacancy или alternate_url).
        Если не найдено — возвращает None.

        :param url: url вакансии.
        :param list_vacancies: Список вакансий.
        :return: Индекс вакансии или None.
        """

        normalized_url = norm_str(url, lower=True)
        if not normalized_url:
            logger.warning("Передан пустой URL для поиска вакансии")
            return None

        if not validate_list(list_vacancies, dict):
            return None

        logger.debug(f"Начат поиск вакансии по URL: '{normalized_url}'")
        logger.debug(f"Список содержит {len(list_vacancies)} вакансий для поиска")

        for index, dict_vac in enumerate(list_vacancies):
            url_vac = str(dict_vac.get("url_vacancy", "")).strip().lower()
            alt_url = str(dict_vac.get("alternate_url", "")).strip().lower()

            if normalized_url in (url_vac, alt_url):
                logger.debug(f"Найдена вакансия по URL '{url}' на позиции {index}")
                return index

        logger.info(f"Вакансия с URL '{url}' не найдена")
        return None

    def get_by_url(self, url: str) -> Optional[Vacancy]:
        """
        Возвращает вакансию по её URL (url_vacancy или alternate_url).
        Если данные повреждены или невалидны — логирует ошибку и возвращает None.

        :param url: Уникальный URL вакансии.
        :return: Объект Vacancy или None, если не найдено.
        """

        normalized_url = norm_str(url, lower=True)
        if not normalized_url:
            logger.warning("Передан пустой URL для поиска вакансии")
            return None

        list_vacancies = self._load_all()
        vac_idx = self.find_vacancy_index(normalized_url, list_vacancies)
        if vac_idx is None:
            logger.info("Вакансия не найдена.")
            return None

        vacancy = list_vacancies[vac_idx]
        logger.debug("Вакансия найдена. Индекс: %s Данные: %s.", vac_idx, vacancy)
        try:
            return Vacancy(**vacancy)
        except (TypeError, ValueError) as e:
            logger.warning("get_by_url: не удалось создать Vacancy из %s: %s", vacancy, e)
            return None
