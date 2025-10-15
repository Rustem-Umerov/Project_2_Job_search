import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from job_search.filters.vacancy_filter import VacancyFilter, normalize_filter
from job_search.models.vacancy import ALLOWED_FIELDS, Vacancy
from job_search.storage.base_storage import VacancyStorage
from job_search.utils.logger_setup import get_logger

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

    def get_vacancies(self, filter_dict: Optional[dict] = None) -> list[Vacancy]:
        """
        Загружает вакансии из JSON-файла и применяет фильтрацию, если передан фильтр.

        :param filter_dict: Словарь с условиями фильтрации.
        :return: Список объектов Vacancy, соответствующих фильтру.
        """

        try:
            with self._filepath.open("r", encoding="utf-8") as f:
                raw_vacancies = json.load(f)

                if not isinstance(raw_vacancies, list):
                    logger.error("Файл содержит не список, а другой тип данных.")
                    return []

                parsed_vacancies = []
                for v in raw_vacancies:
                    try:
                        parsed_vacancies.append(Vacancy(**v))
                    except TypeError as e:
                        logger.warning(f"Ошибка при создании Vacancy из данных: {e}")
                        continue

                if filter_dict is None:
                    return parsed_vacancies

                if not isinstance(filter_dict, dict):
                    logger.error(f"Фильтр должен быть словарем, а получен {type(filter_dict).__name__}.")
                    return []

                try:
                    normalized_filter = normalize_filter(filter_dict)
                    vacancy_filter = VacancyFilter(normalized_filter)

                except (TypeError, ValueError) as e:
                    logger.error(f"[get_vacancies] Невозможно применить фильтр: {e}")
                    return []

                return [v for v in parsed_vacancies if vacancy_filter.match(v)]

        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Ошибка при чтении файла вакансий: {e}")
            return []

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

        vacancy_url = vacancy.url_vacancy or vacancy.alternate_url

        try:
            list_vacancies = self._load_all()
        except Exception as e:
            logger.exception(f"Ошибка при загрузке списка вакансий: {e}.")
            return False

        if not isinstance(list_vacancies, list):
            logger.error("Формат данных некорректен — ожидался список")
            raise ValueError("Формат файла вакансий некорректен")

        try:
            vacancy_exists = self._exists(vacancy_url)
        except Exception as e:
            logger.exception(f"Ошибка при проверке существования вакансии: {e}")
            return False

        if vacancy_exists:
            try:
                vacancy_dict = self._to_dict(vacancy)
            except Exception as e:
                logger.exception(f"Ошибка при сериализации вакансии для обновления: {e}.")
                return False

            try:
                update_vac = self._update_vacancy(vacancy_url, vacancy_dict)
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
            vac_dict = self._to_dict(vacancy)
        except Exception as e:
            logger.exception(f"Ошибка при сериализации новой вакансии: {e}.")
            return False

        list_vacancies.append(vac_dict)

        try:
            self._save_all(list_vacancies)
            logger.info(f"Добавлена новая вакансия: {vacancy_url}")
            return True
        except Exception as e:
            logger.exception(f"Ошибка при сохранении вакансий после добавления: {e}.")
            return False

    def _update_vacancy(self, url: str, new_data: dict) -> bool:
        """
        Обновляет вакансию по-заданному URL, если есть реальные изменения.
        Фильтрует входные данные, сравнивает с текущими значениями,
        сохраняет обновлённый список и логирует изменения.

        :param url: URL вакансии (может быть url_vacancy или alternate_url)
        :param new_data: Новые данные для обновления (частичный словарь)
        :return: True, если были изменения и они сохранены; False — если нет изменений или вакансия не найдена
        """

        if not isinstance(url, str):
            logger.error(f"Ошибка: URL должен быть строкой. Получено: {type(url).__name__}")
            return False

        normalized_url = url.strip().lower()
        if not normalized_url:
            logger.error("Ошибка: передан пустой или некорректный URL.")
            return False

        if not isinstance(new_data, dict):
            logger.error(f"Ошибка: новые данные должны быть словарём. Получено: {type(new_data).__name__}")
            return False

        try:
            list_vacancies = self._load_all()
        except Exception as e:
            logger.exception(f"Ошибка при загрузке списка вакансий: {e}")
            return False

        if not self._validate_vacancy_list(list_vacancies):
            return False

        index_vac = self._find_vacancy_index(normalized_url, list_vacancies)
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

        try:
            self._save_all(list_vacancies)
            logger.info(f"Обновлена вакансия '{url}': изменены поля {changes_made}")
            logger.debug(f"Обновлённая вакансия: {original_vacancy}")
            return True

        except Exception as e:
            logger.error(f"Ошибка при сохранении вакансии '{url}': {e}")
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

    def _to_dict(self, vacancy: Vacancy) -> dict:
        """
        Преобразует объект Vacancy в словарь по доступным полям из ALLOWED_FIELDS.
        Применяет нормализацию значений, задаёт дефолты для пустых полей
        и корректирует диапазон зарплаты, если from > to.

        :param vacancy: Экземпляр Vacancy для сериализации.
        :return: Словарь с нормализованными данными, готовый для JSON.
        """

        vacancy_dict = {}
        salary_from = None
        salary_to = None

        logger.debug(f"Начало сериализации вакансии: {vacancy}")

        for field_name in ALLOWED_FIELDS:
            obj_vacancy = getattr(vacancy, field_name, None)
            logger.debug(f"Обработка поля '{field_name}': исходное значение = {obj_vacancy!r}")

            if field_name in ("name_vacancy", "url_vacancy", "alternate_url", "currency", "description"):
                if field_name == "description":
                    field_value = self._norm_str(obj_vacancy) or "Описание не указано"
                else:
                    field_value = self._norm_str(obj_vacancy) or ""

            elif field_name == "salary_from":
                salary_from = self._norm_int(obj_vacancy)
                field_value = str(salary_from) if salary_from is not None else ""

            elif field_name == "salary_to":
                salary_to = self._norm_int(obj_vacancy)
                field_value = str(salary_to) if salary_to is not None else ""

            else:
                logger.warning(f"Поле {field_name} не обработано — нет нормализатора")
                continue

            logger.debug(f"Поле '{field_name}': нормализованное значение = {field_value!r}")
            vacancy_dict[field_name] = field_value

        if salary_from is not None and salary_to is not None and salary_from > salary_to:
            logger.warning(
                f"Корректировка диапазона зарплаты: salary_from={salary_from}, salary_to={salary_to} → меняем местами"
            )
            vacancy_dict["salary_from"], vacancy_dict["salary_to"] = str(salary_to), str(salary_from)
            logger.debug(
                f"После корректировки: salary_from={vacancy_dict['salary_from']}, "
                f"salary_to={vacancy_dict['salary_to']}"
            )

        cleaned = {k: v for k, v in vacancy_dict.items() if v is not None}
        logger.debug(f"Результат сериализации: {cleaned}")

        return cleaned

    @staticmethod
    def _norm_str(value: object) -> str | None:
        """Обрезает пробелы, пустое → None."""

        if isinstance(value, str):
            s = value.strip()
            return s or None
        return None

    @staticmethod
    def _norm_int(value: object | int) -> int | None:
        """Преобразует в int, если возможно."""

        if isinstance(value, (str, int)):
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        return None

    def _exists(self, url: str) -> bool:
        """
        Проверяет, существует ли вакансия с указанным URL в хранилище.
        """

        normalized_url = url.strip().lower()

        return any(
            normalized_url == (Vacancy.from_dict(d).url_vacancy or "").strip().lower() for d in self._load_all()
        )

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

    def remove_vacancy(self, url: str) -> bool:
        """
        Удаляет вакансию из хранилища по её URL.
        Возвращает True, если удаление прошло успешно; False — если возникла ошибка или вакансия не найдена.

        :param url: Уникальная ссылка на вакансию.
        :return: Bool — результат удаления.
        """

        if not isinstance(url, str):
            logger.error(f"Ошибка: URL должен быть строкой. Получено: {type(url).__name__}")
            return False

        normalized_url = url.strip().lower()
        if not normalized_url:
            logger.error("Ошибка: передан пустой или некорректный URL.")
            return False

        try:
            list_vacancies = self._load_all()
        except Exception as e:
            logger.exception(f"Ошибка при загрузке списка вакансий: {e}.")
            return False

        if not self._validate_vacancy_list(list_vacancies):
            return False

        index_vac_for_del = self._find_vacancy_index(normalized_url, list_vacancies)
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

    def _find_vacancy_index(self, url: str, list_vacancies: list[dict]) -> Optional[int]:
        """
        Возвращает индекс вакансии с заданным URL (url_vacancy или alternate_url).
        Если не найдено — возвращает None.

        :param url: url вакансии.
        :param list_vacancies: Список вакансий.
        :return: Индекс вакансии или None.
        """

        if not isinstance(url, str):
            logger.error(f"Передан URL некорректного типа: {type(url).__name__}")
            return None

        normalized_url = url.strip().lower()
        if not normalized_url:
            logger.warning("Передан пустой URL для поиска вакансии")
            return None

        if not self._validate_vacancy_list(list_vacancies):
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

    @staticmethod
    def _validate_vacancy_list(data: object) -> bool:
        """
        Проверяет, что data — это непустой список словарей.
        Логирует ошибки при несоответствии.

        :param data: Объект, который должен быть списком вакансий.
        :return: True, если список валиден; False — если нет.
        """

        if not isinstance(data, list):
            logger.error(f"Ожидался список вакансий, но получено: {type(data).__name__}")
            return False

        if not data:
            logger.info("Список вакансий пуст — операция невозможна")
            return False

        if not all(isinstance(v, dict) for v in data):
            logger.warning("Некоторые элементы списка вакансий не являются словарями")
            return False

        return True
