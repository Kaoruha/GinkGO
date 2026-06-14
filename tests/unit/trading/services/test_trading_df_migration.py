"""
#6107 ADR-010 数据对象三层角色分离 - trading 层 5 站点迁移守卫

迁移目标：消费者从 svc.get() + hasattr(data,'to_dataframe') 双分支，
改成 svc.get_*_df() 单出口（data 已是 DataFrame）。

本测试确保：
1. 消费者不再调 .to_dataframe()（鸭子探测已删除）
2. 空 DataFrame 走 .empty 判空，进正确分支（return error / raise ValueError / 返 []）
3. 非空 DataFrame 取 iloc[0].to_dict() / 列.tolist() 行为保持
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.base_service import ServiceResult


@pytest.mark.unit
class TestEngineAssemblyGetEngineByIdMigration:
    """EngineAssemblyService.get_engine_by_id 迁 get_engines_df 出口"""

    def _make_service(self):
        from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
        svc = EngineAssemblyService.__new__(EngineAssemblyService)
        svc._engine_service = MagicMock()
        return svc

    def test_nonempty_df_returns_dict(self):
        svc = self._make_service()
        df = pd.DataFrame([{"engine_id": "e1", "name": "eng"}])
        svc._engine_service.get_engines_df.return_value = ServiceResult.success(data=df)

        result = svc.get_engine_by_id("e1")

        assert result.success is True
        assert result.data["engine_id"] == "e1"
        # 不再走 get()，也不再调 to_dataframe
        svc._engine_service.get_engines_df.assert_called_once_with(engine_id="e1")
        svc._engine_service.get.assert_not_called()

    def test_empty_df_returns_error(self):
        """空 DataFrame 必须用 .empty 判空返 error，bool() 会抛 ValueError"""
        svc = self._make_service()
        svc._engine_service.get_engines_df.return_value = ServiceResult.success(data=pd.DataFrame())

        result = svc.get_engine_by_id("missing")

        assert result.success is False
        assert "No engine found" in result.error

    def test_failed_result_returns_error(self):
        svc = self._make_service()
        svc._engine_service.get_engines_df.return_value = ServiceResult.error(error="boom")

        result = svc.get_engine_by_id("e1")

        assert result.success is False


@pytest.mark.unit
class TestDataPreparerFetchEngineConfigMigration:
    """DataPreparer._fetch_engine_config 迁 get_engines_df，空 DF raise ValueError"""

    def _make_preparer(self):
        from ginkgo.trading.services._assembly.data_preparer import DataPreparer
        p = DataPreparer()
        p._engine_service = MagicMock()
        return p

    def test_nonempty_df_returns_dict(self):
        p = self._make_preparer()
        df = pd.DataFrame([{"engine_id": "e1", "name": "eng"}])
        p._engine_service.get_engines_df.return_value = ServiceResult.success(data=df)

        cfg = p._fetch_engine_config("e1")

        assert cfg["engine_id"] == "e1"
        p._engine_service.get_engines_df.assert_called_once_with(engine_id="e1")
        p._engine_service.get.assert_not_called()

    def test_empty_df_raises(self):
        p = self._make_preparer()
        p._engine_service.get_engines_df.return_value = ServiceResult.success(data=pd.DataFrame())

        with pytest.raises(ValueError, match="No engine found"):
            p._fetch_engine_config("missing")


@pytest.mark.unit
class TestDataPreparerGetPortfolioConfigMigration:
    """DataPreparer._get_portfolio_config_refactored 迁 get_portfolios_df，空 DF raise"""

    def _make_preparer(self):
        from ginkgo.trading.services._assembly.data_preparer import DataPreparer
        p = DataPreparer()
        p._portfolio_service = MagicMock()
        return p

    def test_nonempty_df_returns_dict(self):
        p = self._make_preparer()
        df = pd.DataFrame([{"portfolio_id": "pf1", "name": "p"}])
        p._portfolio_service.get_portfolios_df.return_value = ServiceResult.success(data=df)

        cfg = p._get_portfolio_config_refactored("pf1")

        assert cfg["portfolio_id"] == "pf1"
        p._portfolio_service.get_portfolios_df.assert_called_once_with(portfolio_id="pf1")
        p._portfolio_service.get.assert_not_called()

    def test_empty_df_raises(self):
        p = self._make_preparer()
        p._portfolio_service.get_portfolios_df.return_value = ServiceResult.success(data=pd.DataFrame())

        with pytest.raises(ValueError, match="No portfolio found"):
            p._get_portfolio_config_refactored("missing")


@pytest.mark.unit
class TestDataPreparerPortfolioLoopMigration:
    """prepare_engine_data 循环内 portfolio 迁 get_portfolios_df，空 DF 走 continue"""

    def test_empty_df_in_loop_skipped_not_raised(self):
        """站点2：循环内 portfolio 空 DF 应 WARN+continue，不抛 ValueError、不阻断"""
        from ginkgo.trading.services._assembly.data_preparer import DataPreparer
        from types import SimpleNamespace

        p = DataPreparer()
        p._engine_service = MagicMock()
        p._portfolio_service = MagicMock()

        # 前置：engine config 拿到；engine 下有 1 条 portfolio mapping
        p._fetch_engine_config = MagicMock(return_value={"engine_id": "e1"})
        p._engine_service.get_portfolios.return_value = ServiceResult.success(
            data={"mappings": [SimpleNamespace(portfolio_id="pf1")]}
        )
        # 循环内：portfolio 返空 DF，应 continue（最终 configs 为空）
        p._portfolio_service.get_portfolios_df.return_value = ServiceResult.success(
            data=pd.DataFrame()
        )

        result = p.prepare_engine_data("e1")

        # 空 DF 被 continue，函数正常返回 success，但 portfolio_configs 为空 dict
        assert result.success is True
        assert result.data["portfolio_configs"] == {}
        # 循环内调 get_portfolios_df，不调 get
        p._portfolio_service.get_portfolios_df.assert_called_once_with(portfolio_id="pf1")
        p._portfolio_service.get.assert_not_called()


@pytest.mark.unit
class TestCnAllSelectorMigration:
    """CNAllSelector.pick 迁 get_stockinfos_df，空 DF 返 []"""

    @patch("ginkgo.data.containers.container")
    def test_nonempty_df_returns_codes(self, mock_container):
        df = pd.DataFrame([{"code": "000001.SZ"}, {"code": "000002.SZ"}])
        mock_stockinfo = MagicMock()
        mock_stockinfo.get_stockinfos_df.return_value = ServiceResult.success(data=df)
        mock_container.stockinfo_service.return_value = mock_stockinfo

        from ginkgo.trading.selectors.cn_all_selector import CNAllSelector

        sel = CNAllSelector()
        codes = sel.pick()

        assert codes == ["000001.SZ", "000002.SZ"]
        mock_stockinfo.get_stockinfos_df.assert_called_once_with()
        mock_stockinfo.get.assert_not_called()

    @patch("ginkgo.data.containers.container")
    def test_empty_df_returns_empty_list(self, mock_container):
        mock_stockinfo = MagicMock()
        mock_stockinfo.get_stockinfos_df.return_value = ServiceResult.success(data=pd.DataFrame())
        mock_container.stockinfo_service.return_value = mock_stockinfo

        from ginkgo.trading.selectors.cn_all_selector import CNAllSelector

        sel = CNAllSelector()
        codes = sel.pick()

        assert codes == []

    @patch("ginkgo.data.containers.container")
    def test_failed_result_returns_empty_list(self, mock_container):
        mock_stockinfo = MagicMock()
        mock_stockinfo.get_stockinfos_df.return_value = ServiceResult.error(error="db down")
        mock_container.stockinfo_service.return_value = mock_stockinfo

        from ginkgo.trading.selectors.cn_all_selector import CNAllSelector

        sel = CNAllSelector()
        codes = sel.pick()

        assert codes == []
