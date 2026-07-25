# Issue: ADR-025 第④步 (Redis CacheMapper + CacheEntry 类型化)
# Upstream: src/ginkgo/data/mappers/cache_mapper.py (CacheMapper / CacheEntry)
# Downstream: pytest, pydantic
# Role: 验 CacheMapper encode/decode wire 契约 + β 运行期校验响亮报错 (遵 #4652)

"""ADR-025 第④步 Redis CacheMapper — wire 转换 + β 校验测试。

证明四件事:

- **encode 契约**: ``ensure_ascii=False`` (CJK 直存 UTF-8 非 ``\\uXXXX``), dict/list/
  标量皆可; 非可序列化对象 TypeError 响亮报错。
- **decode 契约**: str/bytes 自适应; malformed wire 抛 ``json.JSONDecodeError``
  (纯 transform **不吞**, fallback 归 IO 层); ``None`` 透传。
- **β 运行期校验** (遵 #4652): ``decode(raw, dto_cls=X)`` 时 wire 须符 schema, 否则
  ``ValueError`` 响亮报错 (不静默兜底); 成功返模型实例。
- **wire 兼容**: ``ensure_ascii=False`` 新写键可被旧 ensure_ascii=True 读法 (``json.loads``)
  还原 — 翻转 round-trip 安全 (redis_crud 既有键零迁移)。
"""

import json

import pytest
from pydantic import ValidationError

from ginkgo.data.mappers.cache_mapper import CacheEntry, CacheMapper
from ginkgo.data.mappers import CacheMapper as ExportedCacheMapper
from ginkgo.data.mappers import CacheEntry as ExportedCacheEntry


class _ProgressEntry(CacheEntry):
    """测试用 typed cache DTO (证 β 校验)。"""

    progress: float
    stage: str


# ----------------------------------------------------------------------
# encode 契约
# ----------------------------------------------------------------------


class TestCacheMapperEncode:
    def test_encode_dict_round_trips(self):
        wire = CacheMapper.encode({"a": 1, "b": [2, 3]})
        assert json.loads(wire) == {"a": 1, "b": [2, 3]}

    def test_encode_ensure_ascii_false_for_cjk(self):
        # ensure_ascii=False: 中文以 UTF-8 字节直存, 不转 \uXXXX 转义
        wire = CacheMapper.encode({"name": "回测"})
        assert "回测" in wire
        assert "\\u" not in wire  # 无 ASCII 转义

    def test_encode_scalar_types(self):
        assert CacheMapper.encode(42) == "42"
        assert CacheMapper.encode(1.5) == "1.5"
        assert CacheMapper.encode(True) == "true"  # JSON 小写
        assert CacheMapper.encode("hi") == '"hi"'  # 字符串加引号

    def test_encode_raises_type_error_on_non_serializable(self):
        # 非可序列化对象响亮报错 (交调用方 broad-except 决策, 不静默兜底)
        with pytest.raises(TypeError):
            CacheMapper.encode(object())


# ----------------------------------------------------------------------
# decode 契约 (默认路径, 无 dto_cls)
# ----------------------------------------------------------------------


class TestCacheMapperDecode:
    def test_decode_str_json(self):
        assert CacheMapper.decode('{"x": 1}') == {"x": 1}

    def test_decode_bytes_auto_utf8(self):
        # bytes 自动 decode (redis-py decode_responses=False 路径)
        assert CacheMapper.decode(b'{"x": 2}') == {"x": 2}

    def test_decode_cjk_round_trip(self):
        wire = CacheMapper.encode({"name": "策略", "n": 1})
        assert CacheMapper.decode(wire) == {"name": "策略", "n": 1}

    def test_decode_none_passthrough(self):
        assert CacheMapper.decode(None) is None

    def test_decode_malformed_raises(self):
        # 纯 transform: 非 JSON 抛 JSONDecodeError (fallback 归 IO 层, 此处不吞)
        with pytest.raises(json.JSONDecodeError):
            CacheMapper.decode("not-json{")


