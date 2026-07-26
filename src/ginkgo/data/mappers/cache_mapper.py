# Upstream: RedisCRUD (Redis 基础操作)、api/core/redis_client.py (异步回测进度)
# Downstream: redis-py wire (JSON)、pydantic (β 运行期校验)
# Role: CacheMapper — Redis 边界 wire↔DTO 转换收敛层 (ADR-025 第④步)


"""
CacheMapper — Redis 边界 wire↔DTO 转换收敛层 (ADR-025 第④步)。

收敛既有 4 处平行 ``json.dumps``/``json.loads``:

- ``redis_crud.RedisCRUD.set``     — ``json.dumps(value)`` (ensure_ascii=True 默认)
- ``redis_crud.RedisCRUD.hset``    — 同上 (dict/list); 非聚合走 ``str(value)``
- ``redis_crud.RedisCRUD.get/hget``— ``json.loads`` + **静默** raw-string fallback
- ``api/core/redis_client.py``     — ``json.dumps(..., ensure_ascii=False)``

本类统一:

- **encode**: ``json.dumps(value, ensure_ascii=False)`` — CJK 可读、体积更小。
  ``json.loads`` 双向兼容 ensure_ascii=True 的旧键, 故翻转 round-trip 安全。
- **decode**: ``json.loads``。malformed wire 抛 ``json.JSONDecodeError``
  (交 IO 层决定 fallback 策略, 本纯 transform **不吞**)。opt-in ``dto_cls``
  走 β 运行期校验: ``model_validate`` 失败 → ``ValueError`` 响亮报错 (遵 #4652,
  不静默兜底)。

与 ADR-010 Entity Mapper (``from_model``/``to_model``/...) 不同: CacheMapper 是
IO 边界 wire 转换, 非 Entity↔ORM↔DTO 三态互转, 故不混入 Entity mapper 五方法矩阵。
"""

import json
from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class CacheEntry(BaseModel):
    """缓存条目标记基类 (ADR-025)。

    业务侧 typed cache DTO 继承本类, 经 ``CacheMapper.decode(raw, dto_cls=X)``
    做 β 运行期校验::

        class BacktestProgressEntry(CacheEntry):
            progress: float
            stage: str

        prog = CacheMapper.decode(raw, BacktestProgressEntry)

    注意:
    - 本类是 marker/基类, **不强加 wire 信封** (不包 ``payload`` 字段) ——
      保持与既有裸 dict 缓存键 wire 兼容; 命名表其 "被缓存的 typed 条目" 角色。
    - 与 ``data.streaming.cache.cache_manager.CacheEntry`` (内存 LRU 账本)
      同名不同义, 模块隔离 (本类在 ``data.mappers.cache_mapper``)。
    """


class CacheMapper:
    """Redis wire↔Python 转换 (ADR-025 第④步 CacheMapper)。

    所有方法 ``@staticmethod``, 无状态, 纯 transform —— 不夹日志、不做 fallback
    (缓存 best-effort 策略归 IO 层 ``RedisCRUD``/``redis_client``)。
    """

    @staticmethod
    def encode(value: Any) -> str:
        """Python → Redis wire (JSON, ``ensure_ascii=False``)。

        Args:
            value: 任意 JSON 可序列化对象 (dict/list/标量)。

        Returns:
            JSON 字符串。``ensure_ascii=False`` → CJK 以 UTF-8 直存 (非 ``\\uXXXX``)。

        Raises:
            TypeError: value 含非 JSON 可序列化对象 (交调用方 broad-except 决策,
                同既有 ``RedisCRUD.set`` 语义)。
        """
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def decode(raw: Any, dto_cls: Optional[Type[T]] = None) -> Any:
        """Redis wire → Python。

        Args:
            raw: Redis 返回值 (``str`` 或 ``bytes``; ``bytes`` 自动 decode utf-8;
                ``None`` → 返回 ``None``)。
            dto_cls: 可选 pydantic 模型。

                - 传入 → **β 校验**: ``raw`` 经 ``json.loads`` 后须符 ``dto_cls``
                  schema, 否则 ``ValueError`` (响亮报错, 遵 #4652 不静默兜底);
                  成功返回该模型实例。
                - 不传 → 返回 ``json.loads`` 解析值 (纯 Python 对象)。

        Returns:
            反序列化后的 Python 对象; ``dto_cls`` 传入时返回该模型实例;
            ``raw is None`` 时返回 ``None``。

        Raises:
            json.JSONDecodeError: wire 非 JSON (交 IO 层决定 fallback)。
            ValueError: ``dto_cls`` 传入但 wire 不符 schema (β 校验失败)。
        """
        if raw is None:
            return None
        data_str = raw if isinstance(raw, str) else raw.decode("utf-8")

        parsed = json.loads(data_str)  # JSONDecodeError 透传给 IO 层

        if dto_cls is not None:
            try:
                return dto_cls.model_validate(parsed)
            except ValidationError as e:
                raise ValueError(
                    f"CacheMapper.decode: wire 不符 {dto_cls.__name__} schema: {e}"
                ) from e
        return parsed
