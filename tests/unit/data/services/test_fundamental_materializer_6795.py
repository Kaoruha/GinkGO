"""
FundamentalFactorMaterializer 物化器单元测试 (#6795 L2)

把 tushare fina_indicator 财报 DataFrame 物化为因子存储行
(entity_type=STOCK, factor_category=fundamental, timestamp=报告期)。
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock

from ginkgo.enums import ENTITY_TYPES


@pytest.mark.unit
class TestFundamentalMaterializer:
    """基本面财报 → 因子物化 (#6795 L2)"""

    def _make_source(self, df):
        source = MagicMock()
        source.fetch_cn_fundancial_indicator.return_value = df
        return source

    def test_materialize_maps_fina_indicator_to_factor_dicts(self):
        """fina_indicator DataFrame → MFactor dict 列表(category=fundamental, ts=报告期 end_date)"""
        from ginkgo.data.services.fundamental_materializer import FundamentalFactorMaterializer

        df = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "ann_date": "20240430",
                    "end_date": "20240331",
                    "eps": 1.23,
                    "bps": 15.6,
                    "roe": 8.5,
                    "dt_roe": 8.1,
                    "profit_to_gr": 26.3,
                    "debt_to_assets": 70.2,
                }
            ]
        )
        source = self._make_source(df)
        factor_service = MagicMock()

        mat = FundamentalFactorMaterializer(source, factor_service)
        mat.materialize(code="000001.SZ", period="20240331")

        factor_service.add_factor_batch.assert_called_once()
        factors = factor_service.add_factor_batch.call_args[0][0]

        names = {f["factor_name"] for f in factors}
        assert {"EPS", "BPS", "ROE", "DILUTED_ROE", "NET_MARGIN", "DEBT_TO_ASSETS"} == names
        # 全归 fundamental 类目
        assert all(f["factor_category"] == "fundamental" for f in factors)
        # entity = STOCK + ts_code
        assert all(f["entity_id"] == "000001.SZ" for f in factors)
        assert all(f["entity_type"] == ENTITY_TYPES.STOCK for f in factors)
        # timestamp = 报告期 end_date(非 ann_date)
        assert all(f["timestamp"] == "20240331" for f in factors)
        # 值正确
        eps_row = next(f for f in factors if f["factor_name"] == "EPS")
        assert float(eps_row["factor_value"]) == 1.23

    def test_materialize_empty_df_returns_success_no_write(self):
        """空 DataFrame → 成功空结果,不调 add_factor_batch"""
        from ginkgo.data.services.fundamental_materializer import FundamentalFactorMaterializer

        source = self._make_source(pd.DataFrame())
        factor_service = MagicMock()

        mat = FundamentalFactorMaterializer(source, factor_service)
        r = mat.materialize(code="000001.SZ", period="20240331")

        assert r.success is True
        assert r.data["records_added"] == 0
        factor_service.add_factor_batch.assert_not_called()

    def test_materialize_multi_rows_multi_codes(self):
        """多行(多 ts_code)→ 每行各字段都映射,因子数 = 行数 × 字段数"""
        from ginkgo.data.services.fundamental_materializer import FundamentalFactorMaterializer

        df = pd.DataFrame(
            [
                {"ts_code": "000001.SZ", "end_date": "20240331", "eps": 1.23, "bps": 15.6, "roe": 8.5, "dt_roe": 8.1, "profit_to_gr": 26.3, "debt_to_assets": 70.2},
                {"ts_code": "600000.SH", "end_date": "20240331", "eps": 0.95, "bps": 12.0, "roe": 7.2, "dt_roe": 7.0, "profit_to_gr": 22.1, "debt_to_assets": 65.4},
            ]
        )
        source = self._make_source(df)
        factor_service = MagicMock()

        mat = FundamentalFactorMaterializer(source, factor_service)
        mat.materialize(code="000001.SZ", period="20240331")

        factors = factor_service.add_factor_batch.call_args[0][0]
        assert len(factors) == 12  # 2 行 × 6 字段
        assert {f["entity_id"] for f in factors} == {"000001.SZ", "600000.SH"}

    def test_materialize_skips_nan_fields(self):
        """财报字段为 NaN → 跳过该字段不产出因子行"""
        from ginkgo.data.services.fundamental_materializer import FundamentalFactorMaterializer

        df = pd.DataFrame(
            [{"ts_code": "000001.SZ", "end_date": "20240331", "eps": 1.23, "bps": float("nan"), "roe": 8.5}]
        )
        source = self._make_source(df)
        factor_service = MagicMock()

        mat = FundamentalFactorMaterializer(source, factor_service)
        mat.materialize(code="000001.SZ", period="20240331")

        factors = factor_service.add_factor_batch.call_args[0][0]
        names = {f["factor_name"] for f in factors}
        assert "EPS" in names and "ROE" in names
        assert "BPS" not in names  # NaN 跳过
