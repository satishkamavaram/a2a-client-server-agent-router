import contextvars
from typing import Optional

access_token_var = contextvars.ContextVar('access_token', default=None)


def get_access_token() -> Optional[str]:
    return access_token_var.get()


def set_access_token(token: str):
    access_token_var.set(token)


def clear_access_token() -> None:
    access_token_var.set(None)
