# Upstream: PaperTradingWorker, CLI deploy command
# Downstream: Engine (advance_time_to), BarService (sync_range_batch), TradeDayCRUD
# Role: 每日循环控制器 — 检查交易日、拉取数据、推进引擎


from dataclasses import dataclass
from datetime import datetime
from typing import List

from ginkgo.libs import GLOG, time_logger


@dataclass
class DailyCycleResult:
    """每日循环执行结果"""
    skipped: bool = False
    date: str = ""
    fetched_count: int = 0
    advanced: bool = False
    error: str = ""
    warning: str = ""


class PaperTradingController:
    """
    纸上交易控制器

    职责：每个交易日收盘后执行一次循环：
    1. 检查是否交易日
    2. 自行拉取 portfolio 关注股票的当日 K 线（同步调用，不依赖 bar_snapshot）
    3. 推进引擎到下一个交易日（通过 TradeDayCRUD.get_next_trading_day() 避免周末/节假日）

    数据就绪保证：通过 bar_service.sync_range_batch() 同步拉取，
    拉取完成后数据即在 ClickHouse 中，无需等待 bar_snapshot 的异步处理。

    边界处理：
    - 重复推进：LogicalTimeProvider.set_current_time() 拒绝时间倒退，相同时间幂等
    - sync 0 数据：交易日已提前检查，0 成功 = 拉取失败，skip + error log
    - 周末/节假日：用 TradeDayCRUD.get_next_trading_day() 而非 today + 1 day
    """

    def __init__(self, engine, bar_service=None, trade_day_crud=None):
        """
        Args:
            engine: TimeControlledEventEngine 实例
            bar_service: BarService 实例（可选，默认从 services 获取）
            trade_day_crud: TradeDayCRUD 实例（可选，默认从 services 获取）
        """
        self._engine = engine
        if bar_service is None:
            from ginkgo import services
            bar_service = services.data.bar_service()
        self._bar_service = bar_service
        if trade_day_crud is None:
            from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
            trade_day_crud = TradeDayCRUD()
        self._trade_day_crud = trade_day_crud

    def get_interested_codes(self) -> List[str]:
        """从引擎的 selector 获取关注股票列表"""
        codes = []
        for portfolio in self._engine.portfolios.values():
            selector = getattr(portfolio, "selector", None)
            if selector and hasattr(selector, "_interested"):
                codes.extend(selector._interested)
        return list(set(codes))

    @time_logger
    def run_daily_cycle(self) -> DailyCycleResult:
        """
        执行每日循环

        Returns:
            DailyCycleResult: 执行结果
        """
        today = datetime.now().date()

        # 1. 检查交易日
        if not self._is_trading_day(today):
            GLOG.INFO(f"[PAPER] {today} is not a trading day, skipping")
            return DailyCycleResult(skipped=True, date=str(today))

        # 2. 获取关注股票列表
        codes = self.get_interested_codes()
        if not codes:
            GLOG.WARN("[PAPER] No interested codes, skipping")
            return DailyCycleResult(
                skipped=True, date=str(today), error="No interested codes"
            )

        # 3. 同步拉取当日 K 线数据（同步调用，确保数据就绪）
        try:
            sync_result = self._bar_service.sync_range_batch(
                codes=codes,
                start_date=today,
                end_date=today,
            )
            batch_details = getattr(sync_result.data, 'batch_details', {}) if sync_result.success else {}
            fetched_count = batch_details.get("successful_codes", 0)
            failed_count = batch_details.get("failed_codes", 0)
            failures = batch_details.get("failures", [])
        except Exception as e:
            GLOG.ERROR(f"[PAPER] Failed to fetch data: {e}")
            return DailyCycleResult(
                skipped=True, date=str(today), error=f"Data fetch failed: {e}"
            )

        # 交易日但 sync 返回 0 成功 → 拉取失败，不推进
        if fetched_count == 0:
            GLOG.ERROR(f"[PAPER] Trading day {today} but no data fetched, skipping")
            return DailyCycleResult(
                skipped=True, date=str(today), error="No data fetched"
            )

        # 部分失败：告警但仍推进
        warning = ""
        if failed_count > 0 and failures:
            failed_code_list = [f["code"] for f in failures]
            warning = f"Partial sync failure: {failed_code_list}"
            GLOG.WARN(f"[PAPER] {warning}")

        # 4. 推进引擎到下一个交易日 15:00
        next_trading_day = self._trade_day_crud.get_next_trading_day(today)
        if next_trading_day is None:
            GLOG.ERROR(f"[PAPER] Cannot find next trading day after {today}")
            return DailyCycleResult(
                skipped=True, date=str(today), error="No next trading day found"
            )

        target_time = datetime.combine(
            next_trading_day.date() if hasattr(next_trading_day, 'date') else next_trading_day,
            datetime.min.time().replace(hour=15, minute=0),
        )

        try:
            success = self._engine.advance_time_to(target_time)
            GLOG.INFO(
                f"[PAPER] Daily cycle: {today} -> {target_time.date()}, "
                f"fetched={fetched_count}/{len(codes)}, advanced={success}"
            )
            return DailyCycleResult(
                skipped=False,
                date=str(today),
                fetched_count=fetched_count,
                advanced=success,
                warning=warning,
            )
        except Exception as e:
            GLOG.ERROR(f"[PAPER] Failed to advance engine: {e}")
            return DailyCycleResult(
                skipped=False,
                date=str(today),
                fetched_count=fetched_count,
                advanced=False,
                error=str(e),
            )

    def _is_trading_day(self, date) -> bool:
        """判断指定日期是否是 A 股交易日"""
        from ginkgo.enums import MARKET_TYPES

        try:
            results = self._trade_day_crud.find(
                filters={"timestamp": date, "market": MARKET_TYPES.CHINA}
            )
            if results and len(results) > 0:
                return bool(results[0].is_open)
        except Exception as e:
            GLOG.ERROR(f"Failed to check trading day: {e}")
        return False
