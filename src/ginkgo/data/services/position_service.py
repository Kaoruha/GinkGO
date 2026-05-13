# Upstream: PortfolioLive (构造函数注入的 position_writer)
# Downstream: PositionCRUD (持仓持久化)、GLOG (日志)
# Role: 持仓业务服务，提供 save_positions / get_positions 等接口


from typing import List, Optional, Any

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG, to_decimal


class PositionService(BaseService):
    """
    持仓业务服务层。

    编排 PositionCRUD 的数据访问操作，提供业务语义化的接口。
    作为 PortfolioLive 的 position_writer 注入。
    """

    def __init__(self, crud_repo=None, **kwargs):
        super().__init__(crud_repo=crud_repo, **kwargs)

    def save_positions(self, positions: list) -> ServiceResult:
        """
        持久化持仓列表（逐条写入）。

        Args:
            positions: 持仓实体列表（Position 或 duck-typed 对象）

        Returns:
            ServiceResult
        """
        try:
            for pos in positions:
                self._crud_repo.create(pos)
            GLOG.DEBUG(f"Saved {len(positions)} positions")
            return ServiceResult.success(data={"count": len(positions)})
        except Exception as e:
            GLOG.ERROR(f"save_positions failed: {e}")
            return ServiceResult.error(str(e))

    def get_positions(self, portfolio_id: str) -> ServiceResult:
        """
        查询指定 portfolio 的持仓。
        """
        try:
            result = self._crud_repo.find_by_portfolio(portfolio_id)
            return ServiceResult.success(data=result)
        except Exception as e:
            GLOG.ERROR(f"get_positions failed: {e}")
            return ServiceResult.error(str(e))

    def get_portfolio_value(self, portfolio_id: str) -> ServiceResult:
        """
        获取 portfolio 持仓总市值。
        """
        try:
            result = self._crud_repo.get_portfolio_value(portfolio_id)
            return ServiceResult.success(data=result)
        except Exception as e:
            GLOG.ERROR(f"get_portfolio_value failed: {e}")
            return ServiceResult.error(str(e))
