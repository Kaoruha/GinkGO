# Upstream: DeploymentService
# Downstream: BaseCRUD (继承提供标准CRUD能力)、MDeployment (MySQL deployment表)
# Role: 部署记录CRUD操作

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MDeployment


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

    def get_by_source_portfolio(self, portfolio_id: str):
        """根据源Portfolio ID查询部署记录"""
        return self.find(filters={"source_portfolio_id": portfolio_id})

    def get_by_uuid(self, deployment_id: str):
        """根据部署记录 uuid(deployment_id) 查询。

        #5952/#5939: deploy deploy 返回的 ID 即记录 uuid（list_deployments
        输出的 deployment_id）。deploy info 应按此查，不可与 target_portfolio_id 混淆。
        """
        return self.find(filters={"uuid": deployment_id})
