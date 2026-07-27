"""
assemble_factor_dataframe 单元测试 (#6795 L3)

把因子存储行(MFactor dict)组装成表达式引擎可消费的宽表 DataFrame:
列 = 因子名小写(对齐 FieldNode 的 .lstrip('$').lower() 标准化),
行 = 交易日轴,值按报告期 forward-fill(交易日 ≥ 报告期起生效)。
这是"基本面因子定义库可计算产出非零值"的数据胶水层(#6795 acceptance 第3条)。
"""

import numpy as np
import pandas as pd
import pytest


@pytest.mark.unit
class TestAssembleFactorDataframe:
    """因子存储行 → 表达式引擎宽表 (#6795 L3)"""

    def test_assemble_builds_wide_table_lowercase_columns_forward_filled(self):
        """EPS/ROE 因子行 + 交易日轴 → 宽表(列小写,报告期后 forward-fill,报告期前 NaN)"""
        from ginkgo.data.services.factor_assembly import assemble_factor_dataframe

        records = [
            {"factor_name": "EPS", "factor_value": 1.23, "timestamp": "20240331"},
            {"factor_name": "ROE", "factor_value": 8.5, "timestamp": "20240331"},
        ]
        # 20240329 在报告期前(无数据),20240401/02 在报告期后(应 forward-fill)
        date_index = ["20240329", "20240401", "20240402"]

        wide = assemble_factor_dataframe(records, date_index)

        # 列名小写(对齐 FieldNode 标准化: $EPS / $eps → 'eps')
        assert "eps" in wide.columns
        assert "roe" in wide.columns
        # 报告期前(20240329)无数据 → NaN
        assert pd.isna(wide.loc["20240329", "eps"])
        # 报告期后(20240401/02)forward-fill 生效
        assert wide.loc["20240401", "eps"] == pytest.approx(1.23)
        assert wide.loc["20240402", "roe"] == pytest.approx(8.5)

    def test_assemble_feeds_expression_engine_nonzero_pe(self):
        """assemble 的 eps 列 + bar close → ExpressionEngine 算 $close/$eps 产出非零(PE)

        #6795 acceptance 第3条验收:物化的基本面因子经 assemble 后,含基本面变量的
        表达式可计算产出非零值(此处 PE = 价格 / 每股收益)。
        """
        from ginkgo.data.services.factor_assembly import assemble_factor_dataframe
        from ginkgo.features.engines.expression_engine import ExpressionEngine

        dates = ["20240401", "20240402"]
        bar = pd.DataFrame({"close": [12.3, 12.5]}, index=dates)
        records = [{"factor_name": "EPS", "factor_value": 1.23, "timestamp": "20240331"}]

        wide = assemble_factor_dataframe(records, dates)
        data = bar.copy()
        data["eps"] = wide["eps"].values

        engine = ExpressionEngine()
        pe = engine.execute_expression("$close / $eps", data)

        assert isinstance(pe, pd.Series)
        assert not pe.isna().all()          # 非全 NaN(基本面变量取到了值)
        assert (pe > 0).all()               # 全非零正
        assert pe.iloc[0] == pytest.approx(10.0)  # 12.3 / 1.23 = 10.0
