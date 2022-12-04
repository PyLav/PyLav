from __future__ import annotations

from abc import abstractmethod
from typing import Any

from deepdiff import DeepDiff  # type: ignore

from pylav.logging import getLogger

LOGGER = getLogger("PyLav.Filters")


class FilterMixin:
    __slots__ = ("_default", "_default_value")

    def __init__(self) -> None:
        self._default: FilterMixin | None = None
        self._default_value = None

    def __eq__(self, other: Any) -> bool:
        """Overrides the default implementation"""
        if isinstance(other, self.__class__):
            return bool(
                DeepDiff(
                    self.to_dict(),
                    other.to_dict(),
                    ignore_order=True,
                    max_passes=1,
                    cache_size=100,
                    exclude_paths=["root['name']"],
                )
            )
        return NotImplemented

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the Filter"""
        raise NotImplementedError

    def __hash__(self) -> int:
        """Overrides the default implementation"""
        return hash(tuple(sorted(self.to_dict().items())))

    def __bool__(self) -> bool:
        return self.changed

    @property
    def off(self) -> bool:
        return not self.changed

    @property
    def changed(self) -> bool:
        if self._default is None:
            self._default = self.default()

        assert self._default is not None

        changed = DeepDiff(
            self.to_dict(),
            self._default.to_dict(),
            ignore_order=True,
            max_passes=1,
            cache_size=100,
            exclude_paths=["root['name']"],
        )
        return bool(changed)

    @classmethod
    def default(cls) -> FilterMixin:
        return cls()
