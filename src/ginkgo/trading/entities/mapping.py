# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Mapping映射实体提供对象关联关系定义支持引擎组合映射和处理器组合映射实现组件关联支持交易系统功能和组件集成提供完整业务支持






"""
通用映射业务对象

用于表示系统中各种映射关系，如：
- Engine与Handler的映射 (engine_id ↔ handler_id)
- Engine与Portfolio的映射 (engine_id ↔ portfolio_id)
- Portfolio与File的映射 (portfolio_id ↔ file_id)
- 其他键值对映射关系
"""

from typing import Any, Dict, Optional
from ginkgo.trading.core.base import Base
from ginkgo.enums import COMPONENT_TYPES, SOURCE_TYPES


class Mapping(Base):
    """
    通用映射业务对象

    表示系统中各种键值对映射关系，提供统一的业务接口。
    继承自Base类，使用COMPONENT_TYPES.ENGINE标识。

    Examples:
        - Engine-Handler映射: left_key="engine_id", right_key="handler_id"
        - Engine-Portfolio映射: left_key="engine_id", right_key="portfolio_id"
        - Portfolio-File映射: left_key="portfolio_id", right_key="file_id"
    """

    def __init__(
        self,
        left_key: str,              # 左侧键 (如engine_id, portfolio_id)
        right_key: str,             # 右侧键 (如handler_id, portfolio_id)
        left_name: str = "",         # 左侧名称描述 (如"Engine", "Portfolio")
        right_name: str = "",          # 右侧名称描述 (如"Handler", "Portfolio", "File")
        mapping_type: str = "",         # 映射类型描述
        uuid: str = "",              # 实例唯一标识
        metadata: Optional[Dict[str, Any]] = None,    # 扩展元数据
        source: SOURCE_TYPES = SOURCE_TYPES.VOID,
        *args,
        **kwargs
    ):
        # 使用Base类初始化，传入ENGINE组件类型
        super(Mapping, self).__init__(
            uuid=uuid,
            component_type=COMPONENT_TYPES.ENGINE,
            *args,
            **kwargs
        )

        # 验证核心字段
        if not left_key:
            raise ValueError("left_key cannot be empty.")
        if not right_key:
            raise ValueError("right_key cannot be empty.")

        # 设置映射关系属性
        self._left_key = left_key
        self._right_key = right_key
        self._left_name = left_name
        self._right_name = right_name
        self._mapping_type = mapping_type
        self._metadata = metadata or {}
        self._source = source

    @property
    def left_key(self) -> str:
        """左侧键标识符 (engine_id/portfolio_id/file_id等)"""
        return self._left_key

    @property
    def right_key(self) -> str:
        """右侧键标识符 (handler_id/portfolio_id/file_id等)"""
        return self._right_key

    @property
    def mapping_key(self) -> str:
        """完整映射键 (格式: left_key↔right_key)"""
        return f"{self._left_key}↔{self._right_key}"

    @property
    def left_name(self) -> str:
        """左侧名称描述"""
        return self._left_name

    @property
    def right_name(self) -> str:
        """右侧名称描述"""
        return self._right_name

    @property
    def mapping_type(self) -> str:
        """映射类型描述"""
        return self._mapping_type

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        获取元数据

        Args:
            key: 元数据键
            default: 默认值

        Returns:
            元数据值
        """
        return self._metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """
        设置元数据

        Args:
            key: 元数据键
            value: 元数据值
        """
        self._metadata[key] = value

    def metadata_items(self) -> list:
        """获取所有元数据项"""
        return list(self._metadata.items())

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            包含所有映射数据的字典
        """
        result = {
            'uuid': self.uuid,
            'left_key': self._left_key,
            'right_key': self._right_key,
            'left_name': self._left_name,
            'right_name': self._right_name,
            'mapping_type': self._mapping_type,
            'metadata': self._metadata.copy(),
            'source': self._source.value if hasattr(self._source, 'value') else self._source
        }
        return result

    def __getitem__(self, key: str) -> Any:
        """
        支持字典式访问

        Args:
            key: 属性键

        Returns:
            属性值
        """
        # 优先返回核心属性
        if key in ['left_key', 'right_key', 'left_name', 'right_name', 'mapping_type']:
            return getattr(self, f'_{key}')

        # 然后查找元数据
        return self._metadata.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """
        支持字典式设置

        Args:
            key: 属性键
            value: 属性值
        """
        # 优先设置核心属性
        if key in ['left_key', 'right_key', 'left_name', 'right_name', 'mapping_type']:
            setattr(self, f'_{key}', value)
        else:
            # 设置元数据
            self._metadata[key] = value

    def keys(self) -> list:
        """获取所有可用键"""
        core_keys = ['left_key', 'right_key', 'left_name', 'right_name', 'mapping_type']
        return core_keys + list(self._metadata.keys())

    def items(self) -> list:
        """获取所有键值对"""
        core_items = [
            ('left_key', self._left_key),
            ('right_key', self._right_key),
            ('left_name', self._left_name),
            ('right_name', self._right_name),
            ('mapping_type', self._mapping_type)
        ]
        return core_items + list(self._metadata.items())

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取属性值，支持默认值

        Args:
            key: 属性键
            default: 默认值

        Returns:
            属性值或默认值
        """
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: str) -> bool:
        """支持in操作符"""
        return key in self.keys()

    def __str__(self) -> str:
        """字符串表示"""
        return f"Mapping({self.mapping_key}: {self._left_name}↔{self._right_name})"

    def __repr__(self) -> str:
        """调试表示"""
        return f"Mapping(left_key='{self._left_key}', right_key='{self._right_key}', type='{self._mapping_type}', uuid='{self.uuid}')"

    @classmethod
    def from_model(cls, model, mapping_type: str = "", *args, **kwargs):
        """
        从任意映射模型创建Mapping业务对象

        Args:
            model: 任意的映射模型实例
            mapping_type: 映射类型描述
            *args: 额外参数
            **kwargs: 额外关键字参数

        Returns:
            Mapping业务对象实例
        """
        # 常见的映射键字段
        potential_keys = ['engine_id', 'portfolio_id', 'file_id', 'handler_id']

        left_key = None
        right_key = None
        left_name = ""
        right_name = ""

        # 智能检测左右键字段
        for key in potential_keys:
            if hasattr(model, key):
                value = getattr(model, key)
                if value and value.strip():  # 确保值不为空
                    if left_key is None:
                        left_key = value
                        left_name = key.replace('_id', '') + '_name'
                    else:
                        right_key = value
                        right_name = key.replace('_id', '') + '_name'

        # 构建元数据字典
        metadata = {}

        # 复制模型的所有属性到元数据
        for attr in dir(model):
            if not attr.startswith('_') and not callable(getattr(model, attr)):
                value = getattr(model, attr)
                if value is not None:
                    # 处理特殊类型
                    if hasattr(value, 'value'):  # 枚举类型
                        value = value.value
                    elif hasattr(value, 'isoformat'):  # 时间类型
                        value = value.isoformat()
                    elif hasattr(value, '__str__'):  # UUID等类型
                        value = str(value)

                    # 避免覆盖核心字段
                    if attr not in ['left_key', 'right_key', 'left_name', 'right_name']:
                        metadata[attr] = value

        # 提取基础信息
        uuid = str(getattr(model, 'uuid', ''))
        source = getattr(model, 'source', SOURCE_TYPES.VOID)

        return cls(
            left_key=left_key or "",
            right_key=right_key or "",
            mapping_type=mapping_type or cls.__name__.replace('Mapping', ''),
            uuid=uuid,
            metadata=metadata,
            source=source,
            *args,
            **kwargs
        )