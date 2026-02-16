# Upstream: ginkgo.data.cruds, ginkgo.trading.portfolio, ginkgo.trading.strategies
# Downstream: ginkgo.trading.comparison, ginkgo.client
# Role: Paper Trading 引擎 - 使用实盘数据验证策略表现

"""
Paper Trading Engine

使用实盘市场数据验证策略表现，与回测结果对比。

核心功能:
- 加载 Portfolio 和策略配置
- 按交易日执行策略计算
- 应用滑点模型模拟成交
- 与回测结果对比

Usage:
    from ginkgo.trading.paper.paper_engine import PaperTradingEngine

    engine = PaperTradingEngine(
        portfolio_id="portfolio_001",
        slippage_model="percentage",
        slippage_value=0.001
    )
    engine.start()
    engine.on_daily_close()  # 每日收盘后调用
    result = engine.compare_with_backtest("backtest_001")
    engine.stop()
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union
import uuid

from ginkgo.trading.paper.models import (
    PaperTradingState,
    PaperTradingSignal,
    PaperTradingResult,
    PaperTradingStatus,
)
from ginkgo.trading.paper.slippage_models import (
    SlippageModel,
    FixedSlippage,
    PercentageSlippage,
    NoSlippage,
    get_default_slippage_model,
)
from ginkgo.libs import GLOG


class PaperTradingEngine:
    """
    Paper Trading 引擎

    使用实盘数据验证策略表现，模拟交易执行但不实际下单。

    Attributes:
        portfolio_id: 关联的 Portfolio ID
        slippage_model: 滑点模型
        commission_rate: 佣金率
        commission_min: 最低佣金
        is_running: 是否正在运行
        state: Paper Trading 状态
        signals: 信号记录
    """

    def __init__(
        self,
        portfolio_id: Optional[str] = None,
        slippage_model: Union[str, SlippageModel] = "percentage",
        slippage_value: Decimal = Decimal("0.001"),
        commission_rate: Decimal = Decimal("0.0003"),
        commission_min: Decimal = Decimal("5"),
    ):
        """
        初始化 Paper Trading 引擎

        Args:
            portfolio_id: 关联的 Portfolio ID
            slippage_model: 滑点模型类型 ("fixed", "percentage", "none") 或 SlippageModel 实例
            slippage_value: 滑点值 (固定金额或百分比)
            commission_rate: 佣金率 (默认 0.03%)
            commission_min: 最低佣金 (默认 5 元)
        """
        self.portfolio_id = portfolio_id or ""
        self._portfolio = None

        # 初始化滑点模型
        if isinstance(slippage_model, SlippageModel):
            self.slippage_model = slippage_model
        elif slippage_model == "fixed":
            self.slippage_model = FixedSlippage(slippage=slippage_value)
        elif slippage_model == "percentage":
            self.slippage_model = PercentageSlippage(percentage=slippage_value)
        elif slippage_model == "none":
            self.slippage_model = NoSlippage()
        else:
            self.slippage_model = get_default_slippage_model()

        self.commission_rate = commission_rate
        self.commission_min = commission_min
        self._is_running = False

        # 状态和信号记录
        self._state = PaperTradingState(portfolio_id=self.portfolio_id)
        self._signals: List[PaperTradingSignal] = []

        GLOG.INFO(f"PaperTradingEngine 初始化: portfolio={portfolio_id}, slippage={slippage_model}")

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running

    @property
    def state(self) -> PaperTradingState:
        """当前状态"""
        return self._state

    @property
    def paper_id(self) -> str:
        """Paper Trading 实例 ID"""
        return self._state.paper_id

    def load_portfolio(self, portfolio_id: str) -> bool:
        """
        加载 Portfolio

        Args:
            portfolio_id: Portfolio ID

        Returns:
            是否加载成功
        """
        try:
            # TODO: 从数据库加载 Portfolio
            # from ginkgo import services
            # portfolio_crud = services.data.cruds.portfolio()
            # self._portfolio = portfolio_crud.get_by_id(portfolio_id)

            self.portfolio_id = portfolio_id
            self._state.portfolio_id = portfolio_id
            GLOG.INFO(f"加载 Portfolio: {portfolio_id}")
            return True
        except Exception as e:
            GLOG.ERROR(f"加载 Portfolio 失败: {e}")
            self._state.error_message = str(e)
            return False

    def start(self) -> bool:
        """
        启动 Paper Trading

        Returns:
            是否启动成功
        """
        if self._is_running:
            GLOG.WARN("Paper Trading 已在运行")
            return True

        if not self.portfolio_id:
            GLOG.ERROR("未指定 Portfolio，无法启动")
            return False

        try:
            self._is_running = True
            self._state.status = PaperTradingStatus.RUNNING
            self._state.started_at = datetime.now()
            GLOG.INFO(f"Paper Trading 启动: {self.paper_id}")
            return True
        except Exception as e:
            GLOG.ERROR(f"启动失败: {e}")
            self._state.error_message = str(e)
            self._state.status = PaperTradingStatus.ERROR
            return False

    def stop(self) -> bool:
        """
        停止 Paper Trading

        Returns:
            是否停止成功
        """
        if not self._is_running:
            GLOG.WARN("Paper Trading 未在运行")
            return True

        try:
            self._is_running = False
            self._state.status = PaperTradingStatus.STOPPED
            GLOG.INFO(f"Paper Trading 停止: {self.paper_id}")
            return True
        except Exception as e:
            GLOG.ERROR(f"停止失败: {e}")
            self._state.error_message = str(e)
            return False

    def on_daily_close(self, date: Optional[str] = None) -> List[PaperTradingSignal]:
        """
        处理日收盘事件

        每日收盘后调用，执行策略计算并生成信号。

        Args:
            date: 交易日期 (YYYYMMDD)，默认今天

        Returns:
            生成的信号列表
        """
        if not self._is_running:
            GLOG.WARN("Paper Trading 未运行，无法处理收盘事件")
            return []

        date = date or datetime.now().strftime("%Y%m%d")
        self._state.current_date = date

        try:
            # TODO: 实现完整逻辑
            # 1. 从 data 模块获取当日日K
            # 2. 调用 Portfolio 策略计算
            # 3. 应用滑点模型模拟成交
            # 4. 记录信号

            GLOG.INFO(f"处理收盘事件: {date}")

            # 更新统计
            self._state.last_signal_date = date

            return []

        except Exception as e:
            GLOG.ERROR(f"处理收盘事件失败: {e}")
            self._state.error_message = str(e)
            self._state.status = PaperTradingStatus.ERROR
            return []

    def get_current_state(self) -> PaperTradingState:
        """
        获取当前状态

        Returns:
            当前 Paper Trading 状态
        """
        return self._state

    def get_signals(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[PaperTradingSignal]:
        """
        获取信号记录

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            信号列表
        """
        signals = self._signals

        if start_date:
            signals = [s for s in signals if s.date >= start_date]
        if end_date:
            signals = [s for s in signals if s.date <= end_date]

        return signals

    def generate_signals(self, date: str) -> List[PaperTradingSignal]:
        """
        生成交易信号

        Args:
            date: 交易日期

        Returns:
            生成的信号列表
        """
        if not self._portfolio:
            GLOG.WARN("未加载 Portfolio，无法生成信号")
            return []

        try:
            # TODO: 调用 Portfolio 策略计算
            # signals = self._portfolio.strategies[0].cal(portfolio_info, event)

            signals = []
            return signals

        except Exception as e:
            GLOG.ERROR(f"生成信号失败: {e}")
            return []

    def compare_with_backtest(
        self,
        backtest_id: str,
        threshold: Decimal = Decimal("0.10"),
    ) -> PaperTradingResult:
        """
        与回测结果对比

        Args:
            backtest_id: 回测 ID
            threshold: 可接受差异阈值

        Returns:
            对比结果
        """
        result = PaperTradingResult(
            paper_id=self.paper_id,
            portfolio_id=self.portfolio_id,
            threshold=threshold,
        )

        try:
            # TODO: 从数据库获取回测结果
            # from ginkgo import services
            # backtest_result = services.data.cruds.backtest_result().get_by_id(backtest_id)
            # result.backtest_return = backtest_result.total_return

            # 统计信号
            result.paper_signals = len(self._signals)
            result.start_date = self._state.started_at.strftime("%Y%m%d") if self._state.started_at else None
            result.end_date = self._state.current_date

            GLOG.INFO(f"对比回测结果: paper={result.paper_return}, backtest={result.backtest_return}")

        except Exception as e:
            GLOG.ERROR(f"对比回测失败: {e}")
            result.metadata["error"] = str(e)

        return result

    def calculate_commission(self, amount: Decimal) -> Decimal:
        """
        计算佣金

        Args:
            amount: 交易金额

        Returns:
            佣金金额
        """
        commission = amount * self.commission_rate
        return max(commission, self.commission_min)

    def apply_slippage(
        self,
        price: Decimal,
        direction: Any,
    ) -> Decimal:
        """
        应用滑点

        Args:
            price: 原始价格
            direction: 交易方向

        Returns:
            调整后的价格
        """
        from ginkgo.enums import DIRECTION_TYPES

        if not isinstance(direction, DIRECTION_TYPES):
            # 尝试转换
            if direction in ("LONG", "BUY", 1):
                direction = DIRECTION_TYPES.LONG
            else:
                direction = DIRECTION_TYPES.SHORT

        return self.slippage_model.apply(price, direction)

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "paper_id": self.paper_id,
            "portfolio_id": self.portfolio_id,
            "is_running": self._is_running,
            "slippage_model": repr(self.slippage_model),
            "commission_rate": str(self.commission_rate),
            "commission_min": str(self.commission_min),
            "state": self._state.to_dict(),
            "signal_count": len(self._signals),
        }
