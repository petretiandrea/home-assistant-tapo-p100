from typing import Any, TypeVar, Union

from homeassistant.config_entries import ConfigEntry
from plugp100.common.functional.either import Either


def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)


T = TypeVar("T")


def value_or_raise(either: Either[T, Exception]) -> T:
    value_or_error: Union[T, Exception] = either.fold(lambda x: x, lambda y: y)
    if isinstance(value_or_error, Exception):
        raise value_or_error
    else:
        return value_or_error


def get_short_model(model: str) -> str:
    return model.lower().split(maxsplit=1)[0]


def get_entry_data(entry: ConfigEntry) -> dict[str, Any]:
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)
    return data
