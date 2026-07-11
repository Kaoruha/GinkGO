"""枚举基类 EnumBase：提供 enum_convert/from_int/to_int/validate_input，供 DB 存储与业务层互转。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from enum import Enum


class EnumBase(Enum):
    @classmethod
    def enum_convert(cls, string):
        r = None
        try:
            r = cls[string.upper()]
        except Exception as e:
            return
        return r

    @classmethod
    def from_int(cls, value):
        """Convert integer value to enum"""
        if isinstance(value, cls):
            return value
        if value is None:
            return None
        try:
            return cls(int(value))
        except (ValueError, TypeError):
            return None

    def to_int(self):
        """Convert enum to integer value"""
        return self.value

    @classmethod
    def validate_input(cls, value):
        """Validate and convert input (enum or int) to integer for database storage"""
        if value is None:
            return None
        if isinstance(value, cls):
            return value.value
        if isinstance(value, int):
            # Validate that the int value exists in enum
            try:
                cls(value)
                return value
            except ValueError:
                return None
        return None

    # def __repr__(self):
    #     return self.value


__all__ = ['EnumBase']
