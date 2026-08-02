# Upstream: PortfolioService (删除组合时清理信号)、BacktestTaskService (重跑前清理旧信号)、
#           T1Backtest._emit_signal (回测信号持久化 seam)
# Downstream: SignalCRUD (信号数据访问)、SignalMapper (Entity↔ORM 收敛)、GLOG (日志)
# Role: 信号业务服务，提供查询、delete_signals_by_portfolio、add 等接口


from typing import Any, Optional

import pandas as pd

from ginkgo.data.mappers import SignalMapper
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import GLOG, datetime_normalize


class SignalService(BaseService):
    """
    信号业务服务层。

    编排 SignalCRUD 的数据访问操作，提供业务语义化的接口。
    """

    def __init__(self, crud_repo=None, **kwargs):
        super().__init__(crud_repo=crud_repo, **kwargs)

    def add(
        self,
        portfolio_id: str,
        engine_id: str,
        task_id: str,
        code: str,
        direction: DIRECTION_TYPES,
        reason: str,
        source: SOURCE_TYPES = SOURCE_TYPES.OTHER,
        timestamp: Any = None,
        business_timestamp: Any = None,
        volume: int = 0,
        weight: float = 0.0,
        strength: float = 0.5,
        confidence: float = 0.5,
        uuid: str = "",
        **kwargs,
    ) -> ServiceResult:
        """持久化一条 Signal 记录（ADR-029 Task 6）。

        链路:kwargs → Signal entity → SignalMapper.entity_to_model → crud.add(model)。
        替代 t1backtest 直调 signal_crud.create(**kwargs) 的隐式 _create_from_params 路径,
        显式经 Signal entity → SignalMapper 收敛转换(退役 _convert_input_item hook)。

        Args:
            portfolio_id/engine_id/task_id: 上下文 UUID 三元组
            code: 标的代码
            direction: DIRECTION_TYPES 枚举(LONG/SHORT/OTHER/VOID)
            reason: 信号原因(非空)
            source: SOURCE_TYPES 枚举(默认 OTHER;回测由调用方传 STRATEGY/RISK)
            timestamp: 现实时间戳(默认 None→TimeMixin 用 datetime.now)
            business_timestamp: 业务时间戳(回测价格事件时间)
            volume/weight/strength/confidence: 信号扩展字段
            uuid: 显式 UUID(空则 Signal 构造自动生成)

        Returns:
            ServiceResult.data: {"uuid": 写入 model.uuid}
        """
        try:
            # kwargs → Signal entity
            entity = Signal(
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                task_id=task_id,
                code=code,
                direction=direction,
                reason=reason,
                source=source,
                volume=volume,
                weight=weight,
                strength=strength,
                confidence=confidence,
                uuid=uuid,
                business_timestamp=business_timestamp,
            )
            # 显式设 timestamp(TimeMixin 默认 datetime.now,回测传业务时间覆盖)
            if timestamp is not None:
                entity.timestamp = timestamp

            # Signal entity → mapper → crud.add(model)
            model = SignalMapper.entity_to_model(entity)
            self._crud_repo.add(model)
            return ServiceResult.success(
                data={"uuid": model.uuid},
                message=f"Signal added: {code} {getattr(direction, 'name', direction)}",
            )
        except Exception as e:
            GLOG.ERROR(f"signal_service.add failed: {e}")
            return ServiceResult.error(str(e))

    def get_signals(
        self,
        engine_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        page_size: int = 50,
    ) -> ServiceResult:
        """
        查询信号记录。

        Args:
            engine_id: 引擎 ID（可选）
            portfolio_id: 组合 ID（可选）
            page_size: 返回数量限制，0 表示全部

        Returns:
            ServiceResult.data: ModelList
        """
        try:
            filters = {"is_del": False}
            if engine_id:
                filters["engine_id"] = engine_id
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            results = self._crud_repo.find(
                filters=filters,
                page_size=(
                    page_size if page_size and page_size > 0 else None
                ),  # None 守卫：0=全量下推 None，裸 >0 对 None 报 TypeError
            )
            return ServiceResult.success(data=results)
        except Exception as e:
            GLOG.ERROR(f"查询信号失败: {e}")
            return ServiceResult.error(str(e))

    def get_signals_by_portfolio(
        self,
        portfolio_id: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> ServiceResult:
        """
        按组合查询信号（日期范围下推到 crud.find_by_portfolio，#6030）。

        Args:
            portfolio_id: 组合 UUID
            start_date: 起始时间（可选，下推为 timestamp__gte）
            end_date: 结束时间（可选，下推为 timestamp__lte）

        Returns:
            ServiceResult.data: List[Signal]
        """
        if not portfolio_id:
            return ServiceResult.error("portfolio_id 不能为空")
        try:
            results = self._crud_repo.find_by_portfolio(
                portfolio_id=portfolio_id,
                start_date=start_date,
                end_date=end_date,
            )
            return ServiceResult.success(data=results)
        except Exception as e:
            GLOG.ERROR(f"查询组合信号失败: {e}")
            return ServiceResult.error(str(e))

    def _build_signal_filters(
        self,
        engine_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> dict:
        """从业务参数构造 Signal CRUD filters。get_signals_df 独立使用（DRY）。

        filter 域与 Order/Position 三维对称（engine_id/portfolio_id/task_id），
        固定排除 is_del=True。未抽改 get_signals()，保持纯增量。
        """
        filters = {"is_del": False}
        if engine_id:
            filters["engine_id"] = engine_id
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if task_id:
            filters["task_id"] = task_id
        return filters

    def get_signals_df(
        self,
        engine_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        task_id: Optional[str] = None,
        page: int = None,
        page_size: int = 50,
    ) -> ServiceResult:
        """出口①：data 是 pandas.DataFrame（类型即契约）。

        ADR-010：API/CLI 消费 DataFrame 语义时走此出口，不接触 ORM ModelList、
        不再绕 ``result.data.to_dataframe()``。内部 find 返 ModelList 后调
        ``to_dataframe()``；空结果返空 ``pd.DataFrame()``。

        #5009：page（0-based）/page_size 分页；MSignal 为 ClickHouse（MClickBase），
        order_by=timestamp desc 保证分页确定性（CH MergeTree 无隐式顺序保证，
        缺 order_by 则分页结果不稳定；对齐 analyzer/result_service 同族出口）。
        """
        try:
            filters = self._build_signal_filters(
                engine_id=engine_id,
                portfolio_id=portfolio_id,
                task_id=task_id,
            )
            model_list = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=(
                    page_size if page_size and page_size > 0 else None
                ),  # None 守卫：0=全量下推 None，裸 >0 对 None 报 TypeError
                order_by="timestamp",
                desc_order=True,
            )
            df = model_list.to_dataframe() if model_list else pd.DataFrame()
            return ServiceResult.success(
                data=df,
                message=f"Retrieved {len(df)} signal records (DataFrame)",
            )
        except Exception as e:
            GLOG.ERROR(f"查询信号(df)失败: {str(e)}")
            return ServiceResult.error(f"查询信号(df)失败: {str(e)}")

    def count_signals(
        self,
        engine_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> ServiceResult:
        """统计匹配信号总数（#5009：metadata.total 真实总数，非 len(df)）。"""
        try:
            filters = self._build_signal_filters(
                engine_id=engine_id,
                portfolio_id=portfolio_id,
                task_id=task_id,
            )
            count = self._crud_repo.count(filters=filters)
            return ServiceResult.success({"count": count}, f"Successfully counted signals: {count}")
        except Exception as e:
            GLOG.ERROR(f"统计信号失败: {str(e)}")
            return ServiceResult.error(f"统计信号失败: {str(e)}")

    def delete_signals_by_portfolio(self, portfolio_id: str) -> ServiceResult:
        """
        删除指定组合的所有信号记录。

        Args:
            portfolio_id: 组合 UUID

        Returns:
            ServiceResult
        """
        if not portfolio_id:
            return ServiceResult.error("portfolio_id 不能为空")

        try:
            self._crud_repo.remove(filters={"portfolio_id": portfolio_id})
            GLOG.WARN(f"已删除组合 {portfolio_id} 的所有信号记录")
            return ServiceResult.success(message="信号删除成功")
        except Exception as e:
            GLOG.ERROR(f"删除组合信号失败: {e}")
            return ServiceResult.error(str(e))

    def delete_signals_by_portfolio_and_date_range(
        self,
        portfolio_id: str,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
    ) -> ServiceResult:
        """
        删除指定组合在日期范围内的信号记录。

        Args:
            portfolio_id: 组合 UUID
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            ServiceResult
        """
        if not portfolio_id:
            return ServiceResult.error("portfolio_id 不能为空")

        try:
            filters = {"portfolio_id": portfolio_id}
            if start_date:
                filters["timestamp__gte"] = datetime_normalize(start_date)
            if end_date:
                filters["timestamp__lte"] = datetime_normalize(end_date)

            self._crud_repo.remove(filters=filters)
            GLOG.INFO(f"已删除组合 {portfolio_id} 在指定日期范围内的信号记录")
            return ServiceResult.success(message="信号删除成功")
        except Exception as e:
            GLOG.ERROR(f"删除组合信号失败: {e}")
            return ServiceResult.error(str(e))
