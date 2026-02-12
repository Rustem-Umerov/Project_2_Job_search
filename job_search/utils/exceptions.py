class FilterCancelled(Exception):
    """Исключение, выбрасываемое при отмене фильтра пользователем."""

    pass


class UnexpectedStatusError(Exception):
    """Исключение, выбрасываемое, если валидирующая функция вернула неожиданный статус."""

    pass
