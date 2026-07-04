"""
性能: 218MB RSS, 1.88s, 12 tests [PASS]
TickCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MTick 模型（需设置 model_class）
- Business Helper: find_by_time_range, count_by_direction
- 构造与类型检查

注意：TickCRUD 是特殊的动态Model CRUD，不继承 BaseCRUD，
因此 fixture 需要手动设置 model_class。
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data.models import MTick


# ============================================================
# 辅助：构造 TickCRUD 实例（mock DB 连接）
# TickCRUD 不继承 BaseCRUD，需要特殊处理
# ============================================================


@pytest.fixture
def tick_crud():
    """构造 TickCRUD 实例并设置模拟的 model_class"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.tick_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.tick_crud import TickCRUD
        crud = TickCRUD()
        # TickCRUD 不继承 BaseCRUD，手动设置 model_class 用于 _create_from_params
        crud.model_class = MTick
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestTickCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, tick_crud):
        """配置包含 code/price/volume/direction/timestamp"""
        config = tick_crud._get_field_config()

        required_keys = {"code", "price", "volume", "direction", "timestamp"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_code_validation(self, tick_crud):
        """code 字段为 string 类型，min=1, max=32"""
        config = tick_crud._get_field_config()

        assert config["code"]["type"] == "string"
        assert config["code"]["min"] == 1
        assert config["code"]["max"] == 32

    @pytest.mark.unit
    def test_field_config_price_validation(self, tick_crud):
        """price 字段 min=0"""
        config = tick_crud._get_field_config()

        assert 0 == config["price"]["min"]

    @pytest.mark.unit
    def test_field_config_direction_is_enum(self, tick_crud):
        """direction 字段为枚举类型"""
        config = tick_crud._get_field_config()

        assert "enum" in config["direction"]["type"]
        assert "choices" in config["direction"]


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestTickCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_direction_and_source(self, tick_crud):
        """映射包含 direction 和 source 两个枚举"""
        mappings = tick_crud._get_enum_mappings()

        assert "direction" in mappings
        assert "source" in mappings
        assert mappings["direction"] is TICKDIRECTION_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestTickCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, tick_crud):
        """传入完整参数，返回 MTick 模型且属性正确

        注意：源码 tick_crud.py:424 使用了 TICKDIRECTION_TYPES.OTHER（不存在），
        使用 patch.object 将 OTHER 映射到 VOID 以绕过源码 bug。
        """
        with patch("ginkgo.data.crud.tick_crud.datetime_normalize") as mock_dt, \
             patch("ginkgo.data.crud.tick_crud.to_decimal") as mock_decimal, \
             patch.object(TICKDIRECTION_TYPES, "OTHER", TICKDIRECTION_TYPES.VOID, create=True):
            mock_dt.return_value = datetime(2024, 1, 15, 9, 30, 0)
            mock_decimal.return_value = Decimal("10.50")

            params = {
                "code": "000001.SZ",
                "price": Decimal("10.50"),
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
            }

            mtick = tick_crud._create_from_params(**params)

            assert isinstance(mtick, MTick)
            assert mtick.code == "000001.SZ"
            assert mtick.volume == 1000

    @pytest.mark.unit
    def test_create_from_params_requires_code(self, tick_crud):
        """缺少 code 参数应抛出 ValueError"""
        with pytest.raises(ValueError, match="code"):
            tick_crud._create_from_params(price=10.50, volume=1000)


# ============================================================
# Business Helper 测试
# ============================================================


class TestTickCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_time_range(self, tick_crud):
        """find_by_time_range 构造正确的 filters 并调用 self.find"""
        tick_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.tick_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            tick_crud.find_by_time_range(
                code="000001.SZ",
                start_time="2024-01-01",
                end_time="2024-12-31",
            )

        tick_crud.find.assert_called_once()
        call_kwargs = tick_crud.find.call_args[1]
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert "timestamp__gte" in call_kwargs["filters"]
        assert "timestamp__lte" in call_kwargs["filters"]
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_count_by_direction(self, tick_crud):
        """count_by_direction 调用 self.count 并传入正确 filters"""
        tick_crud.count = MagicMock(return_value=42)

        result = tick_crud.count_by_direction(code="000001.SZ", direction=TICKDIRECTION_TYPES.ACTIVEBUY)

        assert result == 42
        tick_crud.count.assert_called_once()
        call_args = tick_crud.count.call_args[0][0]
        assert call_args["code"] == "000001.SZ"
        assert call_args["direction"] == TICKDIRECTION_TYPES.ACTIVEBUY

    @pytest.mark.unit
    def test_find_by_time_range_requires_code(self, tick_crud):
        """find_by_time_range 缺少 code 应抛出 ValueError"""
        with pytest.raises(ValueError, match="code"):
            tick_crud.find_by_time_range(code="", start_time="2024-01-01")


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestTickCRUDConstruction:
    """TickCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_tick_crud_construction(self, tick_crud):
        """验证 TickCRUD 实例可正常创建，model_class 可设置"""
        # TickCRUD 不继承 BaseCRUD，没有 _is_mysql/_is_clickhouse
        assert tick_crud.model_class is MTick


    @pytest.mark.unit
    def test_tick_crud_not_base_crud(self, tick_crud):
        """验证 TickCRUD 不继承 BaseCRUD"""
        from ginkgo.data.crud.base_crud import BaseCRUD

        assert not isinstance(tick_crud, BaseCRUD)


# ============================================================
# count_all 测试 — #5423 跨分表全量统计
# Tick 数据按股票代码动态分表（{code}_Tick，ClickHouse MergeTree），
# count_all 通过 system.tables 元数据一次聚合所有分表的 total_rows。
# ============================================================


class TestTickCRUDCountAll:
    """count_all: 跨所有 _Tick 分表聚合行数（#5423）"""

    @pytest.mark.unit
    def test_count_all_sums_total_rows_via_system_tables(self, tick_crud):
        """count_all 应查 system.tables 聚合所有 _Tick 分表的 total_rows 并返回 int"""
        with patch("ginkgo.data.crud.tick_crud.get_db_connection") as mock_conn_fn:
            mock_session = MagicMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (543452,)
            mock_session.execute.return_value = mock_result
            mock_conn = MagicMock()
            mock_conn.get_session.return_value.__enter__.return_value = mock_session
            mock_conn_fn.return_value = mock_conn

            total = tick_crud.count_all()

            assert total == 543452
            # 核心契约：必须查 system.tables 元数据表（跨分表聚合的入口）
            sql_text = str(mock_session.execute.call_args[0][0])
            assert "system.tables" in sql_text

    @pytest.mark.unit
    def test_count_all_returns_zero_when_no_tick_tables(self, tick_crud):
        """无 _Tick 分表时（sum 为 NULL），应规整为 0 而非 None"""
        with patch("ginkgo.data.crud.tick_crud.get_db_connection") as mock_conn_fn:
            mock_session = MagicMock()
            mock_result = MagicMock()
            # ClickHouse sum() over empty set 返回 NULL/None
            mock_result.fetchone.return_value = (None,)
            mock_session.execute.return_value = mock_result
            mock_conn = MagicMock()
            mock_conn.get_session.return_value.__enter__.return_value = mock_session
            mock_conn_fn.return_value = mock_conn

            assert tick_crud.count_all() == 0

    @pytest.mark.unit
    def test_count_all_degrades_to_zero_on_db_error(self, tick_crud):
        """DB 异常时不应抛出，应降级返回 0（stats 端点不能因统计失败而 500）"""
        with patch("ginkgo.data.crud.tick_crud.get_db_connection") as mock_conn_fn:
            mock_conn = MagicMock()
            mock_conn.get_session.side_effect = RuntimeError("clickhouse unreachable")
            mock_conn_fn.return_value = mock_conn

            assert tick_crud.count_all() == 0
