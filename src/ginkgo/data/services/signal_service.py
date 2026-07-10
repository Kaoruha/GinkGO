# Upstream: PortfolioService (删除组合时清理信号)、BacktestTaskService (重跑前清理旧信号)
# Downstream: SignalCRUD (信号数据访问)、GLOG (日志)
# Role: 信号业务服务，提供查询、delete_signals_by_portfolio 等接口


from typing import Any, Optional

import pandas as pd

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG, datetime_normalize


class SignalService(BaseService):
    """
    信号业务服务层。

    编排 SignalCRUD 的数据访问操作，提供业务语义化的接口。
    """

    def __init__(self, crud_repo=None, **kwargs):
        super().__init__(crud_repo=crud_repo, **kwargs)

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
                page_size=page_size if page_size > 0 else None,
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

        #5009：page（0-based）/page_size 分页；MSignalTracker 为 MySQL，order_by=create_at
        desc 保证分页确定性（MySQL 无隐式顺序，缺 order_by 则分页结果不稳定）。
        """
        try:
            filters = self._build_signal_filters(
                engine_id=engine_id, portfolio_id=portfolio_id, task_id=task_id,
            )
            model_list = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size if page_size > 0 else None,
                order_by="create_at",
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
                engine_id=engine_id, portfolio_id=portfolio_id, task_id=task_id,
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
