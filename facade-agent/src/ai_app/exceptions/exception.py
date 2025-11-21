class AIException(Exception):
    def __init__(self, http_code: str, msg: str, original_exception=None):
        self.http_code = http_code
        self.message = get_message(msg)
        self.original_exception = original_exception
        super().__init__(self.message)

    def get_message(self):
        return self.message

    def __str__(self):
        return get_str(self.message, self.original_exception)


def get_str(message, exception):
    if exception:
        return f"{message} - original exception: {type(exception).__name__}: {str(exception)}"
    else:
        return message


def get_message(message):
    if message is not None:
        return message[:349]  # retaining only first 349
    return message
