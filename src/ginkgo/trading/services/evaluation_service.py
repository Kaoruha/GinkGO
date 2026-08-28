# Upstream: API Server (api/evaluation), CLI (client/evaluation_cli), trading_container
# Downstream: FunnelEvaluator, ParityCalculator, PreflightChecker, AnalysisEngine (领域层)
# Role: 评估编排服务 — 四级漏斗/一致性/数据预检三路报告的统一入口 (跨源聚合)

"""
EvaluationService — 评估工作台后端编排

分层定位: API/CLI → 本服务 → 领域层 (trading/analysis/evaluation/*) → CRUD/DB。
不暴露 CRUD 实例; 报告实时计算不落库 (设计文档 §2.5)。

三路报告与 CLI (`ginkgo eval ...`) 同源: 同一领域层 evaluator/calculator/checker,
阈值来自 gate_definitions 单一事实源 — 三端 (CLI/API/前端) 口径一致。
"""

from typing import Optional

from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import BaseService, ServiceResult


class EvaluationService(BaseService):
    """评估编排服务 (funnel/parity/preflight 聚合)"""

    def __init__(
        self,
        result_service=None,
        analyzer_service=None,
        bar_crud=None,
        factor_loader=None,
        selector_resolver=None,
    ):
        # 领域层依赖经构造注入; None 时延迟到首次使用再取 (容器懒装配)
        self._result_service = result_service
        self._analyzer_service = analyzer_service
        self._bar_crud = bar_crud
        self._custom_factor_loader = factor_loader
        # selector_resolver(portfolio_id) -> List[str]; None 时用 task_helpers 默认解析
        self._selector_resolver = selector_resolver

    # ---------- 内部装配 ----------

    def _analysis_engine(self):
        from ginkgo.trading.analysis.engine import AnalysisEngine

        if self._result_service is None or self._analyzer_service is None:
            from ginkgo.data.containers import container

            self._result_service = container.result_service()
            self._analyzer_service = container.analyzer_service()
        return AnalysisEngine(self._result_service, self._analyzer_service)

    def _resolve_codes(self, portfolio_id: str):
        if self._selector_resolver is not None:
            return self._selector_resolver(portfolio_id) or []
        from ginkgo.workers.backtest_worker.task_helpers import resolve_selector_codes

        return resolve_selector_codes(portfolio_id) or []

    def _factor_loader(self):
        """复权因子取数 (与 CLI eval preflight 同口径; adjustfactor_service 分页两种形状兼容)"""
        from ginkgo.data.containers import container

        af_service = container.adjustfactor_service()

        def loader(code, s, e):
            res = af_service.get(code=code, start_date=s, end_date=e)
            items = res.data if getattr(res, "success", False) else []
            if isinstance(items, dict):
                items = items.get("data", [])
            out = []
            for r in items or []:
                ts = getattr(r, "timestamp", None)
                fac = getattr(r, "fore_adjustfactor", None)
                if ts is None or fac is None:
                    continue
                out.append((ts.date() if hasattr(ts, "date") else ts, float(fac)))
            return out

        return loader

    def _probe_selector(self, portfolio_id: str):
        """装配 portfolio 绑定的首个 selector 实例 (动态 selector probe 用)。

        与回测装配同路径: load_portfolio_components → ComponentLoader.
        instantiate_component (DB 源码 exec_module + ADR-020 纯位置参数),
        不另建工厂防双份漂移。装配失败返回 None — checker 走「未注入」放行分支。
        """
        from ginkgo.workers.backtest_worker.task_helpers import load_portfolio_components
        from ginkgo.trading.services._assembly.component_loader import ComponentLoader
        from ginkgo.data.containers import container

        components = load_portfolio_components(portfolio_id)
        selectors = components.get("selectors") or []
        if not selectors:
            GLOG.WARNING(f"[evaluation] portfolio {portfolio_id[:8]} 未绑定 selector，跳过 probe")
            return None
        loader = ComponentLoader(
            file_service=container.file_service(),
            param_service=container.param_service(),
        )
        s = selectors[0]
        comp, err = loader.instantiate_component(s["file_id"], s["type"], s["mapping_uuid"])
        if comp is None:
            GLOG.WARNING(f"[evaluation] probe selector 装配失败: {err}")
        return comp

    def _daily_counts_loader(self):
        """底座画像取数 (bar_service.get_daily_code_counts 的 ServiceResult 解包)

        container 访问延迟到 loader 实调 — 单测 stub checker 时不碰容器。
        """

        def loader(s, e):
            from ginkgo.data.containers import container

            res = container.bar_service().get_daily_code_counts(s, e)
            if not getattr(res, "success", False):
                raise RuntimeError(res.error)
            return res.data or {}

        return loader

    # ---------- 对外能力 ----------

    def get_gate_definitions(self) -> ServiceResult:
        """gate 定义清单 (前端渲染阈值线用; 与求值同源防口径漂移)"""
        from ginkgo.trading.analysis.evaluation.gate_definitions import ALL_GATES

        data = [
            {
                "id": g.id,
                "level": g.level,
                "name": g.name,
                "threshold": g.threshold,
                "direction": g.direction,
                "unit": g.unit,
                "severity": g.severity,
                "remediation": g.remediation,
                "requires": g.requires,
            }
            for g in ALL_GATES
        ]
        return ServiceResult(success=True, data=data)

    def get_funnel_report(
        self,
        portfolio_id: str,
        task_id: Optional[str] = None,
        candidate_task_id: Optional[str] = None,
        stability_window: int = 252,
    ) -> ServiceResult:
        """四级漏斗报告 (G0→G3 逐 gate; 实时计算不落库)

        Args:
            portfolio_id: 组合 id
            task_id: 回测 task id (缺省取 portfolio 最近完成任务)
            candidate_task_id: 对比序列 id (模拟盘 deployment 关联 task)
            stability_window: 滚动平稳度窗口
        """
        from ginkgo.trading.analysis.evaluation.funnel_evaluator import FunnelEvaluator

        try:
            fe = FunnelEvaluator(self._analysis_engine())
            r = fe.evaluate(
                portfolio_id=portfolio_id,
                task_id=task_id,
                candidate_task_id=candidate_task_id,
                stability_window=stability_window,
            )
            return ServiceResult(success=True, data=r.to_dict())
        except Exception as e:
            GLOG.ERROR(f"[evaluation] funnel failed: {e}")
            return ServiceResult(success=False, error=f"漏斗评估失败: {e}")

    def get_parity_report(
        self,
        portfolio_id: str,
        baseline_task_id: str,
        candidate_task_id: str,
    ) -> ServiceResult:
        """回测 vs 模拟盘同窗一致性 5 项 (G2; 净值主链 + 换手)"""
        from ginkgo.trading.analysis.evaluation.parity_calculator import ParityCalculator

        try:
            engine = self._analysis_engine()
            base_dp = engine._load_data(baseline_task_id, portfolio_id)
            cand_dp = engine._load_data(candidate_task_id, portfolio_id)
            base_nav, cand_nav = base_dp.get("net_value"), cand_dp.get("net_value")
            if base_nav is None or cand_nav is None:
                return ServiceResult(
                    success=False,
                    error="net_value 序列缺失，无法对比 (先确认两端分析器已产出记录)",
                )
            r = ParityCalculator().compare(
                baseline=base_nav,
                candidate=cand_nav,
                baseline_label=f"backtest:{baseline_task_id[:8]}",
                candidate_label=f"candidate:{candidate_task_id[:8]}",
                baseline_turnover=base_dp.get("order_count"),
                candidate_turnover=cand_dp.get("order_count"),
            )
            return ServiceResult(success=True, data=r.to_dict())
        except Exception as e:
            GLOG.ERROR(f"[evaluation] parity failed: {e}")
            return ServiceResult(success=False, error=f"一致性计算失败: {e}")

    def run_preflight(
        self,
        portfolio_id: str,
        start: str,
        end: str,
        min_bars: int = 10,
    ) -> ServiceResult:
        """数据质量预检 (G0 质量项)

        codes 来自 selector 解析; 动态 selector (codes 空) 时装配实例 probe 采样
        + 数据底座密度兜底 (见 PreflightChecker docstring)。
        """
        from ginkgo.trading.analysis.evaluation.preflight_checker import PreflightChecker

        try:
            codes = self._resolve_codes(portfolio_id)
            if self._bar_crud is None:
                from ginkgo.data.containers import container

                self._bar_crud = container.cruds.bar()
            # 动态 selector: probe 装配 (显式 codes 的 Fixed 场景无需实例化)
            selector = self._probe_selector(portfolio_id) if not codes else None
            checker = PreflightChecker(
                bar_crud=self._bar_crud,
                factor_loader=self._custom_factor_loader or self._factor_loader(),
                selector=selector,
                daily_counts_loader=self._daily_counts_loader(),
            )
            r = checker.check(
                portfolio_id=portfolio_id, codes=codes, start=start, end=end, min_bars=min_bars
            )
            return ServiceResult(success=True, data=r.to_dict())
        except Exception as e:
            GLOG.ERROR(f"[evaluation] preflight failed: {e}")
            return ServiceResult(success=False, error=f"数据预检失败: {e}")
