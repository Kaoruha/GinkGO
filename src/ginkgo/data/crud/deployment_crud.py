# Upstream: DeploymentService
# Downstream: BaseCRUD (继承提供标准CRUD能力)、MDeployment (MySQL deployment表)
# Role: 部署记录CRUD操作

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models.model_deployment import MDeployment


class DeploymentCRUD(BaseCRUD):
    """部署记录CRUD"""

    _model_class = MDeployment

    def __init__(self):
        super().__init__(MDeployment)

    def get_by_target_portfolio(self, portfolio_id: str):
        """根据目标Portfolio ID查询部署记录"""
        return self.find(filters={"target_portfolio_id": portfolio_id})

    def get_by_source_task(self, task_id: str):
        """根据源回测任务ID查询部署记录"""
        return self.find(filters={"source_task_id": task_id})
