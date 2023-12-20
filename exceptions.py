class HTTPStatusError(Exception):
    """Сервер вернул ошибку."""


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""


class EmptyDictOrListError(Exception):
    """Пустой словарь или список."""


class EmptyResponseFromAPI(Exception):
    """Пустой ответ от API."""


class InvalidResponseCode(Exception):
    """Не верный код ответа."""


class RequestFailed(Exception):
    """Ошибка запроса."""
