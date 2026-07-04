"""
#5112 — create_engine_portfolio_mapping 必须校验 engine.is_live 与 portfolio.mode 兼容。

表象：ginkgo engine bind-portfolio <live_engine> <backtest_portfolio> 静默成功，运行时才报错。
根因：MappingService.create_engine_portfolio_mapping 直接落库 MEnginePortfolioMapping，
      不校验 engine.is_live vs portfolio.mode 是否兼容。
契约（引擎只分 BACKTEST/LIVE，见 arch-engine-unification）：
  - BACKTEST engine (is_live=False) + BACKTEST portfolio (mode=0)         → 兼容，创建成功
  - LIVE   engine (is_live=True)  + PAPER/LIVE portfolio (mode>=1)        → 兼容，创建成功
  - BACKTEST engine + PAPER/LIVE portfolio                                → 拒绝，不落库
  - LIVE   engine + BACKTEST portfolio                                    → 拒绝，不落库
"""
from unittest.mock import MagicMock, patch

from ginkgo.data.services.mapping_service import MappingService


def _make_svc():
    mock_ep_mapping = MagicMock()
    mock_pf_mapping = MagicMock()
    mock_eh_mapping = MagicMock()
    mock_param = MagicMock()
    svc = MappingService(
        engine_portfolio_mapping_crud=mock_ep_mapping,
        portfolio_file_mapping_crud=mock_pf_mapping,
        engine_handler_mapping_crud=mock_eh_mapping,
        param_crud=mock_param,
    )
    return svc, mock_ep_mapping


def _engine(is_live: bool):
    e = MagicMock()
    e.is_live = is_live
    return e


def _portfolio(mode: int):
    p = MagicMock()
    p.mode = mode
    return p


class TestCreateEnginePortfolioMappingModeValidation:
    """bind-portfolio 必须校验 engine.is_live 与 portfolio.mode 兼容。"""

    @patch("ginkgo.data.crud.engine_crud.EngineCRUD")
    @patch("ginkgo.data.crud.portfolio_crud.PortfolioCRUD")
    def test_backtest_engine_live_portfolio_rejected(self, mock_pf_crud_cls, mock_eng_crud_cls):
        """BACKTEST engine + LIVE portfolio → 拒绝，不创建 mapping（tracer bullet）"""
        svc, mock_ep_mapping = _make_svc()
        mock_eng_crud_cls.return_value.find_by_uuid.return_value = [_engine(is_live=False)]
        mock_pf_crud_cls.return_value.find_by_uuid.return_value = [_portfolio(mode=2)]  # LIVE

        result = svc.create_engine_portfolio_mapping(
            engine_uuid="eng-1",
            portfolio_uuid="port-1",
            engine_name="E",
            portfolio_name="P",
        )

        assert not result.success, "BACKTEST engine + LIVE portfolio 应被拒绝"
        mock_ep_mapping.add_batch.assert_not_called()

    @patch("ginkgo.data.crud.engine_crud.EngineCRUD")
    @patch("ginkgo.data.crud.portfolio_crud.PortfolioCRUD")
    def test_live_engine_backtest_portfolio_rejected(self, mock_pf_crud_cls, mock_eng_crud_cls):
        """LIVE engine + BACKTEST portfolio → 拒绝，不创建 mapping"""
        svc, mock_ep_mapping = _make_svc()
        mock_eng_crud_cls.return_value.find_by_uuid.return_value = [_engine(is_live=True)]
        mock_pf_crud_cls.return_value.find_by_uuid.return_value = [_portfolio(mode=0)]  # BACKTEST

        result = svc.create_engine_portfolio_mapping(
            engine_uuid="eng-1", portfolio_uuid="port-1",
            engine_name="E", portfolio_name="P",
        )

        assert not result.success, "LIVE engine + BACKTEST portfolio 应被拒绝"
        mock_ep_mapping.add_batch.assert_not_called()

    @patch("ginkgo.data.crud.engine_crud.EngineCRUD")
    @patch("ginkgo.data.crud.portfolio_crud.PortfolioCRUD")
    def test_backtest_engine_backtest_portfolio_accepted(self, mock_pf_crud_cls, mock_eng_crud_cls):
        """BACKTEST engine + BACKTEST portfolio → 兼容，创建 mapping"""
        svc, mock_ep_mapping = _make_svc()
        mock_eng_crud_cls.return_value.find_by_uuid.return_value = [_engine(is_live=False)]
        mock_pf_crud_cls.return_value.find_by_uuid.return_value = [_portfolio(mode=0)]  # BACKTEST
        mock_ep_mapping.find.return_value = []  # 无重复
        created = MagicMock()
        mock_ep_mapping.add_batch.return_value = [created]

        result = svc.create_engine_portfolio_mapping(
            engine_uuid="eng-1", portfolio_uuid="port-1",
            engine_name="E", portfolio_name="P",
        )

        assert result.success, "BACKTEST engine + BACKTEST portfolio 应创建成功"
        mock_ep_mapping.add_batch.assert_called_once()

    @patch("ginkgo.data.crud.engine_crud.EngineCRUD")
    @patch("ginkgo.data.crud.portfolio_crud.PortfolioCRUD")
    def test_live_engine_paper_portfolio_accepted(self, mock_pf_crud_cls, mock_eng_crud_cls):
        """LIVE engine + PAPER portfolio → 兼容，创建 mapping"""
        svc, mock_ep_mapping = _make_svc()
        mock_eng_crud_cls.return_value.find_by_uuid.return_value = [_engine(is_live=True)]
        mock_pf_crud_cls.return_value.find_by_uuid.return_value = [_portfolio(mode=1)]  # PAPER
        mock_ep_mapping.find.return_value = []
        created = MagicMock()
        mock_ep_mapping.add_batch.return_value = [created]

        result = svc.create_engine_portfolio_mapping(
            engine_uuid="eng-1", portfolio_uuid="port-1",
            engine_name="E", portfolio_name="P",
        )

        assert result.success, "LIVE engine + PAPER portfolio 应创建成功"
        mock_ep_mapping.add_batch.assert_called_once()

    @patch("ginkgo.data.crud.engine_crud.EngineCRUD")
    @patch("ginkgo.data.crud.portfolio_crud.PortfolioCRUD")
    def test_engine_not_found_skips_guard(self, mock_pf_crud_cls, mock_eng_crud_cls):
        """engine 查不到 → 跳过守卫（保持原存在性行为，不阻断其他调用方）"""
        svc, mock_ep_mapping = _make_svc()
        mock_eng_crud_cls.return_value.find_by_uuid.return_value = []  # engine 不存在
        mock_pf_crud_cls.return_value.find_by_uuid.return_value = [_portfolio(mode=0)]
        mock_ep_mapping.find.return_value = []
        created = MagicMock()
        mock_ep_mapping.add_batch.return_value = [created]

        result = svc.create_engine_portfolio_mapping(
            engine_uuid="eng-1", portfolio_uuid="port-1",
            engine_name="E", portfolio_name="P",
        )

        assert result.success, "engine 查不到时应跳过守卫保持原行为"