# ----------------------------------------------------------------------
# β 运行期校验 (#4652: 失败响亮报错, 不静默兜底)
# ----------------------------------------------------------------------


class TestCacheMapperBetaValidation:
    def test_typed_decode_returns_model_instance(self):
        wire = CacheMapper.encode({"progress": 0.5, "stage": "running"})
        entry = CacheMapper.decode(wire, dto_cls=_ProgressEntry)
        assert isinstance(entry, _ProgressEntry)
        assert entry.progress == 0.5
        assert entry.stage == "running"

    def test_typed_decode_rejects_wrong_schema(self):
        # wire 缺必填字段 → β 校验失败 → ValueError (不返 None/不兜底)
        wire = CacheMapper.encode({"progress": 0.5})  # 缺 stage
        with pytest.raises(ValueError):
            CacheMapper.decode(wire, dto_cls=_ProgressEntry)

    def test_typed_decode_rejects_wrong_type(self):
        wire = CacheMapper.encode({"progress": "not-a-float", "stage": "x"})
        with pytest.raises(ValueError):
            CacheMapper.decode(wire, dto_cls=_ProgressEntry)

    def test_typed_decode_wraps_malformed_json(self):
        # 非 JSON wire + dto_cls → ValueError (β 路径不抛裸 JSONDecodeError)
        with pytest.raises(ValueError):
            CacheMapper.decode("not-json{", dto_cls=_ProgressEntry)


# ----------------------------------------------------------------------
# wire 兼容: ensure_ascii 翻转 round-trip 安全
# ----------------------------------------------------------------------


class TestWireCompatEnsureAsciiFlip:
    """redis_crud 旧键 (ensure_ascii=True) 与新键 (ensure_ascii=False) 互读安全。"""

    def test_old_ascii_escaped_key_reads_via_new_decode(self):
        # 模拟旧 redis_crud 写入 (ensure_ascii=True): 中文转 \uXXXX
        old_wire = json.dumps({"name": "回测"}, ensure_ascii=True)
        assert "\\u" in old_wire  # 确是 ASCII 转义形态
        # 新 CacheMapper.decode (json.loads) 还原 — 双向兼容
        assert CacheMapper.decode(old_wire) == {"name": "回测"}

    def test_new_utf8_key_reads_via_plain_json_loads(self):
        # 新写键 (ensure_ascii=False, UTF-8 直存) 被标准 json.loads 还原
        new_wire = CacheMapper.encode({"name": "回测"})
        assert json.loads(new_wire) == {"name": "回测"}


# ----------------------------------------------------------------------
# 导出契约 (__init__ 暴露 CacheMapper / CacheEntry)
# ----------------------------------------------------------------------


class TestMapperFamilyExport:
    def test_cache_mapper_exported(self):
        assert ExportedCacheMapper is CacheMapper

    def test_cache_entry_exported(self):
        assert ExportedCacheEntry is CacheEntry

    def test_cache_entry_is_pydantic_marker_base(self):
        # CacheEntry 是可实例化的 marker 基类 (不强加 wire 信封)
        entry = CacheEntry()
        assert isinstance(entry, CacheEntry)


# ----------------------------------------------------------------------
# adoption 契约: redis_crud 走 CacheMapper 后 encode↔decode 自洽
# ----------------------------------------------------------------------


class TestRedisCrudAdoptionContract:
    """redis_crud.set/get 经 CacheMapper 的 encode↔decode 自洽 (无需真连 Redis)。"""

    def test_set_get_round_trip_dict(self):
        value = {"portfolio": "p1", "signals": ["BUY", "SELL"]}
        # set 路径: dict → CacheMapper.encode (替旧 json.dumps)
        wire = CacheMapper.encode(value)
        # get 路径: CacheMapper.decode (替旧 json.loads)
        assert CacheMapper.decode(wire) == value

    def test_set_get_round_trip_cjk(self):
        value = {"strategy": "动量", "count": 3}
        assert CacheMapper.decode(CacheMapper.encode(value)) == value
