# DEPRECATED: 本文件已废弃，未来将被移除。验证结果存储方案需重新设计。
# Upstream: ValidationService
# Downstream: BaseCRUD, MValidationResult
# Role: 验证结果 CRUD 操作

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MValidationResult


class ValidationResultCRUD(BaseCRUD):
    """DEPRECATED: 已废弃，未来将被移除。验证结果存储方案需重新设计。

    验证结果 CRUD"""

    _model_class = MValidationResult

    def __init__(self):
        super().__init__(MValidationResult)

    def get_by_portfolio(self, portfolio_id: str):
        return self.find(filters={"portfolio_id": portfolio_id})

    def get_by_task(self, task_id: str):
        return self.find(filters={"task_id": task_id})

    def get_by_method(self, method: str):
        return self.find(filters={"method": method})
