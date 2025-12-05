from __future__ import annotations

from collections import ChainMap
from typing import Any, Callable, Literal, Optional, overload

from job_search.api.head_hunter_api import HeadHunterAPI
from job_search.filters.hh_formatter import HHFilterFormatter
from job_search.filters.interactive_input import ALLOWED_CURRENCIES, InteractiveFilterInput
from job_search.filters.preview_renderer import FilterPreviewRenderer
from job_search.models.vacancy import Vacancy
from job_search.storage.json_saver import JSONVacancyStorage
from job_search.utils.exceptions import FilterCancelled
from job_search.utils.filters import get_top_n_vacancies, sort_by_salary
from job_search.utils.input_helpers import (
    ask_choice,
    ask_int,
    ask_yes_no,
    next_step,
    render_menu,
    render_vacancies_page,
)
from job_search.utils.logger_setup import get_logger
from job_search.utils.vacancy_fields_validators import (
    norm_str,
    validate_currency,
    validate_list,
    validate_salary,
    validate_url,
)

logger = get_logger(__name__)

DEFAULT_RESULTS_COUNT = 10


class JobSearchApp:
    """
    Класс-контроллер приложения (state machine), который управляет сценарием взаимодействия с пользователем.
    Он не реализует бизнес‑логику сам, а координирует работу других классов:
    API‑клиентов, фильтров, сортировщиков, хранилища.
    """

    def __init__(self, io: dict[str, Callable] | None = None) -> None:
        """Инициализирует состояние приложения и подключает необходимые сервисы."""

        # Абстракция ввода/вывода
        self._io: dict[str, Callable[[str], str]] = io or {"input": input, "output": print}

        # Текущее состояние сценария (используется для управления шагами)
        self.current_step = "main_menu"

        # Выбранный API-клиент (например, HHAPI), будет установлен после выбора пользователем
        self.selected_api = None

        # Список вакансий, полученных из API или архива (объекты Vacancy)
        self.vacancies: list[Vacancy] = []

        # Общее количество найденных
        self.total_vacancies: int = 0

        # Сколько показываем за раз
        self.page_size: int = DEFAULT_RESULTS_COUNT

        # Текущая страница (начинаем с 1)
        self.current_page: int = 1

        # Параметры фильтра, собранные через InteractiveFilterInput
        self.filter: dict = {}

        # Хранилище вакансий на основе JSON-файла
        self.json_storage = JSONVacancyStorage("vacancies.json")

        # Флаг, управляющий основным циклом приложения
        self.running = True

        # Сценарий взаимодействия с пользователем
        self.steps = self.build_steps()

        # История шагов
        self.history: list[str] = []

        # Реестр доступных API-клиентов
        self.api_registry = self.build_api_registry()

        # Вакансия для сохранения в архив (объект класса Vacancy)
        self.current_vacancy: Optional[Vacancy] = None

        # Атрибуты для операций с архивом (удаление/редактирование/обновление)
        self.storage_vacancies: list[dict] = []  # список вакансий из архива
        self.vacancy_idx: int | None = None  # индекс выбранной вакансии
        self.vacancy_new_data: dict = {}  # словарь с обновленными данными
        self.old_url: str | None = None  # старый url, если для обновления данных (если url был обновлен)

    def build_steps(self) -> dict[str, Callable[[], Optional[str]]]:
        """
        Метод возвращает словарь, где описаны все шаги приложения.
        Словарь, где ключ - состояние программы, а значение - метод класса.
        """

        return {
            # Главное меню
            "main_menu": self.step_main_menu,
            # Работа с API
            "search": self.step_search,
            "choose_api": self.step_choose_api,
            "preview": self.step_preview,
            "show_results": self.step_show_results,
            "next_show_results": self.step_next_show_results,
            "prev_show_results": self.step_prev_show_results,
            "show_details": self.step_show_details,  # просмотр подробностей одной вакансии
            # Работа с локальным архивом (JSONVacancyStorage)
            "filter": self.step_filter,
            "storage_add_from_results": self.step_storage_add_from_results,
            "storage_menu": self.step_storage_menu,
            "storage_entry": self.step_storage_entry,
            "storage_add": self.step_storage_add,
            "storage_update": self.step_storage_update,
            "storage_remove": self.step_storage_remove,
            "apply_filter": self.step_apply_filter,
            "storage_remove_confirm": self.step_storage_remove_confirm,
            "storage_update_edit": self.step_storage_update_edit,
            "storage_update_save": self.step_storage_update_save,
        }

    @staticmethod
    def build_api_registry() -> dict[str, type]:
        """
        Формирует и возвращает реестр доступных API-клиентов.

        Возвращает:
            dict[str, type]: Словарь вида {<название API>: <класс клиента>},
            где ключ используется в меню выбора API, а значение — класс,
            который будет инициализирован при выборе пользователем.
        """

        return {
            "HeadHunter": HeadHunterAPI,
        }

    def run(self) -> None:
        """Главный цикл приложения: вызывает шаги и обрабатывает их результат."""

        logger.info("Запуск приложения")
        self.running = True
        self.current_step = "main_menu"

        while self.running:
            logger.debug(f"Текущий шаг: {self.current_step}")

            step_func = self.steps.get(self.current_step)
            if not step_func:
                logger.error(f"Неизвестный шаг: {self.current_step}")
                self._io["output"](f"Неизвестный шаг: {self.current_step}")
                self.current_step = "main_menu"
                continue

            try:
                step_result = step_func()
                logger.debug(f"Шаг {self.current_step} вернул: {step_result}")
            except Exception as e:
                logger.exception(f"Ошибка при выполнении шага {self.current_step}: {e}")
                self.current_step = "main_menu"
                continue

            if step_result == "exit":
                logger.info("Пользователь выбрал выход")
                self._io["output"]("Сохраняем данные и завершаем работу...")
                try:
                    dicts_to_save = [vac.to_dict() for vac in self.vacancies]
                    self.json_storage.save(dicts_to_save)
                    logger.info("Данные успешно сохранены")
                except Exception as e:
                    logger.exception(f"Ошибка при сохранении данных: {e}")
                self.running = False

            elif step_result == "back":
                logger.info("Пользователь хочет вернуться на шаг назад")
                if self.history:
                    self.current_step = self.history.pop()  # возвращаемся к предыдущему шагу
                    logger.info(f"Возврат на шаг назад → {self.current_step}")
                else:
                    self.current_step = "main_menu"
                    logger.info("История пуста, возврат в главное меню")

            elif isinstance(step_result, str):
                if step_result not in self.steps:
                    logger.warning(f"Неизвестный шаг {step_result}, возврат в main_menu")
                    self.current_step = "main_menu"
                else:
                    logger.info(f"Переход к следующему шагу: {step_result}")
                    self.history.append(self.current_step)
                    self.current_step = step_result

            else:
                logger.warning(
                    f"Шаг {self.current_step} вернул некорректное значение ({type(step_result)}): {step_result}"
                )
                self.current_step = "main_menu"

        logger.info("Приложение завершено")

    def step_main_menu(self) -> str:
        """
        Главное меню: показывает список действий и возвращает имя выбранного шага.
        Возвращает 'exit', если пользователь выбрал выход.
        """

        menu = {
            1: ("Поиск вакансий по API", "choose_api"),
            2: ("Работа с архивом", "storage_menu"),
            3: ("Фильтрация", "filter"),
            4: ("Выход", "exit"),
        }

        logger.debug("Отображение главного меню")
        self._io["output"]("Список возможных действий:\n")

        return self._menu_loop(menu, "main_menu")

    @overload
    def _menu_loop(
        self,
        menu: dict[int, tuple[str, tuple[Literal["keyword", "command"], str]]],
        step_name: str,
        *,
        return_tuple: Literal[True],
    ) -> tuple[Literal["keyword", "command"], str]: ...
    @overload
    def _menu_loop(self, menu: dict, step_name: str, *, return_tuple: Literal[False] = False) -> str: ...
    @overload
    def _menu_loop(self, menu: dict, step_name: str, *, return_tuple: Literal[True]) -> tuple[str, str]: ...

    def _menu_loop(
        self, menu: dict[int, tuple[str, Any]], step_name: str, *, return_tuple: bool = False
    ) -> str | tuple:
        """
        Отображает меню и запускает цикл выбора пункта.

        - С помощью render_menu выводит меню в консоль.
        - С помощью ask_choice получает выбор пользователя.
        - Если ask_choice вернул None, возвращает текущий шаг (step_name).
        - Если return_tuple=True, возвращает кортеж (title, step_name) из меню.
        - Если return_tuple=False, возвращает название следующего шага через next_step.

        :param menu: Словарь с пунктами меню {номер: (название, значение)}.
        :param step_name: Название шага, если выбор не был сделан.
        :param return_tuple: Флаг — вернуть кортеж вместо шага.
        :return: Название следующего шага (str) или кортеж (title, step_name).
        """

        render_menu(io=self._io, menu=menu)
        choice = ask_choice(self._io, menu)

        # Условие если ask_choice по ошибке вернул None
        if choice is None:
            if return_tuple:
                return None, step_name
            logger.info("ask_choice вернул None → возврат к шагу '%s'", step_name)
            return step_name

        if return_tuple:
            return menu[choice]  # title, step_name
        return next_step(io=self._io, menu=menu, choice=choice)

    def step_choose_api(self) -> Optional[str]:
        """
        Меню выбора API для поиска вакансий.
        Сохраняет выбранный API-клиент и возвращает имя следующего шага.
        """

        menu: dict[int, tuple[str, str]] = {
            1: ("HeadHunter", "search"),
            2: ("Вернуться на предыдущий шаг", "back"),
            3: ("Выход", "exit"),
        }

        logger.debug("Отображение меню выбора API")

        while True:
            self._io["output"]("Список возможных действий:\n")
            title, step_name = self._menu_loop(menu, "", return_tuple=True)
            if title is None:
                continue

            # Инициализация API-клиента при выборе HeadHunter
            client_cls = self.api_registry.get(title)
            if client_cls:
                self.selected_api = client_cls()
                logger.info(f"Выбран API: {title}")

            return step_name

    def step_search(self) -> Optional[str]:
        """
        Выполняет поиск вакансий через выбранный API.
        - Спрашивает ключевое слово и опциональные параметры (area, per_page).
        - Делает запрос к API.
        - Сохраняет результаты в self.vacancies.
        - Возвращает имя следующего шага: "show_results", "search", "main_menu" или "choose_api".
        """

        if not self.selected_api:
            self._io["output"]("Ошибка: АПИ не выбран. Программа вернется к выбору АПИ.")
            logger.info("Ошибка: АПИ не выбран. Программа вернется к выбору АПИ.")
            return "choose_api"

        # Ключевое слово
        status, value = self._check_keyword_or_command(self._ask_keyword())
        if status == "command":
            return value

        params = {"text": value}

        # Регион
        region = self._ask_int_param("регион поиска")
        if region is not None:
            params["area"] = region

        # Количество вакансий на страницу
        per_page = self._ask_int_param("количество вакансий на страницу")
        if per_page is not None:
            params["per_page"] = per_page

        # Вызов API
        try:
            raw_vacancies = self.selected_api.get_vacancies(params)
            self.vacancies = Vacancy.from_list(raw_vacancies)
            self.total_vacancies = len(self.vacancies)
            logger.info(f"Запрос к API выполнен, найдено {self.total_vacancies} вакансий")
        except (OSError, ValueError, TypeError) as e:
            logger.error(f"Ошибка при вызове API: {e}")
            self._io["output"]("Произошла ошибка при обращении к API. Попробуйте позже.")
            return "main_menu"

        # Обработка результата
        if self.vacancies:
            self.page_size = params.get("per_page", DEFAULT_RESULTS_COUNT)
            self.current_page = 1
            self._io["output"](f"Найдено {self.total_vacancies} вакансий. Сейчас покажу результат...")
            logger.debug(f"Найдено {self.total_vacancies} вакансий.")
            return "show_results"

        else:
            self._io["output"]("Ничего не найдено.")
            logger.info("Программа спрашивает у пользователя: Хотите попробовать ещё раз?")
            again = ask_yes_no(self._io, "Хотите попробовать ещё раз? (да/нет): ")
            if again:
                logger.info("Пользователь выбрал повтор поиска")
                return "search"
            logger.info("Пользователь отказался от повтора, возврат в main_menu")
            return "main_menu"

    def _ask_int_param(self, question: str) -> Optional[int]:
        """
        Запрашивает у пользователя числовой параметр (например, регион поиска или количество вакансий на страницу).

        - Сначала уточняет, хочет ли пользователь задать этот параметр.
        - Если пользователь соглашается, запрашивает число.
        - Если пользователь вводит 'отмена' или отказывается, возвращает None.

        :param question: Текстовое описание параметра (например, "регион поиска").
        :return: Целое число, введённое пользователем, или None.
        """

        logger.debug("Программа спрашивает у пользователя: Хотите указать %s.", question)
        if ask_yes_no(self._io, f"Хотите указать {question}? (да/нет): "):
            value = ask_int(self._io, f"Введите {question} (или 'отмена'): ")
            if value is not None:
                logger.info("Пользователь выбран %s = %s", question, value)
                return value
            logger.debug("Пользователь отказался вводить %s.", question)
        else:
            logger.debug("Пользователь отказался вводить %s.", question)
        return None

    def _ask_keyword(self) -> Optional[str]:
        """
        Запрашивает у пользователя ключевое слово для поиска.

        - Повторяет ввод, если строка пустая или состоит из пробелов.
        - Возвращает нормализованное ключевое слово (строка в нижнем регистре).
        - Никогда не возвращает None: результат всегда валидная строка.
        """

        while True:
            logger.debug("Программа спрашивает у пользователя ключевое слово.")
            keyword: str = self._io["input"]("Введите ключевое слово для поиска: -->").strip().lower()
            if not keyword:
                logger.warning("Ошибка: ключевое слово пустое или состоит из пробельных символов.")
                self._io["output"]("Ключевое слово состоит из пробельных символов. Повторите попытку.")
                continue

            logger.info(f"Пользователь ввел ключевое слово = '{keyword}'")
            return keyword

    def _check_keyword_or_command(self, keyword: str) -> tuple[Literal["keyword", "command"], str]:
        """
        Проверяет, является ли введённое слово специальной командой или ключевым словом.

        - Если слово совпадает с одной из команд ("exit", "выход", "back", "назад"),
          вызывает confirm_special_keyword для уточнения.
        - Возвращает кортеж:
            ("command", <значение>) — если пользователь подтвердил действие команды.
            ("keyword", <слово>) — если пользователь подтвердил, что это ключевое слово.
        """

        commands = {
            "exit": ("завершить приложение", "exit"),
            "выход": ("завершить приложение", "exit"),
            "back": ("вернуться на предыдущий шаг", "back"),
            "назад": ("вернуться на предыдущий шаг", "back"),
        }

        if keyword in commands:
            status, value = self.confirm_special_keyword(keyword, *commands[keyword])
            return status, value

        return "keyword", keyword

    def confirm_special_keyword(
        self, word: str, action: str, return_value: str
    ) -> tuple[Literal["keyword", "command"], str]:
        """
        Уточняет у пользователя, является ли введённое слово ключевым словом или командой.

        :param word: Исходное слово, введённое пользователем (например, "exit", "back").
        :param action: Описание действия для команды (например, "завершить приложение").
        :param return_value: Строка, обозначающая команду ("exit" или "back").

        :return: Кортеж (status, value), где:
            ("keyword", word) — если пользователь подтвердил, что это ключевое слово.
            ("command", return_value) — если пользователь выбрал действие команды.
        """

        while True:
            self._io["output"](f"Вы ввели слово: '{word}'.")
            self._io["output"](f"Это ключевое слово или вы хотите {action}?")
            options: dict[int, tuple[str, tuple[Literal["keyword", "command"], str]]] = {
                1: ("Ключевое слово", ("keyword", word)),
                2: (action.capitalize(), ("command", return_value)),
            }

            status, value = self._menu_loop(options, "", return_tuple=True)
            if status is None:
                continue

            logger.info(
                f"Пользователь подтвердил '{word}' как ключевое слово"
                if status == "keyword"
                else f"Пользователь выбрал действие: {value}"
            )

            return status, value

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_show_results(self) -> str:
        """Показ результатов поиска с поддержкой пагинации и меню действий."""

        if not self.vacancies:
            self._io["output"]("Ошибка: список вакансии пуст. Программа вернется в главное меню.")
            logger.warning("Ошибка: список вакансии пуст. Программа вернется в главное меню.")
            return "main_menu"

        while True:
            # Вывод вакансий текущей страницы
            start, end = render_vacancies_page(
                io=self._io,
                vacancies=self.vacancies,
                current_page=self.current_page,
                page_size=self.page_size,
                total_vacancies=self.total_vacancies,
            )

            self._io["output"](f"Вы видели {end} из {self.total_vacancies} вакансий. Что хотите сделать дальше?")
            self._io["output"]("")
            self._io["output"]("Список возможных действий:")

            menu = {
                1: ("Посмотреть подробности вакансии (по номеру)", "show_details"),
                2: ("Сохранить вакансию (добавить в архив/избранное)", "storage_add_from_results"),
                3: ("Показать следующую страницу", "next_show_results"),
                4: ("Показать предыдущую страницу", "prev_show_results"),
                5: ("Повторить поиск", "search"),
                6: ("В главное меню", "main_menu"),
                7: ("Вернуться на предыдущий шаг", "back"),
                8: ("Выход", "exit"),
            }

            step = self._menu_loop(menu, "")
            if step == "":
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_next_show_results(self) -> str:
        """Переход на следующую страницу результатов."""

        if self.current_page * self.page_size < self.total_vacancies:
            self.current_page += 1
            logger.info(f"Переход на следующую страницу: {self.current_page}")
        else:
            self._io["output"]("Вы уже просмотрели все вакансии.")
            logger.info("Попытка перейти на следующую страницу, но вакансии закончились.")
        return "show_results"

    def step_prev_show_results(self) -> str:
        """Переход на предыдущую страницу результатов."""

        if self.current_page > 1:
            self.current_page -= 1
            logger.info(f"Возврат на предыдущую страницу: {self.current_page}")
        else:
            self._io["output"]("Вы уже на первой странице.")
            logger.info("Попытка вернуться назад с первой страницы.")
        return "show_results"

    def step_show_details(self) -> str:
        """Показ подробностей выбранной вакансии и меню действий."""

        logger.debug("Шаг 'show_details' запущен")

        # 1. Отображение текущей страницы
        self._io["output"]("Вы остановились на этой странице:")
        start, end = render_vacancies_page(
            io=self._io,
            vacancies=self.vacancies,
            current_page=self.current_page,
            page_size=self.page_size,
            total_vacancies=self.total_vacancies,
        )

        # 2. Запрос номера вакансии
        vacancy_num = ask_int(
            self._io,
            "Введите номер вакансии, подробности которой хотите посмотреть (или 'отмена'): --> ",
            min_value=start + 1,
            max_value=end,
        )
        logger.debug(f"Результат ввода номера вакансии: {vacancy_num}")

        if vacancy_num is None:
            logger.info("Пользователь отменил ввод номера вакансии → возврат 'back'")
            return "back"

        vacancy_idx = vacancy_num - 1
        logger.debug(f"Преобразованный индекс вакансии: {vacancy_idx}")

        # Получение и вывод деталей вакансии
        vacancy = self.vacancies[vacancy_idx]
        self.current_vacancy = vacancy
        logger.info(f"Показ деталей вакансии №{vacancy_num} (индекс {vacancy_idx})")
        self._io["output"](vacancy.details())
        self._io["output"]("")

        while True:
            # Меню действий
            menu = {
                1: ("Сохранить вакансию (в архив/избранное)", "storage_add"),
                2: ("Вернуться к списку результатов", "show_results"),
                3: ("Вернуться в главное меню", "main_menu"),
                4: ("Выход", "exit"),
            }
            logger.debug(f"Сформировано меню действий: {list(menu.keys())}")

            self._io["output"]("")
            self._io["output"](f"Вы просмотрели вакансию №{vacancy_num}. " f"Что хотите сделать дальше?")
            self._io["output"]("")
            self._io["output"]("Список возможных действий:")

            step = self._menu_loop(menu, "")
            if step == "":
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_filter(self) -> str:
        """Запускает процесс настройки фильтра вакансий."""

        logger.debug("Шаг настройки фильтра запущен.")
        self._io["output"]("Сейчас начнётся сбор фильтра.")

        try:
            # Создаём форматер и интерактивный ввод
            formatter = HHFilterFormatter()
            filter_input = InteractiveFilterInput(formatter=formatter, io=self._io)

            # Запускаем сценарий сбора фильтра
            result = filter_input.run()

        except FilterCancelled:
            logger.warning("Фильтр отменён пользователем на этапе настройки.")
            self._io["output"]("❌ Сборка фильтра отменена.")
            return "main_menu"

        # Пользователь не подтвердил фильтр
        if result is None:
            logger.info("Фильтр не был подтверждён пользователем.")
            self._io["output"]("ℹ️ Фильтр не применён.")
            return "main_menu"

        # Сохраняем фильтр в состояние приложения
        self.filter = result
        logger.info("Фильтр успешно применён: %r", result)
        self._io["output"]("✅ Фильтр успешно применён.")

        while True:
            # Меню после фильтрации
            self._io["output"]("\nЧто вы хотите сделать дальше?")
            self._io["output"]("")
            menu = {
                1: ("Применить фильтр к архиву", "storage_entry"),
                2: ("Посмотреть собранный фильтр", "preview"),
                3: ("Вернуться в главное меню", "main_menu"),
                4: ("Выйти из приложения", "exit"),
            }

            step = self._menu_loop(menu, "")
            if step == "":
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_storage_entry(self) -> str:
        """
        Точка входа в раздел работы с архивом вакансий.
        Проверяет наличие фильтра, формирует меню действий и делегирует обработку.
        """

        logger.debug("Вход в раздел работы с архивом.")
        self._io["output"]("\nРабота с архивом вакансий\n")

        # Сценарий: фильтр установлен
        if self.filter:
            try:
                vacancies = self.json_storage.apply_filter(self.filter)
            except Exception as e:
                logger.exception("Ошибка при применении фильтра: %s", e)
                self._io["output"]("⚠️ Ошибка при применении фильтра. Возврат в главное меню.")
                return "main_menu"

            logger.info("После фильтрации найдено %d вакансий.", len(vacancies))

            if not vacancies:
                logger.debug("Список отфильтрованных вакансий пуст.")
                return self._handle_filtered_empty()
            return self._handle_filtered_found(vacancies)

        # Сценарий: фильтр отсутствует
        return self._handle_no_filter()

    def _handle_filtered_empty(self) -> str:
        """Меню действий, если, по фильтру, вакансий не найдено."""

        self._io["output"]("По фильтру ничего не найдено.")
        self._io["output"]("Выберите дальнейшее действие:")
        self._io["output"]("")

        menu = {
            1: ("Изменить фильтр", "filter"),
            2: ("Посмотреть собранный фильтр", "preview"),
            3: ("Вернуться в главное меню", "main_menu"),
            4: ("Выйти из приложения", "exit"),
        }

        while True:
            step = self._menu_loop(menu, "")
            if step == "":
                # choice is None → повторяем текущий метод
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def _handle_filtered_found(self, vacancies: list) -> str:
        """Меню действий, если, по фильтру, вакансий найдены."""

        while True:
            self._io["output"](f"✅ Найдено {len(vacancies)} вакансий по фильтру.\n")
            menu = {
                1: ("Показать вакансии как есть", "show"),
                2: ("Отсортировать вакансии по зарплате", "sort"),
                3: ("Показать топ‑N вакансий", "top"),
                4: ("Изменить фильтр", "filter"),
                5: ("Вернуться в главное меню", "main_menu"),
                6: ("Выйти из приложения", "exit"),
            }

            step = self._menu_loop(menu, "")
            if step == "":
                continue
            return self.handle_vacancy_action(step=step, vacancies=vacancies, return_value=step)

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def handle_top_n(self, vacancies: list) -> str:
        """
        Обрабатывает сценарий показа топ‑N вакансий.
        Запрашивает у пользователя число N, проверяет ввод и выводит результат.
        Возвращает имя следующего шага.
        """

        logger.debug("handle_top_n: старт обработки топ‑N для %d вакансий.", len(vacancies))

        n = ask_int(self._io, "Введите количество вакансий для показа: ", min_value=1)
        if n is None:
            self._io["output"]("Отмена выбора. Возврат в главное меню.")
            logger.info("handle_top_n: пользователь отменил ввод топ‑N вакансий.")
            return "main_menu"

        logger.info("handle_top_n: пользователь выбрал N=%d", n)
        top_vacancies = get_top_n_vacancies(vacancies, n)
        logger.debug("handle_top_n: получено %d вакансий после применения top‑N.", len(top_vacancies))

        return self.show_vacancies_list(top_vacancies)

    def show_vacancies_list(self, vacancies: list) -> str:
        """
        Постраничный просмотр вакансий из архива.
        """

        logger.debug("Запуск show_vacancies_list с %d вакансиями.", len(vacancies))

        if not vacancies:
            self._io["output"]("Список вакансий пуст.\n")
            logger.info("Попытка показать вакансии: список пуст.")
            return "main_menu"

        total_vacancies = len(vacancies)

        while True:
            # Рендер текущей страницы
            start, end = render_vacancies_page(
                io=self._io,
                vacancies=vacancies,
                current_page=self.current_page,
                page_size=self.page_size,
                total_vacancies=total_vacancies,
            )

            # После показа — меню действий
            menu = {
                1: ("Следующая страница", "next_page"),
                2: ("Предыдущая страница", "prev_page"),
                3: ("Показать подробности вакансии", "storage_show_details"),
                4: ("Вернуться в раздел архива", "storage_entry"),
                5: ("В главное меню", "main_menu"),
                6: ("Выйти из приложения", "exit"),
            }

            step = self._menu_loop(menu, "")
            if step == "":
                continue

            if step == "next_page":
                if end < total_vacancies:
                    self.current_page += 1
                continue

            elif step == "prev_page":
                if self.current_page > 0:
                    self.current_page -= 1
                continue

            elif step == "storage_show_details":
                return "storage_show_details"

            else:
                return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_preview(self) -> str:
        """
        Выводит человекочитаемый обзор собранного фильтра.
        Возвращает имя следующего шага.
        """

        logger.debug("Запуск step_preview")

        if not self.filter:
            return self._handle_no_filter()

        # Фильтр установлен — показываем обзор
        filter_preview = FilterPreviewRenderer(self.filter, self._io)

        self._io["output"]("\nОбзор фильтра:\n")
        filter_preview.render()
        self._io["output"]("")

        while True:
            menu = {
                1: ("Изменить фильтр", "filter"),
                2: ("Применить фильтр", "apply_filter"),
                3: ("Вернуться в главное меню", "main_menu"),
            }

            step = self._menu_loop(menu, "")
            if step == "":
                continue
            logger.info("step_preview: выбран пункт → %s", step)
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def _handle_no_filter(self) -> str:
        """Общий сценарий, когда фильтр отсутствует."""

        while True:
            logger.debug("Фильтр не установлен.")
            self._io["output"]("Фильтр не установлен.\n")

            menu = {
                1: ("Установить фильтр", "filter"),
                2: ("Показать все вакансии без фильтра", "show_all"),
                3: ("Вернуться в главное меню", "main_menu"),
                4: ("Выйти из приложения", "exit"),
            }

            step = self._menu_loop(menu, "")
            if step == "":
                continue

            if step == "show_all":
                base = self.json_storage.get_vacancies()
                return self._handle_show_all(base)

            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def _handle_show_all(self, vacancies: list) -> str:
        """Меню действий для режима 'Показать все вакансии без фильтра'."""

        while True:
            menu = {
                1: ("Показать как есть", "show"),
                2: ("Отсортировать по зарплате", "sort"),
                3: ("Показать топ‑N вакансий", "top"),
            }

            step = self._menu_loop(menu, "")
            if step == "":
                continue

            return self.handle_vacancy_action(step=step, vacancies=vacancies, return_value="main_menu")

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_apply_filter(self) -> str:
        """
        Применяет текущий фильтр к архиву вакансий и предлагает действия с результатом.
        Возвращает имя следующего шага.
        """

        logger.debug("Запуск step_apply_filter")

        if not self.filter:
            return self._handle_no_filter()

        try:
            vacancies = self.json_storage.apply_filter(self.filter)
        except Exception as e:
            logger.exception("Ошибка при применении фильтра: %s", e)
            self._io["output"]("Ошибка при применении фильтра. Возврат в главное меню.")
            return "main_menu"

        logger.info("После применения фильтра найдено %d вакансий.", len(vacancies))

        if not vacancies:
            return self._handle_filtered_empty()  # Вакансии не найдены
        return self._handle_filtered_found(vacancies)  # Вакансии найдены

    def _show_vacancies(self, vacancies: list) -> str:
        """
        Показывает список вакансий «как есть» без сортировки и дополнительных обработок.

        :param vacancies: Список объектов Vacancy для отображения.
        :return: Имя следующего шага state machine после показа.
        """

        return self.show_vacancies_list(vacancies)

    def _sort_and_show(self, vacancies: list) -> str:
        """
        Сортирует вакансии по зарплате и выводит результат.

        :param vacancies: Список объектов Vacancy для сортировки и отображения.
        :return: Имя следующего шага state machine после показа.
        """

        return self.show_vacancies_list(sort_by_salary(vacancies))

    def _top_and_show(self, vacancies: list) -> str:
        """
        Показывает топ‑N вакансий из списка (N запрашивается у пользователя).

        :param vacancies: Список объектов Vacancy для отбора топ‑N.
        :return: Имя следующего шага state machine после показа.
        """

        return self.handle_top_n(vacancies)

    def handle_vacancy_action(self, *, step: str, vacancies: list, return_value: str = "main_menu") -> str:
        """
        Обрабатывает действие над списком вакансий: показать, отсортировать, показать топ‑N.

        :param step: Ключ действия ("show", "sort", "top").
        :param vacancies: Список объектов Vacancy.
        :param return_value:
        :return: Имя следующего шага state machine.
        """
        if step == "show":
            return self._show_vacancies(vacancies)
        elif step == "sort":
            return self._sort_and_show(vacancies)
        elif step == "top":
            return self._top_and_show(vacancies)
        else:
            logger.warning("handle_vacancy_action: неизвестный шаг %s", step)
            self._io["output"](f"Неизвестный пункт меню. Возврат в {return_value}.")
            return return_value

    def step_storage_add_from_results(self) -> str:
        """
        Сохранение вакансии из списка результатов поиска в локальное хранилище.
        Пользователь видит текущую страницу вакансий и вводит номер для сохранения.
        """

        # 1. Проверка наличия вакансий
        if not self.vacancies:
            while True:
                self._io["output"]("Нет вакансий для сохранения.")
                logger.warning("storage_add_from_results: список вакансий пуст")
                self._io["output"]("")
                self._io["output"]("Хотите вернуться к просмотру вакансий или к поиску вакансий?")
                menu = {
                    1: ("Просмотреть вакансий", "show_results"),
                    2: ("Начать поиск вакансий", "search"),
                }
                step = self._menu_loop(menu, "")
                if step == "":
                    continue
                return step

        # 2. Отображение текущей страницы
        self._io["output"]("Вы остановились на этой странице:")
        start, end = render_vacancies_page(
            io=self._io,
            vacancies=self.vacancies,
            current_page=self.current_page,
            page_size=self.page_size,
            total_vacancies=self.total_vacancies,
        )

        # 3. Запрос выбора
        idx = ask_int(self._io, "Какую вакансию хотите сохранить? Введите номер:", min_value=start + 1, max_value=end)

        if idx is None:
            self._io["output"]("Некорректный ввод. Возврат к списку вакансий.")
            return "show_results"

        # 4. Определение выбранной вакансии
        vacancy = self.vacancies[idx - 1]
        logger.info("storage_add_from_results: выбран индекс %s", idx)

        # 5. Сохранение в архив
        try:
            success = self.json_storage.add_vacancy(vacancy)

            if success:
                self._io["output"]("Вакансия сохранена или обновлена в архиве.")
                logger.info("storage_add_from_results: вакансия добавлена/обновлена")
            else:
                self._io["output"]("Вакансия уже есть в архиве или изменений не требуется.")
                logger.info("storage_add_from_results: изменений не было")
        except (TypeError, ValueError) as e:
            self._io["output"](f"Ошибка при сохранении вакансии: {e}")
            logger.warning("storage_add_from_results: ошибка валидации")

        # 6. Возврат следующего шага
        return "storage_entry"

    def step_storage_add(self) -> str:
        """
        Сохранение вакансии в архив.
        """

        # 1. Проверка контекста
        if not isinstance(self.current_vacancy, Vacancy):
            self._io["output"]("Ошибка: вакансия должна быть объектом класса Vacancy. Возврат к выбору вакансии.")
            return "show_details"

        # 2. Попытка сохранения
        try:
            success = self.json_storage.add_vacancy(self.current_vacancy)
            if success:
                self._io["output"]("Вакансия сохранена или обновлена в архиве.")
                logger.info("storage_add: вакансия добавлена/обновлена")
            else:
                self._io["output"]("Вакансия уже есть в архиве или изменений не требуется.")
                logger.info("storage_add: изменений не было")
        except (TypeError, ValueError) as e:
            self._io["output"](f"Ошибка при сохранении вакансии: {e}")
            logger.warning("storage_add: ошибка валидации")

        # 3. Очистка контекста
        self.current_vacancy = None

        # 4. Переход к следующему шагу
        return "storage_entry"

    def step_storage_menu(self) -> str:
        """
        Главное меню архива.
        Позволяет выбрать действие с сохранёнными вакансиями.
        """

        while True:
            self._io["output"]("Меню архива. Что хотите сделать?")
            menu = {
                1: ("Просмотреть архив", "storage_entry"),
                2: ("Обновить вакансию", "storage_update"),
                3: ("Удалить вакансию", "storage_remove"),
                4: ("Поиск по архиву", "storage_search"),
                5: ("Вернуться к результатам поиска", "show_results"),
                6: ("В главное меню", "main_menu"),
                7: ("Выход", "exit"),
            }

            step = self._menu_loop(menu, "")
            if step == "":
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_storage_show_details(self) -> str:
        """
        Показ подробностей выбранной вакансии из архива и меню действий.
        """

        logger.debug("Шаг 'storage_show_details' запущен")

        # 1. Загрузка вакансий из хранилища
        vacancies = self.json_storage.get_vacancies()

        # 2. Меню действия, если архив пуст
        if not vacancies:
            while True:
                self._io["output"]("Архив пуст.\n")
                self._io["output"]("Что хотите сделать дальше?\n")

                menu = {
                    1: ("Поиск вакансий по API", "choose_api"),
                    2: ("Вернуться к результатам поиска", "show_results"),
                    3: ("В главное меню", "main_menu"),
                    4: ("Выход", "exit"),
                }
                step = self._menu_loop(menu, "")
                if step == "":
                    continue
                return step

        # 3. Отображение текущей страницы архива
        self._io["output"]("Вы остановились на этой странице архива:")
        start, end = render_vacancies_page(
            io=self._io,
            vacancies=vacancies,
            current_page=self.current_page,
            page_size=self.page_size,
            total_vacancies=len(vacancies),
        )

        # 4. Запрос номера вакансии
        vacancy_num = ask_int(
            self._io,
            "Введите номер вакансии, подробности которой хотите посмотреть (или 'отмена' для возврата): --> ",
            min_value=start + 1,
            max_value=end,
        )
        if vacancy_num is None:
            logger.info("Пользователь отменил ввод номера вакансии → возврат в show_vacancies_list")
            self._io["output"]("❌ Вы отменили выбор вакансии. Возврат к списку архива.\n")
            return "show_vacancies_list"

        vacancy_idx = vacancy_num - 1
        vacancy = vacancies[vacancy_idx]
        self.current_vacancy = vacancy

        # 5. Вывод деталей
        self._io["output"](vacancy.details())
        self._io["output"]("")

        # 6. Меню действий
        while True:
            menu = {
                1: ("Обновить вакансию", "storage_update"),
                2: ("Удалить вакансию", "storage_remove"),
                3: ("Вернуться к списку архива", "storage_entry"),
                4: ("В главное меню", "main_menu"),
                5: ("Выход", "exit"),
            }
            step = self._menu_loop(menu, "")
            if step == "":
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_storage_select_vacancy(self) -> str:
        """
        Постраничный просмотр архива с возможностью выбрать вакансию.
        Используется перед обновлением/удалением, если current_vacancy не задан.
        """

        logger.debug("Шаг 'storage_select_vacancy' запущен")

        vacancies = self.json_storage.get_vacancies()
        if not vacancies:
            self._io["output"]("Архив пуст.")
            logger.info("Архив пуст → возврат в storage_menu")
            return "storage_menu"

        if self.current_page < 1:
            logger.debug(f"current_page={self.current_page} → нормализация до 1")
            self.current_page = 1

        while True:
            # 1. Отображение текущей страницы
            start, end = render_vacancies_page(
                io=self._io,
                vacancies=vacancies,
                current_page=self.current_page,
                page_size=self.page_size,
                total_vacancies=len(vacancies),
            )
            logger.debug(f"Отображена страница {self.current_page}: вакансии {start + 1}–{end} из {len(vacancies)}")

            # 2. Меню навигации
            menu = {
                1: ("Следующая страница", "next"),
                2: ("Предыдущая страница", "prev"),
                3: ("Выбрать вакансию", "select"),
                4: ("Вернуться в меню архива", "storage_menu"),
                5: ("В главное меню", "main_menu"),
                6: ("Выход", "exit"),
            }
            render_menu(io=self._io, menu=menu)

            choice = ask_choice(self._io, menu)
            if choice is None:
                logger.info("ask_choice вернул None → возврат в storage_menu")
                return "storage_menu"

            logger.debug(f"Выбор пользователя: {choice}: {menu[choice][1]}")

            if choice == 1:  # next
                if end < len(vacancies):
                    self.current_page += 1
                    logger.info(f"Переход на следующую страницу: {self.current_page}")
                else:
                    self._io["output"]("Это последняя страница.")
                    logger.info("Попытка перейти дальше → последняя страница")

            elif choice == 2:  # prev
                if self.current_page > 1:
                    self.current_page -= 1
                    logger.info(f"Переход на предыдущую страницу: {self.current_page}")
                else:
                    self._io["output"]("Это первая страница.")
                    logger.info("Попытка перейти назад → первая страница")

            elif choice == 3:  # select
                logger.debug("Пользователь выбрал действие 'select' → повторный вывод текущей страницы")
                self._io["output"]("Вы остановились на этой странице архива:")
                start, end = render_vacancies_page(
                    io=self._io,
                    vacancies=vacancies,
                    current_page=self.current_page,
                    page_size=self.page_size,
                    total_vacancies=len(vacancies),
                )

                vacancy_num = ask_int(
                    self._io,
                    "Введите номер вакансии (или 'отмена' для возврата): --> ",
                    min_value=start + 1,
                    max_value=end,
                )
                logger.debug(f"Результат ввода номера вакансии: {vacancy_num}")

                if vacancy_num is None:
                    logger.info("Пользователь отменил выбор вакансии → остаёмся на текущей странице")
                    continue

                vacancy = vacancies[vacancy_num - 1]
                self.current_vacancy = vacancy
                logger.info(
                    f"Выбрана вакансия №{vacancy_num} (индекс {vacancy_num - 1}) → переход в storage_show_details"
                )
                return "storage_show_details"

            else:
                # choice == 4, 5, 6 -> storage_menu, main_menu, exit
                logger.info(f"Выход из step_storage_select_vacancy → переход в {menu[choice][1]}")
                return menu[choice][1]

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def _check_current_vacancy(self) -> tuple[Literal["ok", "not_selected", "invalid_type"], bool]:
        """
        Проверяет установлена ли вакансия для сохранения в архив (объект класса Vacancy) в self.current_vacancy.
        Возвращает статус и булево значение.
        Если значение self.current_vacancy имеет не правильный тип -> "invalid_type", False.
        Если вакансия не установлена -> "not_selected", False.
        Если вакансия установлена -> "ok", True.
        """

        if self.current_vacancy:
            if not isinstance(self.current_vacancy, Vacancy):
                self._io["output"]("Ошибка: выбранная вакансия не является объектом класса Vacancy.")
                logger.info("Ошибка: выбранная вакансия не является объектом класса Vacancy. ")
                return "invalid_type", False
        else:
            self._io["output"]("Вакансия не выбрана.")
            logger.info("Вакансия не выбрана.")
            return "not_selected", False
        return "ok", True

    def _has_vacancies_in_storage(self) -> bool:
        """
        Проверяет, есть ли вакансии в хранилище.
        Returns:
            bool: False, если хранилище пустое; True, если есть вакансии.
        """

        if not self.json_storage.get_vacancies():
            logger.info("Хранилище пусто.")
            return False
        logger.debug("Хранилище содержит вакансии.")
        return True

    def _get_vacancy_from_storage(
        self, vacancy_url: str
    ) -> tuple[Literal["ok", "invalid_type", "not_found"], Optional[Vacancy]]:
        """
        Проверяет наличие вакансии в архиве по URL.
        :param vacancy_url: Ссылка на вакансию.
        :return: ("ok", Vacancy) если найдена;
                 ("not_found", None) если нет.
        """

        vacancy = self.json_storage.get_by_url(vacancy_url)

        if vacancy is None:
            logger.warning("Вакансия по данному URL не найдена.")
            return "not_found", None

        logger.debug("Выбранная вакансия найдена в хранилище.")
        return "ok", vacancy

    def _check_selected_vacancy(self) -> Optional[str]:
        """
        Проверяет корректность выбранной вакансии.
        :return:  Шаг 'storage_select_vacancy', если вакансия не выбрана или тип некорректный,
                  None, если проверка пройдена.
        """

        status, flag = self._check_current_vacancy()
        if not flag and status in ("invalid_type", "not_selected"):
            self._io["output"](
                "Попытайтесь выбрать вакансию заново. " "Переход к выбору вакансии (шаг: storage_select_vacancy)"
            )
            logger.info("Переход к выбору вакансии (шаг: storage_select_vacancy)")
            return "storage_select_vacancy"
        return None

    def _check_storage_not_empty(self) -> Optional[str]:
        """
        Проверяет хранилище на наличие вакансии.
        :return: Шаг 'choose_api', если хранилище пустое,
                 None, если проверка пройдена.
        """

        if not self._has_vacancies_in_storage():
            self._io["output"]("Хранилище пусто. Переход к поиску вакансии (шаг: choose_api).")
            logger.info("Хранилище пусто. Переход к поиску вакансии (шаг: choose_api)")
            return "choose_api"
        return None

    def _check_vacancy_in_storage(self) -> Optional[str]:
        """
        Проверяет нахождение вакансии в хранилище.
        :return: Шаг 'storage_select_vacancy', если вакансия отсутствует в хранилище,
                 None, если вакансия найдена (информация выводится).
        """

        # Проверка, что текущая вакансия выбрана
        if self.current_vacancy is None:
            raise RuntimeError("Вакансия не выбрана")

        vacancy_url = self.current_vacancy.url_vacancy  # url вакансии, которую нужно найти
        status, vacancy = self._get_vacancy_from_storage(vacancy_url)

        if status == "ok":
            if vacancy is None:
                # mypy требует явной проверки
                raise RuntimeError("Vacancy object отсутствует при статусе 'ok'")

            self._io["output"]("Выбранная вакансия найдена в хранилище. Информация о вакансии:")
            # Вывод деталей вакансии
            self._io["output"]("")
            self._io["output"](vacancy.details())
            self._io["output"]("")
            return None

        elif status == "not_found":
            self._io["output"]("Выбранная вакансия отсутствует в хранилище. Попытайтесь выбрать вакансию заново.")
            logger.warning(
                "Выбранная вакансия отсутствует в хранилище. Возврат к выбору вакансии (шаг: storage_select_vacancy)"
            )
            return "storage_select_vacancy"

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def _check_storage_context(self) -> Optional[str]:
        """
        Выполняет комплексную проверку состояния перед операциями с архивом вакансий.

        Последовательно проверяет:
          1. Наличие выбранной вакансии (self.current_vacancy).
          2. Что архив вакансий не пустой.
          3. Что выбранная вакансия действительно присутствует в архиве.

        Если одна из проверок не пройдена — возвращает строку с названием шага.
        Если все проверки успешны — возвращает None, что означает готовность к дальнейшей работе.
        """

        # Проверка выбранной вакансии.
        result = self._check_selected_vacancy()
        if result is not None:
            return result

        # Проверка хранилища.
        result = self._check_storage_not_empty()
        if result is not None:
            return result

        # Проверка нахождения вакансии в хранилище.
        result = self._check_vacancy_in_storage()
        if result is not None:
            return result

        return None

    def step_storage_update(self) -> str:
        """
        Шаг 'storage_update': проверяет выбранную вакансию и хранилище,
        затем предлагает меню действий (обновление, выбор другой вакансии,
        возврат назад, меню архива или главное меню).
        """

        logger.debug("Шаг 'storage_update' запущен")

        check_storage_result = self._check_storage_context()
        if check_storage_result is not None:
            return check_storage_result

        while True:
            # Меню действий
            action_menu = {
                1: ("Внести изменения в вакансию", "storage_update_edit"),
                2: ("Выбрать другую вакансию", "storage_select_vacancy"),
                3: ("Вернуться на предыдущий шаг", "back"),
                4: ("Вернуться в меню архива", "storage_menu"),
                5: ("В главное меню", "main_menu"),
            }

            self._io["output"]("Выберите действие:")
            self._io["output"]("")

            step = self._menu_loop(action_menu, "")
            if step == "":
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_storage_update_edit(self) -> str:
        """
        Запускает цикл редактирования полей вакансии.
        :return: Строка шага (например, "storage_update"), если нужно выйти из сценария,
                 None, если редактирование завершено и остаёмся в текущем шаге.
        """

        self._io["output"]("Вы переходите в раздел обновления вакансии")
        if self.current_vacancy is None:
            self._io["output"]("❌ Вакансия не выбрана. Пожалуйста, выберите вакансию для редактирования.")
            logger.debug("Вакансия не выбрана (self.current_vacancy = None). Переход в storage_select_vacancy.")
            return "storage_select_vacancy"

        self.vacancy_new_data = self.current_vacancy.to_dict()  # Словарь с исходными данными

        while True:
            # Меню для редактирования
            vacancy_fields = {
                1: ("Название вакансии", "name_vacancy"),
                2: ("Ссылка", "url_vacancy"),
                3: ("Альтернативная ссылка", "alternate_url"),
                4: ("Минимальная заработная плата", "salary_from"),
                5: ("Максимальная заработная плата", "salary_to"),
                6: ("Валюта заработной платы", "currency"),
                7: ("Описание", "description"),
            }

            # Меню действий
            step_back = {
                8: ("Сохранить изменения в вакансию", "storage_update_save"),
                9: ("Вернуться на предыдущий шаг", "storage_update"),
            }

            self._io["output"]("Какое поле вакансии вы хотите изменить?")
            self._io["output"]("")
            render_menu(io=self._io, menu=vacancy_fields)
            self._io["output"]("-" * 20)
            render_menu(io=self._io, menu=step_back)

            cm = ChainMap(vacancy_fields, step_back)
            choice_vacancy_fields = ask_choice(self._io, dict(cm))

            # Ссылка для поиска вакансии. Если ссылка будет изменена, то это, старая ссылка для поиска в хранилище.
            self.old_url = self.current_vacancy.url_vacancy or self.current_vacancy.alternate_url

            # Условие если ask_choice по ошибке вернул None
            if choice_vacancy_fields is None:
                logger.info("ask_choice вернул None → повтор меню")
                continue

            # Условие сохранения изменений и на предыдущий шаг
            elif choice_vacancy_fields in (8, 9):
                return next_step(io=self._io, menu=step_back, choice=choice_vacancy_fields)

            # Обработка полей вакансии
            else:
                vac_field = cm[choice_vacancy_fields][1]

                logger.debug(f"Выбор пользователя: {choice_vacancy_fields}: {vac_field}")
                self._io["output"](f"Вы выбрали: {vac_field}")

                if vac_field == "salary_from":
                    self._edit_salary_from(self.vacancy_new_data)

                elif vac_field == "salary_to":
                    self._edit_salary_to(self.vacancy_new_data)

                elif vac_field == "currency":
                    self._edit_currency(self.vacancy_new_data)

                elif vac_field in ("name_vacancy", "description"):
                    self._edit_name_vacancy_and_description(self.vacancy_new_data, vac_field)

                elif vac_field in ("url_vacancy", "alternate_url"):
                    self._edit_url_vacancy_and_alternate_url(self.vacancy_new_data, vac_field)

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_storage_update_save(self) -> str:
        """
        Шаг 'storage_update_save': сохраняет изменения вакансии в архив.
        Обновляет объект Vacancy и возвращает следующий шаг.
        """

        if self.old_url is None:
            raise RuntimeError("old_url не установлен, невозможно обновить вакансию")

        update = self.json_storage.update_vacancy(self.old_url, self.vacancy_new_data)
        if not update:
            self._io["output"]("ℹ️ Изменений не было. Возврат в редактор.")
            return "storage_update_edit"

        logger.info("Вакансия обновлена. Изменения сохранены.")
        self._io["output"]("✅ Изменения сохранены.")

        # Сброс временных данных
        self.current_vacancy = None
        self.vacancy_new_data = {}
        self.old_url = None
        self._io["output"]("✅ Изменения сохранены. Текущая вакансия сброшена, выберите заново для редактирования.")
        logger.debug("Изменения в вакансию сохранены. Текущая вакансия сброшена(self.current_vacancy = None)")

        return "storage_update"

    def _prompt_field_input(self, vacancy_field: str) -> str:
        """
        Просит пользователя ввести новые данные.
        :param vacancy_field: Название поля вакансии.
        :return: Новые данные.
        """

        self._io["output"]("Введите 'назад', чтобы вернуться на шаг назад.")
        return self._io["input"](f"Введите новое значение для '{vacancy_field}' --> ").strip()

    def _edit_salary_from(self, vacancy_new_data: dict) -> bool:
        """
        Проверяем salary_from. Если данные не прошли проверку, просит повторить ввод.
        :param vacancy_new_data: Словарь с новыми данными
        :return: Если пользователь ввел "назад" -> False,
                Если проверка пройдена -> True.
        """

        while True:
            new_value = self._prompt_field_input("salary_from")

            if self._is_back_command_for_step_storage_update(user_input=new_value, vacancy_field="salary_from"):
                logger.debug("Пользователь вышел из редактирования salary_from")
                return False

            salary_from = validate_salary(self._io, new_value)
            if salary_from:
                vacancy_new_data["salary_from"] = salary_from
                return True

    def _edit_salary_to(self, vacancy_new_data: dict) -> bool:
        """
        Проверяем salary_to. Если данные не прошли проверку, просит повторить ввод.
        :param vacancy_new_data: Словарь с новыми данными
        :return: Если пользователь ввел "назад" -> False,
                Если проверка пройдена -> True.
        """

        while True:
            new_value = self._prompt_field_input("salary_to")

            if self._is_back_command_for_step_storage_update(user_input=new_value, vacancy_field="salary_to"):
                logger.debug("Пользователь вышел из редактирования salary_to")
                return False

            salary_to = validate_salary(self._io, new_value)
            if salary_to:
                salary_from = vacancy_new_data.get("salary_from")
                if salary_from is not None and salary_to < salary_from:
                    logger.warning("Максимальная зарплата (%s) меньше минимальной (%s).", salary_to, salary_from)
                    self._io["output"](
                        f"❌ Ошибка: максимальная зарплата ({salary_to}) меньше минимальной ({salary_from})."
                    )
                    self._io["output"]("Попробуйте ввести другое значение.")
                    continue

                else:
                    vacancy_new_data["salary_to"] = salary_to
                    return True

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def _edit_currency(self, vacancy_new_data: dict) -> bool:
        """
        Проверяем currency. Если данные не прошли проверку, просит повторить ввод.
        :param vacancy_new_data: Словарь с новыми данными
        :return: Если пользователь ввел "назад" -> False,
                Если проверка пройдена -> True.
        """

        while True:
            new_value = self._prompt_field_input("currency")

            if self._is_back_command_for_step_storage_update(user_input=new_value, vacancy_field="currency"):
                logger.debug("Пользователь вышел из редактирования currency")
                return False

            currency = validate_currency(new_value, ALLOWED_CURRENCIES)
            if currency:
                vacancy_new_data["currency"] = currency
                return True

    def _edit_name_vacancy_and_description(self, vacancy_new_data: dict, vacancy_field: str) -> bool:
        """
        Проверяем name_vacancy или description. Если данные не прошли проверку, просит повторить ввод.
        :param vacancy_new_data: Словарь с новыми данными
        :param vacancy_field: Поле вакансии
        :return: Если пользователь ввел "назад" -> False,
                Если проверка пройдена -> True.
        """

        while True:
            new_value = self._prompt_field_input(vacancy_field)

            if self._is_back_command_for_step_storage_update(user_input=new_value, vacancy_field=vacancy_field):
                return False

            user_input = new_value.strip()
            if user_input == "":
                logger.warning("Ввод состоит только из пробелов. %s не принято.", vacancy_field)
                self._io["output"](f"❌ {vacancy_field} не может состоять только из пробелов. Повторите попытку.")
                continue

            vacancy_new_data[vacancy_field] = new_value
            return True

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def _edit_url_vacancy_and_alternate_url(self, vacancy_new_data: dict, vacancy_field: str) -> bool:
        """
        Проверяем url_vacancy или alternate_url. Если данные не прошли проверку, просит повторить ввод.
        :param vacancy_new_data: Словарь с новыми данными
        :param vacancy_field: Поле вакансии
        :return: Если пользователь ввел "назад" -> False,
                Если проверка пройдена -> True.
        """

        while True:
            new_value = self._prompt_field_input(vacancy_field)

            if self._is_back_command_for_step_storage_update(user_input=new_value, vacancy_field=vacancy_field):
                return False

            user_input = new_value.strip()
            urls = validate_url(io=self._io, user_input=user_input, step=vacancy_field)
            if urls:
                if len(urls) == 1:
                    vacancy_new_data[vacancy_field] = urls[0]
                    logger.info("Установлен одиночный %s: %s", vacancy_field, urls[0])
                    self._io["output"](f"{vacancy_field} установлен: {urls[0]}")
                    return True
                else:
                    vacancy_new_data[vacancy_field] = urls
                    logger.info("Установлен список %s: %s", vacancy_field, urls)
                    self._io["output"](f"Список {vacancy_field} установлен: {', '.join(urls)}")
                    return True
            continue

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def _is_back_command_for_step_storage_update(self, *, user_input: str, vacancy_field: str) -> bool:
        """
        Проверяет пользовательский ввод.
        :return: Если "назад", то True, иначе False.
        """

        if user_input.lower() == "назад":
            self._io["output"]("Вы вернулись в меню редактирования, изменения не сохранены.")
            logger.info("Пользователь вернулся назад, поле '%s' не изменено", vacancy_field)
            return True
        return False

    def step_storage_remove(self) -> str:
        """
        Шаг 'storage_remove': удаляет выбранную вакансию из архива.

        Последовательно:
          1. Проверяет контекст (выбранная вакансия, непустое хранилище, наличие вакансии).
          2. Определяет индекс вакансии по основному или альтернативному URL.
          3. Показывает информацию о вакансии и меню действий.
          4. При подтверждении удаляет вакансию и сохраняет изменения.
          5. В случае ошибок или отмены возвращает соответствующий шаг.
        """

        logger.debug("Шаг 'storage_remove' запущен")

        # Проверка контекста
        check_storage_result = self._check_storage_context()
        if check_storage_result is not None:
            return check_storage_result

        if not isinstance(self.current_vacancy, Vacancy):
            raise RuntimeError("Ошибка: self.current_vacancy не является объектом класса Vacancy")

        # Получаем ссылки
        vacancy_url = self.current_vacancy.url_vacancy
        vacancy_alternate_url = self.current_vacancy.alternate_url

        # Нормализация ссылок
        normalized_url = norm_str(vacancy_url, lower=True)
        normalized_alternate_url = norm_str(vacancy_alternate_url, lower=True)

        # Проверка на наличие хотя бы одной ссылки
        if not normalized_url and not normalized_alternate_url:
            self._io["output"]("У вакансии отсутствует url и alternate_url. Возврат в storage_menu")
            logger.warning("Ошибка: у вакансии отсутствует url и alternate_url. Возврат в storage_menu")
            return "storage_menu"

        # Загружаем список
        self.storage_vacancies = self.json_storage.safe_load_all()
        if not validate_list(self.storage_vacancies, dict):
            return "storage_menu"

        # Определяем индекс вакансии
        if normalized_url:
            self.vacancy_idx = self.json_storage.find_vacancy_index(normalized_url, self.storage_vacancies)
        if self.vacancy_idx is None and normalized_alternate_url:
            self.vacancy_idx = self.json_storage.find_vacancy_index(normalized_alternate_url, self.storage_vacancies)
        if self.vacancy_idx is None:
            self._io["output"]("Вакансия не найдена по основному и альтернативному URL.")
            logger.warning("Вакансия не найдена по обоим URL. Возврат в storage_select_vacancy")
            return "storage_select_vacancy"

        # Вывод информации о вакансии
        self._io["output"]("Информация о вакансии:")
        self._io["output"]("")
        self._io["output"](self.current_vacancy.details())
        self._io["output"]("")

        while True:
            # Меню действий
            action_menu = {
                1: ("Удалить вакансию", "storage_remove_confirm"),
                2: ("Выбрать другую вакансию", "storage_select_vacancy"),
                3: ("Вернуться на предыдущий шаг", "back"),
                4: ("Вернуться в меню архива", "storage_menu"),
                5: ("В главное меню", "main_menu"),
            }

            self._io["output"]("Выберите действие:")
            self._io["output"]("")

            step = self._menu_loop(action_menu, "")
            if step == "":
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")

    def step_storage_remove_confirm(self) -> str:
        """
        Подтверждение удаления вакансии: удаляет по индексу, сохраняет архив,
        обрабатывает ошибки и возвращает следующий шаг.
        """

        if self.vacancy_idx is None:
            raise RuntimeError("vacancy_idx не установлен, невозможно удалить вакансию")

        # Удаление
        try:
            vac_pop = self.storage_vacancies.pop(self.vacancy_idx)
            self._io["output"](f"Вакансия: '{str(vac_pop)}' успешно удалена.")
            logger.info("Вакансия удалена: %s", str(vac_pop))

            # После успешного удаления сброс состояния.
            self.storage_vacancies = []
            self.vacancy_idx = None

        except IndexError:
            self._io["output"]("Ошибка: индекс вакансии некорректен. Возврат к просмотру архива.")
            logger.exception("Ошибка при удалении вакансии по индексу")
            return "storage_entry"

        # Сохранение
        try:
            self.json_storage.save(self.storage_vacancies)
            self._io["output"]("Изменения успешно сохранены.")
            return self._post_remove_menu()

        except (OSError, TypeError, ValueError):
            self._io["output"]("Ошибка при сохранении архива. Возврат в storage_menu.")
            return "storage_menu"

    def _post_remove_menu(self) -> str:
        """
        Мини‑меню после успешного удаления вакансии.
        Позволяет выбрать новую вакансию, вернуться в меню архива или выйти в главное меню.
        """

        while True:
            # Меню действий
            action_menu = {
                1: ("Выбрать другую вакансию", "storage_select_vacancy"),
                2: ("Вернуться в меню архива", "storage_menu"),
                3: ("В главное меню", "main_menu"),
            }

            self._io["output"]("Выберите действие:")
            self._io["output"]("")

            step = self._menu_loop(action_menu, "")
            if step == "":
                continue
            return step

        # сюда никогда не дойдём, но нужно для mypy
        raise RuntimeError("Unreachable")
