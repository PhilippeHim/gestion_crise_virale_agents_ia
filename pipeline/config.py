import os
from typing import Callable, TypeVar


T = TypeVar("T")


try:
    from decouple import config as _decouple_config
except ModuleNotFoundError:
    _decouple_config = None


def config(key: str, default=None, cast: Callable[[str], T] | None = None):
    if _decouple_config is not None:
        if cast is None:
            return _decouple_config(key, default=default)
        return _decouple_config(key, default=default, cast=cast)

    valeur = os.getenv(key)
    if valeur is None:
        return default
    if cast is None:
        return valeur
    if cast is bool:
        return valeur.lower() in {"1", "true", "yes", "on"}
    return cast(valeur)
