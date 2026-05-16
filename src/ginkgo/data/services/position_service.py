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

    def upsert_position(self, position) -> ServiceResult:
        """
        创建或更新持仓（upsert 语义）。

        按 portfolio_id + code 查找已存在记录，存在则更新，不存在则创建。

        Args:
            position: Position 或 duck-typed 对象，需包含 portfolio_id, code 等属性

        Returns:
            ServiceResult
        """
        try:
            existing = self._crud_repo.get_position(
                portfolio_id=position.portfolio_id,
                code=position.code,
            )

            if existing:
                self._crud_repo.update_position(
                    portfolio_id=position.portfolio_id,
                    code=position.code,
                    cost=position.cost,
                    volume=position.volume,
                    frozen_volume=position.frozen_volume,
                    frozen_money=position.frozen_money,
                    price=position.price,
                    fee=position.fee,
                )
                GLOG.DEBUG(f"Updated position: {position.code}")
            else:
                self._crud_repo.add(position)
                GLOG.DEBUG(f"Created position: {position.code}")

            return ServiceResult.success(
                data={"updated": existing is not None, "created": existing is None},
                message="Position upserted successfully",
            )
        except Exception as e:
            GLOG.ERROR(f"upsert_position failed: {e}")
            return ServiceResult.error(str(e))
