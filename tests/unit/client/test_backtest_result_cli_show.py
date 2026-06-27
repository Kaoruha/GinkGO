"""#6136: backtest_result_cli show() 选 portfolio 分支走 mapping_service._df 出口。

验证 ``--engine`` 给定、``--portfolio`` 缺省时调用
``mapping_service.get_engine_portfolio_mappings_df``（修复前的死调用
``engine_service.get_engine_portfolio_mappings`` 不再触发）。

注：show() 旧方式分支顶部 ``from ginkgo.data.operations import ...`` 指向的模块
当前 master 全仓缺失（预存、独立于 #6136），此处注入 sys.modules 桩隔离之，
聚焦验证 #6136 的 mapping _df 出口契约，端到端可达性留待 operations 补齐。
"""

import os
import sys

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pandas as pd
from unittest.mock import MagicMock, patch

# 隔离预存的 operations 缺失（非 #6136 范围）：注入桩使 show() 顶部 import 不崩，
# 聚焦验证 L114 死调用已改走 mapping_service._df 出口。
sys.modules.setdefault("ginkgo.data.operations", MagicMock())

from ginkgo.client import backtest_result_cli


def _make_service_result(df: pd.DataFrame, success: bool = True) -> MagicMock:
    """模拟 ServiceResult：.success + .data(DataFrame)，对齐 _df 出口契约。"""
    result = MagicMock()
    result.success = success
    result.data = df
    return result


def test_show_portfolio_branch_uses_mapping_service_df():
    """#6136：engine 给定 + portfolio 缺省 → 走 mapping_service._df，不崩且展示。"""
    mock_mapping = MagicMock()
    mock_mapping.get_engine_portfolio_mappings_df.return_value = _make_service_result(
        pd.DataFrame([{"engine_id": "eng-1", "portfolio_id": "pf-1", "portfolio_name": "P1"}])
    )
    with patch("ginkgo.data.containers.container") as mock_container, \
         patch("ginkgo.libs.utils.display.display_dataframe") as mock_display, \
         patch.object(backtest_result_cli.console, "print"):
        mock_container.mapping_service.return_value = mock_mapping
        # portfolio 默认 None → 进入"选 portfolio"分支（call site 3）
        backtest_result_cli.show(engine="eng-1")

    mock_mapping.get_engine_portfolio_mappings_df.assert_called_once_with(engine_uuid="eng-1")
    # 非空映射 → 调 display_dataframe 展示
    assert mock_display.called


def test_show_portfolio_branch_empty_mappings_does_not_crash():
    """#6136：空映射 → 打印提示，不崩（_df 出口 data 即空 DataFrame）。"""
    mock_mapping = MagicMock()
    mock_mapping.get_engine_portfolio_mappings_df.return_value = _make_service_result(
        pd.DataFrame(columns=["engine_id", "portfolio_id"])
    )
    with patch("ginkgo.data.containers.container") as mock_container, \
         patch("ginkgo.libs.utils.display.display_dataframe") as mock_display, \
         patch.object(backtest_result_cli.console, "print"):
        mock_container.mapping_service.return_value = mock_mapping
        backtest_result_cli.show(engine="eng-1")

    mock_mapping.get_engine_portfolio_mappings_df.assert_called_once_with(engine_uuid="eng-1")
    # 空映射 → 不调 display_dataframe（走 "No portfolios found" 提示分支）
    assert not mock_display.called
