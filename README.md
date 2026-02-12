# Описание проекта

Project_2_Job_search — это консольное приложение для поиска вакансий, 
их фильтрации и удобного отображения.
Проект позволяет получать вакансии из разных источников (например, HeadHunter API или локальных файлов), 
сортировать их по различным параметрам и выводить в удобном формате.
Цель проекта — предоставить простой инструмент для анализа рынка труда 
и выбора подходящих предложений.

# Функциональность

Загрузка вакансий из API или JSON‑файлов.
### Фильтрация по:
Зарплате, ключевым словам, региону
Можно отсортировать по зарплате.

# Архитектура проекта
Проект разделён на логические модули:

[base_api.py](job_search/api/base_api.py) - Абстрактный класс VacancyAPI. Базовый интерфейс для всех сервисов вакансий. 
Обеспечивает единую сигнатуру для работы с разными API.

[head_hunter_api.py](job_search/api/head_hunter_api.py) - Класс-наследник от абстрактного класса VacancyAPI.
Реализует взаимодействие с API hh.ru для получения вакансий.

[types.py](job_search/api/types.py) - Унифицированный формат результата поиска вакансий.
Все API‑классы должны возвращать словарь этой структуры.

[filter_formatters.py](job_search/filters/filter_formatters.py) - Абстрактный класс для форматирования фильтра под конкретный API.

[hh_formatter.py](job_search/filters/hh_formatter.py) - Форматирует фильтры для вакансий HH.

[interactive_input.py](job_search/filters/interactive_input.py) - Класс для интерактивного сбора фильтра от пользователя.

[preview_renderer.py](job_search/filters/preview_renderer.py) - Отвечает за формирование и вывод человекочитаемого обзора собранных параметров фильтра.
Получает словарь ответов пользователя и абстракцию ввода/вывода.

[vacancy_filter.py](job_search/filters/vacancy_filter.py) - Класс для фильтрации объектов Vacancy по заданным условиям.

[job_search_app.py](job_search/models/job_search_app.py) - Класс-контроллер приложения (state machine), который управляет сценарием взаимодействия с пользователем.
Он не реализует бизнес‑логику сам, а координирует работу других классов: API‑клиентов, фильтров, сортировщиков, хранилища.

[vacancy.py](job_search/models/vacancy.py) - Класс для создания объектов из вакансий полученных от АПИ.

[base_storage.py](job_search/storage/base_storage.py) - Абстрактный базовый класс для хранилищ вакансий.

[json_saver.py](job_search/storage/json_saver.py) - Реализация хранилища вакансий на основе JSON-файла.

[exceptions.py](job_search/utils/exceptions.py) - Модуль с классами-исключениями. 

[filters.py](job_search/utils/filters.py) - Модуль с функциями для сортировки и фильтрации вакансии по зарплате.

[input_helpers.py](job_search/utils/input_helpers.py) - Модуль с вспомогательными функциями.

[logger_setup.py](job_search/utils/logger_setup.py) - Модуль с логгером.

[vacancy_fields_validators.py](job_search/utils/vacancy_fields_validators.py) - Модуль с вспомогательными функциями.

[main.py](job_search/main.py) - Модуль, с главной функцией, для запуска приложения.




