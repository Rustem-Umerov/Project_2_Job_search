from typing import Optional

from job_search.utils.logger_setup import get_logger

logger = get_logger(__name__)


def ask_yes_no(io: dict, question: str) -> Optional[bool]:
    """
    Запрашивает у пользователя ответ 'да' или 'нет'.
    Возвращает None, если введено 'отмена'.
    Если ответ не верный, цикл повторяется.

    :param io: Словарь с ключами "input" и "output"
    :param question: Вопрос для пользователя.
    :return: True — если введено 'да' (y/yes/д/да),
             False — если введено 'нет' (n/no/н/нет),
             None — если введено 'отмена'.
    """
    logger.debug("ask_yes_no: старт вопроса → %s", question)

    while True:
        user_input = io["input"](question).strip().lower()
        logger.debug("ask_yes_no: ввод пользователя → '%s'", user_input)

        if user_input in ("y", "yes", "д", "да"):
            logger.info("ask_yes_no: пользователь ответил ДА")
            return True
        if user_input in ("n", "no", "н", "нет"):
            logger.info("ask_yes_no: пользователь ответил НЕТ")
            return False
        if user_input == "отмена":
            logger.info("ask_yes_no: пользователь ввёл 'отмена' → возврат None")
            return None

        io["output"]("Ошибка: введите 'да', 'нет' или 'отмена'.")
        logger.warning("ask_yes_no: некорректный ввод → '%s'", user_input)


def ask_int(io: dict, question: str, *, min_value: int | None = None, max_value: int | None = None) -> Optional[int]:
    """
    Запрашивает у пользователя целое число.
    Возвращает None, если введено 'отмена'.
    Повторяет вопрос до тех пор, пока не будет введено корректное значение.

    :param io: Словарь с ключами "input" и "output"
    :param question: Вопрос для пользователя.
    :param min_value: Минимально допустимое значение (если задано).
    :param max_value: Максимально допустимое значение (если задано).
    :return: Корректное целое число, введённое пользователем. Или None, если введено 'отмена'.
    """

    logger.debug("ask_int: старт вопроса → %s (min=%s, max=%s)", question, min_value, max_value)

    while True:
        user_input = io["input"](question).strip().lower()
        logger.debug("ask_int: ввод пользователя → '%s'", user_input)

        if user_input == "отмена":
            logger.info("ask_int: пользователь ввёл 'отмена' → возврат None")
            return None

        if not user_input.isdigit():
            io["output"]("Ошибка: ответ должен состоять только из цифр. Если хотите пропустить, введите: 'отмена'.")
            logger.warning("ask_int: некорректный ввод (не цифра) → '%s'", user_input)
            continue

        value = int(user_input)
        logger.debug("ask_int: преобразованное значение → %d", value)

        if min_value is not None and value < min_value:
            io["output"](f"Ошибка: число должно быть не меньше {min_value}.")
            logger.warning("ask_int: значение %d меньше min=%d", value, min_value)
            continue
        if max_value is not None and value > max_value:
            io["output"](f"Ошибка: число должно быть не больше {max_value}.")
            logger.warning("ask_int: значение %d больше max=%d", value, max_value)
            continue

        logger.info("ask_int: принято корректное значение → %d", value)
        return value


def ask_choice(io: dict, menu: dict, *, prompt: str = "Введите номер действия: --> ") -> Optional[int]:
    """
    Универсальный цикл выбора пункта меню.
    Возвращает выбранный номер (ключ из menu).

    :param io: Словарь с ключами "input" и "output"
    :param menu: Словарь вида {номер: (название, значение)}
    :param prompt: Текст запроса для пользователя
    :return: Выбранный номер (int)
    """

    logger.debug("ask_choice: старт выбора из меню (%s пунктов)", len(menu))

    while True:
        user_input = io["input"](prompt).strip()
        logger.debug("ask_choice: ввод пользователя → '%s'", user_input)

        valid_choices = [k for k in menu if isinstance(k, int)]
        if not user_input.isdigit():
            io["output"](f"Ошибка: нужно ввести цифру от {min(valid_choices)} до {max(valid_choices)}.")
            logger.warning("ask_choice: некорректный ввод (не цифра) → '%s'", user_input)
            continue

        choice = int(user_input)
        if choice not in menu:
            io["output"](f"Ошибка: такого пункта нет. Введите цифру от {min(valid_choices)} до {max(valid_choices)}.")
            logger.warning("ask_choice: некорректный ввод (нет пункта) → %d", choice)
            continue

        logger.info(
            "ask_choice: выбран пункт меню → %d (%s)",
            choice,
            menu[choice][0] if isinstance(menu[choice], (list, tuple)) else menu[choice],
        )
        return choice


