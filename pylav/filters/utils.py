from __future__ import annotations

from abc import abstractmethod

from deepdiff import DeepDiff


class FilterMixin:
    __slots__ = ("_default", "_off", "_default_value")

    def __init__(self):
        self._default = None
        self._off = True
        self._default_value = None

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, self.__class__):
            return bool(DeepDiff(self.to_json(), other.to_json(), ignore_order=True, max_diffs=1))
        return NotImplemented

    @abstractmethod
    def to_json(self) -> dict:
        """Returns a dictionary representation of the Filter without the state key"""
        raise NotImplementedError

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(tuple(sorted(self.to_json().items())))

    @property
    def off(self) -> bool:
        return True if self.is_default() else self._off

    @off.setter
    def off(self, value: bool):
        self._off = value

    @property
    def changed(self) -> bool:
        return self.off is False

    @classmethod
    def default(cls) -> FilterMixin:
        return cls()

    def is_default(self) -> bool:
        if self._default is None:
            self._default = self.default()
        return bool(DeepDiff(self.to_json(), self._default.to_json(), ignore_order=True, max_diffs=1))
