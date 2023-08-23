from typing import Optional
from typing import TypeVar

from plugp100.common.functional.tri import Try

T = TypeVar("T")


def value_optional(tri: Try[T]) -> Optional[T]:
    return tri.get() if tri.is_success() else None


def clamp(value, min_value, max_value):
    return max(min(value, max_value), min_value)


def get_short_model(model: str) -> str:
    return model.lower().split(maxsplit=1)[0]
