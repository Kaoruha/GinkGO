# Upstream: PortfolioService (删除组合时清理信号)、BacktestTaskService (重跑前清理旧信号)
# Downstream: SignalCRUD (信号数据访问)、GLOG (日志)
# Role: 信号业务服务，提供查询、delete_signals_by_portfolio 等接口


from typing import Any, Optional

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
