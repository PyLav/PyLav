from __future__ import annotations


class FilterMixin:
    _default: FilterMixin = None
    _off = False

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __hash__(self):
        """Overrides the default implementation"""
        return hash(tuple(sorted(self.__dict__.items())))

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
        return NotImplemented

    def is_default(self) -> bool:
        if self._default is None:
            self._default = self.default()
        return self == self._default
