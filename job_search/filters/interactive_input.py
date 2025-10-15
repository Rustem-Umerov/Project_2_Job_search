from typing import Any, Dict, Optional, Union

from job_search.filters.filter_formatters import BaseFilterFormatter
from job_search.filters.preview_renderer import FilterPreviewRenderer
from job_search.utils.exceptions import FilterCancelled
from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)

ALLOWED_CURRENCIES = ["USD", "EUR", "RUB", "GBP", "JPY", "CNY"]


class InteractiveFilterInput:
    """Класс для интерактивного сбора фильтра от пользователя."""

    def __init__(
        self, formatter: BaseFilterFormatter, allowed_currencies: Optional[set[str]] = None, io: Optional[dict] = None
    ):
        """ """

        # Форматер для фильтра.
        self._formatter = formatter
        # Сырые ответы пользователя.
        self._answers: dict = {}
        # Список допустимых валют.
        self._allowed_currencies = allowed_currencies or ALLOWED_CURRENCIES
        # Абстракция ввода/вывода.
        self._io = io or {"input": input, "output": print}

    def start(self) -> None:
        """Выводит приветствие, правила и список доступных полей фильтра."""

        logger.info("Запущена интерактивная сборка фильтра.")
        logger.debug("Выводим приветствие и инструкции по управлению шагами.")

        self._io["output"]("")
        self._io["output"]("🔍 Сейчас мы соберём фильтр для поиска вакансий.")
        self._io["output"]("Вы можете пропустить любой шаг, просто нажав Enter.")
        self._io["output"]("Чтобы вернуться на шаг назад - введите 'назад'.")
        self._io["output"]("Чтобы отменить фильтр, введите 'отмена' на любом шаге.")
        self._io["output"]("")

        logger.debug("Выводим список доступных полей фильтра.")
        self._io["output"]("📋 Доступные поля фильтра:")
        fields = [
            "Зарплата от / до",
            "Валюта (например: USD, EUR, RUB)",
            "Ключевые слова в описании",
            "Подстрока в названии вакансии",
            "URL вакансии (или список через запятую)",
            "Alternate URL (если есть)",
        ]
        for field in fields:
            self._io["output"](f"— {field}")

        logger.debug("Выводим примеры ввода.")
        self._io["output"]("")
        self._io["output"]("💡 Примеры ввода:")
        self._io["output"]("— Зарплата: 100000")
        self._io["output"]("— Валюта: USD")
        self._io["output"]("— Ключевые слова: Python удалёнка")
        self._io["output"]("")

        logger.info("Переход к первому шагу — запрос минимальной зарплаты.")
        self._io["output"]("✅ Начнём с минимальной зарплаты…")

    def ask_salary_from(self) -> None:
        """Запрашивает минимальную зарплату, валидирует ввод и сохраняет результат."""

        logger.info("Запрос минимальной зарплаты начат.")

        while True:
            self._io["output"]("")
            self._io["output"]("Введите минимальную зарплату (например: 100000).")
            self._io["output"]("Можно указать дробное значение, например: 100000.50")
            self._io["output"]("")
            self._io["output"]("Оставьте пустым, чтобы пропустить этот шаг.")
            self._io["output"]("Введите 'отмена', чтобы прервать сборку фильтра.")
            self._io["output"]("")

            user_input = self._io["input"]("→ ").strip()
            logger.debug("Ответ пользователя на шаг 'минимальная зарплата': '%s'", user_input)

            if user_input.lower() == "отмена":
                logger.warning("Пользователь отменил сборку фильтра на шаге минимальной зарплаты.")
                self._io["output"]("Сборка фильтра отменена")
                raise FilterCancelled("Фильтр отменён пользователем.")

            if user_input == "":
                logger.info("Пользователь пропустил шаг минимальной зарплаты.")
                self._io["output"]("Минимальная зарплата не указана. Переходим к следующему шагу.")
                return

            if user_input.lower() == "назад":
                logger.info("Пользователь попытался вернуться назад на первом шаге.")
                self._io["output"]("Вы уже на первом шаге. Назад идти некуда.")
                continue

            try:
                salary_from = float(user_input)
                salary_from = int(salary_from) if salary_from.is_integer() else salary_from
                if salary_from > 0:
                    self._answers["salary_from"] = salary_from
                    logger.info("Минимальная зарплата установлена: %s", salary_from)
                    self._io["output"](f"Минимальная зарплата установлена: {salary_from}")
                    return
                else:
                    logger.warning("Ошибка: введена неположительная зарплата: %s", salary_from)
                    self._io["output"]("❌ Ошибка: зарплата должна быть больше нуля. Попробуйте ещё раз.")
            except ValueError:
                logger.warning("Ошибка преобразования зарплаты: '%s' не является числом.", user_input)
                self._io["output"]("❌ Ошибка: зарплата должна быть числом. Попробуйте ещё раз.")

    def ask_salary_to(self) -> Optional[str]:
        """Запрашивает максимальную зарплату, валидирует ввод и сохраняет результат."""

        logger.info("Запрос максимальной зарплаты начат.")

        while True:
            self._io["output"]("")
            self._io["output"]("Введите максимальную зарплату (например: 100000).")
            self._io["output"]("Можно указать дробное значение, например: 100000.50")
            self._io["output"]("")
            self._io["output"]("Оставьте пустым, чтобы пропустить этот шаг.")
            self._io["output"]("Введите 'назад', чтобы вернуться на шаг назад.")
            self._io["output"]("Введите 'отмена', чтобы прервать сборку фильтра.")
            self._io["output"]("")

            user_input = self._io["input"]("→ ").strip()
            logger.debug("Ответ пользователя на шаг 'максимальная зарплата': '%s'", user_input)

            if user_input.lower() == "отмена":
                logger.warning("Пользователь отменил сборку фильтра на шаге максимальной зарплаты.")
                self._io["output"]("Сборка фильтра отменена")
                raise FilterCancelled("Фильтр отменён пользователем.")

            if user_input == "":
                logger.info("Пользователь пропустил шаг максимальной зарплаты.")
                self._io["output"]("Максимальная зарплата не указана. Переходим к следующему шагу.")
                return None

            if user_input.lower() == "назад":
                logger.info("Пользователь вернулся на шаг назад из запроса максимальной зарплаты.")
                self._io["output"]("Вы возвращаетесь на шаг назад.")
                return "back"

            try:
                salary_to = float(user_input)
                salary_to = int(salary_to) if salary_to.is_integer() else salary_to

                if salary_to <= 0:
                    logger.warning("Введена неположительная максимальная зарплата: %s", salary_to)
                    self._io["output"]("❌ Ошибка: зарплата должна быть положительным числом. Попробуйте ещё раз.")
                    continue

                salary_from = self._answers.get("salary_from")
                if salary_from is not None and salary_to < salary_from:
                    logger.warning("Максимальная зарплата (%s) меньше минимальной (%s).", salary_to, salary_from)
                    self._io["output"](
                        f"❌ Ошибка: максимальная зарплата ({salary_to}) меньше минимальной ({salary_from})."
                    )
                    self._io["output"]("Попробуйте ввести другое значение или пропустите шаг.")
                    continue

                self._answers["salary_to"] = salary_to
                logger.info("Максимальная зарплата установлена: %s", salary_to)
                self._io["output"](f"Максимальная зарплата установлена: {salary_to}")
                return None

            except ValueError:
                logger.warning("Ошибка преобразования зарплаты: '%s' не является числом.", user_input)
                self._io["output"]("❌ Ошибка: зарплата должна быть числом. Попробуйте ещё раз.")

    def ask_currency(self) -> Optional[str]:
        """Запрашивает валюту, валидирует ввод и сохраняет результат."""

        logger.info("Запрос валюты начат.")
        allowed = ", ".join(self._allowed_currencies)
        logger.debug("Допустимые валюты: %s", allowed)

        while True:
            self._io["output"]("")
            self._io["output"]("Введите валюту.")
            self._io["output"](f"Можете указать одну из: {allowed}")
            self._io["output"]("")
            self._io["output"]("Оставьте пустым, чтобы пропустить этот шаг.")
            self._io["output"]("Введите 'назад', чтобы вернуться на шаг назад.")
            self._io["output"]("Введите 'отмена', чтобы прервать сборку фильтра.")
            self._io["output"]("")

            user_input = self._io["input"]("→ ").strip()
            logger.debug("Ответ пользователя на шаг 'валюта': '%s'", user_input)

            if user_input.lower() == "отмена":
                logger.warning("Пользователь отменил сборку фильтра на шаге валюты.")
                self._io["output"]("Сборка фильтра отменена")
                raise FilterCancelled("Фильтр отменён пользователем.")

            if user_input == "":
                logger.info("Пользователь пропустил шаг валюты.")
                self._io["output"]("Валюта не указана. Переходим к следующему шагу.")
                return None

            if user_input.lower() == "назад":
                logger.info("Пользователь вернулся на шаг назад из запроса валюты.")
                self._io["output"]("Вы возвращаетесь на шаг назад.")
                return "back"

            currency = user_input.upper()
            logger.debug("Преобразованная валюта: '%s'", currency)

            if currency in self._allowed_currencies:
                self._answers["currency"] = currency
                logger.info("Валюта установлена: %s", currency)
                self._io["output"](f"Валюта установлена: {currency}")
                return None
            else:
                logger.warning("Валюта '%s' не поддерживается. Допустимые: %s", currency, allowed)
                self._io["output"](f"❌ Валюта '{currency}' не поддерживается. Допустимые варианты: {allowed}")
                self._io["output"]("Попробуйте ввести другую валюту или пропустите шаг.")
                continue

    def ask_description(self) -> Optional[str]:
        """Запрашивает ключевые слова для описания вакансии, валидирует ввод и сохраняет результат."""

        logger.info("Запрос ключевых слов для описания вакансии начат.")

        while True:
            self._io["output"]("")
            self._io["output"]("Введите ключевые слова для описания вакансии")
            self._io["output"]("Например: Python, удалённо, Flask")
            self._io["output"]("")
            self._io["output"]("Оставьте пустым, чтобы пропустить этот шаг.")
            self._io["output"]("Введите 'назад', чтобы вернуться на шаг назад.")
            self._io["output"]("Введите 'отмена', чтобы прервать сборку фильтра.")
            self._io["output"]("")

            raw_input = self._io["input"]("→ ")
            user_input = raw_input.strip()
            logger.debug("Ответ пользователя на шаг 'описание': raw='%s', stripped='%s'", raw_input, user_input)

            if user_input.lower() == "отмена":
                logger.warning("Пользователь отменил сборку фильтра на шаге описания.")
                self._io["output"]("Сборка фильтра отменена.")
                raise FilterCancelled("Фильтр отменён пользователем.")

            if user_input.lower() == "назад":
                logger.info("Пользователь вернулся на шаг назад из запроса описания.")
                self._io["output"]("Вы возвращаетесь на шаг назад.")
                return "back"

            if raw_input == "":
                logger.info("Пользователь пропустил шаг описания.")
                self._io["output"]("Описание не указано. Переходим к следующему шагу.")
                return None

            if user_input == "":
                logger.warning("Ввод состоит только из пробелов. Описание не принято.")
                self._io["output"]("❌ Описание не может состоять только из пробелов. Попробуйте ещё раз.")
                continue

            self._answers["contains_description"] = user_input
            logger.info("Описание вакансии установлено: '%s'", user_input)
            self._io["output"](f"Описание установлено: {user_input}")
            return None

    def ask_name_vacancy(self) -> Optional[str]:
        """Запрашивает ключевые слова для названия вакансии, валидирует ввод и сохраняет результат."""

        logger.info("Запрос ключевых слов для названия вакансии начат.")

        while True:
            self._io["output"]("")
            self._io["output"]("Введите ключевые слова, которые должны присутствовать в названии вакансии.")
            self._io["output"]("Например: Python, аналитик, удалённо")
            self._io["output"]("Поиск будет по частичному совпадению.")
            self._io["output"]("Оставьте пустым, чтобы пропустить этот шаг.")
            self._io["output"]("Введите 'назад', чтобы вернуться на шаг назад.")
            self._io["output"]("Введите 'отмена', чтобы прервать сборку фильтра.")
            self._io["output"]("")

            raw_input = self._io["input"]("→ ")
            user_input = raw_input.strip()
            logger.debug(
                "Ответ пользователя на шаг 'название вакансии': raw='%s', stripped='%s'", raw_input, user_input
            )

            if user_input.lower() == "отмена":
                logger.warning("Пользователь отменил сборку фильтра на шаге названия вакансии.")
                self._io["output"]("Сборка фильтра отменена.")
                raise FilterCancelled("Фильтр отменён пользователем.")

            if user_input.lower() == "назад":
                logger.info("Пользователь вернулся на шаг назад из запроса названия вакансии.")
                self._io["output"]("Вы возвращаетесь на шаг назад.")
                return "back"

            if raw_input == "":
                logger.info("Пользователь пропустил шаг названия вакансии.")
                self._io["output"]("Название вакансии не указано. Переходим к следующему шагу.")
                return None

            if user_input == "":
                logger.warning("Ввод состоит только из пробелов. Название вакансии не принято.")
                self._io["output"]("❌ Название не может состоять только из пробелов. Попробуйте ещё раз.")
                continue

            self._answers["contains_name"] = user_input
            logger.info("Название вакансии установлено: '%s'", user_input)
            self._io["output"](f"Название вакансии должно содержать: {user_input}")
            return None

    def ask_url(self) -> Optional[str]:
        """Запрашивает URL или список URL, валидирует ввод и сохраняет результат."""

        logger.info("Запрос URL начат.")

        while True:
            self._io["output"]("")
            self._io["output"]("Введите URL или список URL через запятую.")
            self._io["output"]("Например: https://hh.ru/vacancy/123, https://hh.ru/vacancy/456")
            self._io["output"]("Если указано несколько — будет использован оператор in.")
            self._io["output"]("Оставьте пустым, чтобы пропустить этот шаг.")
            self._io["output"]("Введите 'назад', чтобы вернуться на шаг назад.")
            self._io["output"]("Введите 'отмена', чтобы прервать сборку фильтра.")
            self._io["output"]("")

            raw_input = self._io["input"]("→ ").strip()
            logger.debug("Ответ пользователя на шаг 'URL': '%s'", raw_input)

            if raw_input.lower() == "отмена":
                logger.warning("Пользователь отменил сборку фильтра на шаге URL.")
                self._io["output"]("Сборка фильтра отменена.")
                raise FilterCancelled("Фильтр отменён пользователем.")

            if raw_input.lower() == "назад":
                logger.info("Пользователь вернулся на шаг назад из запроса URL.")
                self._io["output"]("Вы возвращаетесь на шаг назад.")
                return "back"

            if raw_input == "":
                logger.info("Пользователь пропустил шаг URL.")
                self._io["output"]("URL не указан. Переходим к следующему шагу.")
                return None

            urls = [url.strip() for url in raw_input.split(",") if url.strip()]
            logger.debug("Обработанный список URL: %s", urls)

            if not urls:
                logger.warning("Ввод не содержит ни одного корректного URL.")
                self._io["output"]("❌ Ввод не содержит ни одного корректного URL. Попробуйте ещё раз.")
                continue

            if not all(url.startswith("http") for url in urls):
                logger.warning("Некорректный формат URL: не все начинаются с http/https.")
                self._io["output"]("❌ Все URL должны начинаться с http или https. Попробуйте ещё раз.")
                continue

            if len(urls) == 1:
                self._answers["url"] = urls[0]
                logger.info("Установлен одиночный URL: %s", urls[0])
                self._io["output"](f"URL установлен: {urls[0]}")
            else:
                self._answers["url"] = urls
                logger.info("Установлен список URL: %s", urls)
                self._io["output"](f"Список URL установлен: {', '.join(urls)}")

            return None

    def ask_use_alternate_url(self) -> Union[bool, str]:
        """Спрашивает, хочет ли пользователь фильтровать по alternate_url."""

        logger.info("Пользователю предложено указать: желает ли он ввести alternate URL, (да/нет).")

        while True:
            self._io["output"]("")
            self._io["output"]("Хотите указать alternate URL для фильтрации?")
            self._io["output"]("Обычно alternate URL — это альтернативная ссылка на вакансию.")
            self._io["output"]("Введите 'да' — чтобы указать, 'нет' — чтобы пропустить.")
            self._io["output"]("Введите 'назад' — чтобы вернуться на шаг назад.")
            self._io["output"]("Введите 'отмена' — чтобы прервать сборку фильтра.")
            self._io["output"]("")

            answer = self._io["input"]("→ ").strip().lower()
            logger.debug("Ответ пользователя на вопрос, желает ли он ввести alternate URL: '%s'", answer)

            if answer == "отмена":
                logger.warning("Пользователь отменил сборку фильтра на шаге, определяющем нужен ли alternate URL.")
                self._io["output"]("Сборка фильтра отменена.")
                raise FilterCancelled("Фильтр отменён пользователем.")

            if answer == "назад":
                logger.info("Пользователь вернулся на шаг назад из запроса, определяющего нужен ли alternate URL.")
                self._io["output"]("Вы возвращаетесь на шаг назад.")
                return "back"

            if answer == "да":
                logger.info("Пользователь выбрал использовать alternate URL.")
                return True

            if answer == "нет":
                logger.info("Пользователь отказался от использования alternate URL.")
                return False

            logger.warning(
                "Неверный ответ на вопрос: хочет ли пользователь фильтровать по alternate URL: '%s'. "
                "Нужно ввести 'да' или 'нет'.",
                answer,
            )
            self._io["output"]("❌ Пожалуйста, введите 'да', 'нет', 'назад' или 'отмена'.")

    def ask_alternate_url(self) -> Optional[str]:
        """Запрашивает alternate_url или список alternate_url, валидирует ввод и сохраняет результат."""

        logger.info("Пользователю предложено указать alternate URL для фильтрации.")

        while True:
            self._io["output"]("")
            self._io["output"]("Введите alternate URL или список alternate URL через запятую.")
            self._io["output"]("Например: https://hh.ru/alt/123, https://hh.ru/alt/456")
            self._io["output"]("Если указано несколько — будет использован оператор in.")
            self._io["output"]("Оставьте пустым, чтобы пропустить этот шаг.")
            self._io["output"]("Введите 'назад', чтобы вернуться на шаг назад.")
            self._io["output"]("Введите 'отмена', чтобы прервать сборку фильтра.")
            self._io["output"]("")

            raw_input = self._io["input"]("→ ").strip()
            logger.debug("Ответ пользователя на шаг 'alternate URL': '%s'", raw_input)

            if raw_input.lower() == "отмена":
                logger.warning("Пользователь прервал сборку фильтра на этапе alternate URL.")
                self._io["output"]("Сборка фильтра отменена.")
                raise FilterCancelled("Фильтр отменён пользователем.")

            if raw_input.lower() == "назад":
                logger.info("Пользователь выбрал 'назад' на шаге alternate URL.")
                self._io["output"]("Вы возвращаетесь на шаг назад.")
                return "back"

            if raw_input == "":
                logger.info("Пользователь пропустил шаг alternate URL.")
                self._io["output"]("Alternate URL не указан. Переходим к следующему шагу.")
                return None

            urls = [url.strip() for url in raw_input.split(",") if url.strip()]
            logger.debug("Обработанный список alternate URL: %s", urls)

            if not urls:
                logger.warning("Ввод не содержит ни одного корректного alternate URL.")
                self._io["output"]("❌ Ввод не содержит ни одного корректного alternate URL. Попробуйте ещё раз.")
                continue

            if not all(url.startswith("http") for url in urls):
                logger.warning("Некорректный формат alternate URL: не все URL начинаются с http/https. Ввод: %s", urls)
                self._io["output"]("❌ Все alternate URL должны начинаться с http или https. Попробуйте ещё раз.")
                continue

            if len(urls) == 1:
                self._answers["alternate_url"] = urls[0]
                logger.info("Установлен одиночный alternate URL: %s", urls[0])
                self._io["output"](f"Alternate URL установлен: {urls[0]}")
            else:
                self._answers["alternate_url"] = urls
                logger.info("Установлен список alternate URL: %s", urls)
                self._io["output"](f"Список alternate URL установлен: {', '.join(urls)}")

            return None

    def preview(self) -> None:
        """Выводит человекочитаемый обзор собранных фильтров."""

        renderer = FilterPreviewRenderer(self._answers, self._io)
        logger.info("Переход к предварительному обзору фильтра.")
        renderer.render()

    def confirm(self) -> Optional[Dict[str, Any]]:
        """Предлагает применить, изменить или отменить фильтр.
        Возвращает:
            dict[str, Any] — если пользователь подтвердил применение фильтра,
            None — если пользователь завершил изменения, но не применил фильтр.
        Исключение:
                FilterCancelled — если пользователь отменил фильтр.
        """

        while True:
            logger.info("Пользователю показан финальный выбор: применить, изменить или отменить фильтр.")

            self._io["output"]("")
            self._io["output"]("📋 Вы просмотрели собранный фильтр.")
            self._io["output"]("Выберите действие:")
            self._io["output"]("✅ Применить фильтр — введите 'да'")
            self._io["output"]("✏️ Изменить параметры — введите 'изменить'")
            self._io["output"]("❌ Отменить фильтр — введите 'отмена'")

            user_input = self._io["input"]("→ ").strip().lower()
            logger.debug("Ответ пользователя на финальный выбор: '%s'", user_input)

            if user_input == "да":
                logger.info("Пользователь подтвердил применение фильтра.")
                filter_block = self._formatter.build_from(self._answers)
                logger.debug("Итоговый фильтр, переданный на применение: %r", filter_block)
                return filter_block

            elif user_input == "отмена":
                logger.warning("Пользователь отменил фильтр на финальном этапе.")
                raise FilterCancelled("Фильтр отменён пользователем.")

            elif user_input == "изменить":
                logger.info("Пользователь выбрал изменить параметры фильтра.")
                result = self._change_filter()
                if result == "back":
                    logger.info("Пользователь вернулся назад из режима изменения фильтра.")
                    continue

            else:
                logger.warning(
                    "Неверный ввод на финальном этапе подтверждения фильтра: '%s'. "
                    "Ожидалось: 'да', 'изменить' или 'отмена'.",
                    user_input,
                )
                self._io["output"]("❌ Неверный ввод. Пожалуйста, выберите 'да', 'изменить' или 'отмена'.")

    def _change_filter(self) -> str | None:
        """Позволяет изменить один или несколько параметров фильтра.
        Возвращает:
            "back" — если пользователь выбрал вернуться назад,
            None — если пользователь завершил изменения.
        """

        logger.info("Пользователь выбрал изменить параметры фильтра.")
        self._io["output"]("")
        self._io["output"]("Вы выбрали: '✏️Изменить параметры'")
        self._io["output"]("Введите 'назад', чтобы вернуться на шаг назад.")

        mapping = {
            1: self.ask_salary,
            2: self.ask_name_vacancy,
            3: self.ask_description,
            4: self.ask_url,
            5: self.ask_alternate_url,
        }

        while True:
            self._io["output"]("")
            self._io["output"]("Что хотите изменить?")
            self._io["output"]("1. Зарплата \n2. Название \n3. Описание \n4. Ссылки \n5. Альтернативные ссылки")

            user_input = self._io["input"]("Введите номер: ").strip().lower()
            logger.debug("Выбор пользователя для изменения параметра: '%s'", user_input)

            if user_input == "назад":
                logger.info("Пользователь вернулся назад из режима изменения параметров.")
                self._io["output"]("↩️ Возврат к предыдущему шагу.")
                return "back"

            if not user_input.isdigit() or int(user_input) not in mapping:
                logger.warning(
                    "Неверный ввод при выборе параметра для изменения: '%s'. Ожидалось число от 1 до 5.", user_input
                )
                self._io["output"]("❌ Введите число от 1 до 5.")
                continue

            try:
                logger.info("Пользователь изменяет параметр №%s", user_input)
                mapping[int(user_input)]()
            except FilterCancelled:
                logger.warning("Сборка фильтра отменена пользователем при попытке изменить параметр №%s", user_input)
                self._io["output"]("❌ Изменение параметра отменено.")

            # спрашиваю, хочет ли пользователь изменить ещё
            while True:
                again = self._io["input"]("Хотите изменить ещё один параметр? (да/нет) ").strip().lower()
                logger.debug("Ответ пользователя на вопрос 'изменить ещё один параметр': '%s'", again)

                if again == "да":
                    logger.info("Пользователь решил изменить ещё один параметр.")
                    break  # возвращаемся к выбору параметра
                elif again == "нет":
                    logger.info("Пользователь завершил изменение параметров. Переход к обзору.")
                    self.preview()
                    return None
                else:
                    logger.warning(
                        "Неверный ввод при подтверждении повторного изменения: '%s'. Ожидалось 'да' или 'нет'.", again
                    )
                    self._io["output"]("❌ Неверный ввод. Пожалуйста, введите 'да' или 'нет'.")

    def ask_salary(self) -> None:
        """Запрашивает параметры зарплаты: от, до, валюта (если указана хотя бы одна граница)."""

        logger.info("Пользователь начал изменение параметров зарплаты.")

        self._io["output"]("")
        self._io["output"]("💰 Изменение параметров зарплаты.")
        self._io["output"]("Введите минимальную сумму, максимальную сумму и валюту.")

        try:
            self.ask_salary_from()
            self.ask_salary_to()

            salary_from = self._answers.get("salary_from")
            salary_to = self._answers.get("salary_to")
            logger.debug("Значения зарплаты: salary_from=%s, salary_to=%s", salary_from, salary_to)

            if isinstance(salary_from, (int, float)) or isinstance(salary_to, (int, float)):
                logger.info("Хотя бы одна граница зарплаты указана — запрашиваем валюту.")
                self.ask_currency()
            else:
                logger.info("Границы зарплаты не указаны — валюту запрашивать не будем.")
                self._answers["currency"] = None
                self._io["output"]("💡 Валюта не запрашивается, так как зарплата не указана.")
        except FilterCancelled:
            logger.warning("Пользователь отменил сборку фильтра во время изменения параметров зарплаты.")
            self._io["output"]("❌ Изменение параметров зарплаты отменено.")

    def reset(self) -> None:
        """Очищает состояние фильтра для повторного использования."""

        logger.info("Состояние фильтра очищено для повторного использования.")
        self._answers.clear()
