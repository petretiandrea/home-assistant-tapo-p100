from typing import Optional
from typing import TypeVar

from homeassistant.util.color import (
    color_temperature_kelvin_to_mired as kelvin_to_mired,
)
from homeassistant.util.color import (
    color_temperature_mired_to_kelvin as mired_to_kelvin,
)
from plugp100.common.functional.tri import Try

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


# Mireds and Kelving are min, max tuple
def hass_to_tapo_color_temperature(
    color_temp: int | None, mireds: (int, int), kelvin: (int, int)
) -> int | None:
    if color_temp is not None:
        constraint_color_temp = clamp(color_temp, mireds[0], mireds[1])
        return clamp(
            mired_to_kelvin(constraint_color_temp),
            min_value=kelvin[0],
            max_value=kelvin[1],
        )
    return color_temp


def tapo_to_hass_color_temperature(
    color_temp: int | None, mireds: (int, int)
) -> int | None:
    if color_temp is not None and color_temp > 0:
        return clamp(
            kelvin_to_mired(color_temp),
            min_value=mireds[0],
            max_value=mireds[1],
        )
    return None
