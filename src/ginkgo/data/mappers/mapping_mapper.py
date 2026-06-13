"""MappingMapper — 任意映射 ORM 模型 → Mapping Entity（ADR-010）。

承接原 Mapping.from_model 内嵌逻辑（entities/mapping.py:226-293）。

特例：from_model 带 mapping_type 形参（mapping_type 决定映射语义，如
"EnginePortfolio"/"PortfolioFile"，调用方必传）。原码用潜在键字段
[engine_id, portfolio_id, file_id, handler_id] 智能检测 left_key/right_key。

写路径特例：原码无 to_model（Mapping 只读）。grep 确认无 MMapping 写路径
经 entity.to_model。忠实搬运 → to_model raise NotImplementedError。

已知问题（#6126，留后续 issue 不擅修）：
- 模型两映射键都为空时，from_model 走 left_key or ""=空串传构造器，触发
  Mapping.__init__ 校验 ValueError（mapping.py:60-63）。原码 left_key or ""
  是 None→"" 兜底，但空串仍被构造器拒。

铁律：不 import CRUD；不含 to_dataframe（DF 出口留 CRUD）。
"""
from typing import List

from ginkgo.entities import Mapping
from ginkgo.enums import SOURCE_TYPES


class MappingMapper:
    """Mapping 通用映射对象转换。无状态，全部静态方法。

    接收任意映射 ORM 模型（非单一 M* 类），故 from_model 无 isinstance 守卫
    （duck-typing：靠 hasattr 检测潜在键字段）。
    """

    # ------------------------------------------------------------------
    # ORM → Entity
    # ------------------------------------------------------------------
    @staticmethod
    def from_model(model, mapping_type: str = "") -> Mapping:
        """任意映射模型 → Mapping Entity。

        mapping_type 形参保留（决定映射语义，调用方必传）。

        忠实原码（mapping.py:226-293）：遍历 potential_keys 智能检测 left/right；
        metadata 复制模型非核心属性；uuid/source 提取。
        """
        # 常见的映射键字段（忠实原码 mapping.py:241）
        potential_keys = ['engine_id', 'portfolio_id', 'file_id', 'handler_id']

        left_key = None
        right_key = None
        left_name = ""
        right_name = ""

        # 智能检测左右键字段（忠实原码 mapping.py:248-258）
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

        # 构建元数据字典（忠实原码 mapping.py:261-278）
        metadata = {}
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

        # 提取基础信息（忠实原码 mapping.py:281-282）
        uuid = str(getattr(model, 'uuid', ''))
        source = getattr(model, 'source', SOURCE_TYPES.VOID)

        return Mapping(
            left_key=left_key or "",
            right_key=right_key or "",
            left_name=left_name,
            right_name=right_name,
            mapping_type=mapping_type or Mapping.__name__.replace('Mapping', ''),
            uuid=uuid,
            metadata=metadata,
            source=source,
        )

    @staticmethod
    def from_models(models, mapping_type: str = "") -> List[Mapping]:
        return [MappingMapper.from_model(m, mapping_type) for m in models]

    # ------------------------------------------------------------------
    # Entity → ORM（原码无写路径）
    # ------------------------------------------------------------------
    @staticmethod
    def to_model(entity: Mapping):
        """Mapping 只读，原码无 to_model。忠实搬运 NotImplementedError。"""
        raise NotImplementedError("Mapping 无写路径，to_model 未实现")