def next_step(*, io: dict, menu: dict[int, tuple[str, str]], choice: int, default: str = "main_menu") -> str:
    """
    Определяет следующий шаг приложения по выбору пользователя.
    Если выбранный пункт меню отсутствует, по умолчанию функция возвращает "main_menu".

    :param io: Словарь с функциями "input"/"output"
    :param menu: Словарь вида {номер: (название, имя_шага)}
    :param choice: Выбранный пользователем номер
    :param default: Шаг по умолчанию, если выбор некорректный
    :return: Имя следующего шага (str)
    """
    logger.debug("next_step вызван с choice=%r", choice)

    step = menu.get(choice)
    if step is None:
        io["output"]("⚠️ Некорректный выбор, возвращаемся в главное меню.")
        logger.warning("ask_choice вернул None, переход в %s", default)
        return default

    title, step_name = step
    logger.info("Выбран пункт меню %d → '%s' → переход к шагу '%s'", choice, title, step_name)
    io["output"](f"➡️ Вы выбрали: {title}\n")
    return step_name


def render_menu(*, io: dict, menu: dict) -> None:
    """
    Выводит меню в консоль.
    Не возвращает значения — отвечает только за вывод.

    :param io: Словарь с функциями ввода/вывода.
    :param menu: Словарь меню вида {num: (title, action)}.
    :return: None. Функция отвечает только за вывод.
    """

    for num, (title, action) in menu.items():
        try:
            if isinstance(num, int):
                line = f"{num}. {title}"
            else:
                line = str(title)
            io["output"](line)
        except Exception as e:
            logger.exception(f"Ошибка при выводе пункта меню {num}: {e}")
    io["output"]("")


def render_vacancies_page(
    *, io: dict, vacancies: list, current_page: int, page_size: int, total_vacancies: int, global_offset: int = 0
) -> tuple[int, int]:
    """
    Отображает список вакансий для текущей страницы в виде таблицы:
    № на стр. | Глобальный индекс | Вакансия
    Возвращает кортеж (start, end) — индексы диапазона показанных вакансий.

    :param io: Словарь с функциями ввода/вывода.
    :param vacancies: Список вакансий (объекты или строки), из которого берётся срез.
    :param current_page: Номер текущей страницы (начиная с 1).
    :param page_size: Количество вакансий, отображаемых на одной странице.
    :param total_vacancies: Общее количество вакансий в списке.
    :param global_offset: Это номер, с которого начинается глобальная нумерация на текущей странице.
    :return: Tuple[int, int] — кортеж (start, end), где:
             start (int) — индекс первой показанной вакансии (0-based),
             end (int) — индекс последней показанной вакансии (не включительно)
    """

    if total_vacancies == 0:
        io["output"]("Список пуст.")
        logger.debug("Список с вакансиями пуст (total_vacancies == 0)")
        return 0, 0

    start = (current_page - 1) * page_size
    end = min(start + page_size, total_vacancies)

    if total_vacancies == 1:
        io["output"]("Страница 1. Вакансия 1 из 1:")
        logger.debug("В списке вакансий: 1 вакансия (total_vacancies == 1)")
    else:
        io["output"](f"Страница {current_page}. Вакансии {start + 1}–{end} из {total_vacancies}:")
        logger.debug(f"Вывод вакансий {start + 1}–{end} из {total_vacancies} (страница {current_page})")
    io["output"]("")

    # Заголовок таблицы
    io["output"](f"{'№ на стр.':<8}{'Глоб. №':<10}{'Вакансия'}")
    io["output"]("-" * 50)

    for local_idx, vacancy in enumerate(vacancies[start:end], start=1):
        global_idx = global_offset + local_idx
        io["output"](f"{local_idx:<8}{global_idx:<10}{vacancy}")
        io["output"]("")

    return start, end
