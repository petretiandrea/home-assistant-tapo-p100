from logging import Logger
from typing import Optional, TypeVar

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from plugp100.common.functional.tri import Try
from plugp100.errors import InvalidAuthentication, TapoError, TapoException

T = TypeVar("T")


def value_optional(tri: Try[T]) -> Optional[T]:
    return tri.get() if tri.is_success() else None


def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)


def get_short_model(model: str) -> str:
    return model.lower().split(maxsplit=1)[0]


def hass_to_tapo_brightness(brightness: float | None) -> float | None:
    if brightness is not None:
        return round((brightness / 255) * 100)
    return brightness


def tapo_to_hass_brightness(brightness: float | None) -> float | None:
    if brightness is not None:
        return round((brightness * 255) / 100)
    return brightness


def hass_to_tapo_color_temperature(
    color_temp: int | None, kelvin: (int, int)
) -> int | None:
    if color_temp is not None:
        constraint_color_temp = clamp(color_temp, kelvin[0], kelvin[1])
        return clamp(
            constraint_color_temp,
            min_value=kelvin[0],
            max_value=kelvin[1],
        )
    return color_temp


def tapo_to_hass_color_temperature(
    color_temp: int | None, colors: (int, int)
) -> int | None:
    if color_temp is not None and color_temp > 0:
        return clamp(
            color_temp,
            min_value=colors[0],
            max_value=colors[1],
        )
    return None


def _raise_from_tapo_exception(exception: Exception, logger: Logger):
    logger.error("Tapo exception: %s", str(exception))
    if isinstance(exception, InvalidAuthentication):
        raise ConfigEntryAuthFailed from exception
    if (
        isinstance(exception, TapoException)
        and exception.error_code == TapoError.INVALID_CREDENTIAL.value
    ):
        raise ConfigEntryAuthFailed from exception
    raise UpdateFailed(f"Error tapo exception: {exception}") from exception
