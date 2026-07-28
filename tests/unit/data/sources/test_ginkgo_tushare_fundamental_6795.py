"""
GinkgoTushare 基本面数据源适配器单元测试 (#6795)

测试范围:
1. fetch_cn_fundancial_indicator 调 pro.fina_indicator 并返回财报 DataFrame
   (后续垂直切片追加: 字段映射 / 空数据 / 异常)
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestGinkgoTushareFundamental:
    """GinkgoTushare 基本面财报获取 (#6795)"""

    @patch("ginkgo.data.sources.ginkgo_tushare.ts")
    @patch("ginkgo.data.sources.ginkgo_tushare.GCONF")
    def test_fetch_fundancial_indicator_calls_pro_and_returns_df(self, mock_conf, mock_ts):
        """fetch_cn_fundancial_indicator 应调 pro.fina_indicator(ts_code, period) 并原样返回 DataFrame"""
        from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare

        mock_pro = MagicMock()
        mock_ts.pro_api.return_value = mock_pro

        fake_df = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "ann_date": "20240430",
                    "end_date": "20240331",
                    "eps": 1.23,
                    "bps": 15.60,
                    "roe": 8.5,
                    "dt_roe": 8.1,
                    "profit_to_gr": 26.3,
                }
            ]
        )
        mock_pro.fina_indicator.return_value = fake_df

        source = GinkgoTushare()
        r = source.fetch_cn_fundancial_indicator(code="000001.SZ", period="20240331")

        # 1. 调用了 pro.fina_indicator
        mock_pro.fina_indicator.assert_called_once()
        _, kwargs = mock_pro.fina_indicator.call_args
        assert kwargs.get("ts_code") == "000001.SZ"
        assert kwargs.get("period") == "20240331"
        # 2. 返回的是 tushare 原始 DataFrame,内容不变
        assert not r.empty
        assert r.iloc[0]["eps"] == 1.23
        assert r.iloc[0]["roe"] == 8.5
