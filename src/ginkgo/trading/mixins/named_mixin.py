"""
名称管理Mixin

提供组件名称管理功能
"""


class NamedMixin:
    """名称管理Mixin，提供组件名称管理功能"""

    def __init__(self, name: str = "", *args, **kwargs):
        """
        初始化名称管理

        Args:
            name: 组件名称
        """
        self._name = str(name) if name else ""
        super().__init__(*args, **kwargs)

    @property
    def name(self) -> str:
        """获取组件名称"""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """设置组件名称"""
        if not isinstance(value, str):
            raise ValueError("Name must be a string.")
        self._name = value

    def set_name(self, name: str) -> str:
        """
        设置组件名称

        Args:
            name: 新的组件名称

        Returns:
            str: 设置后的名称
        """
        self._name = str(name)
        return self._name