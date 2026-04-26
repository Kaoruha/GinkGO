# Upstream: ValidationService
# Downstream: BaseCRUD, MValidationResult
# Role: 验证结果 CRUD 操作

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models.model_validation_result import MValidationResult


class ValidationResultCRUD(BaseCRUD):
    """验证结果 CRUD"""

    _model_class = MValidationResult

    def __init__(self):
        super().__init__(MValidationResult)

    def get_by_portfolio(self, portfolio_id: str):
        return self.find(filters={"portfolio_id": portfolio_id})

    def get_by_task(self, task_id: str):
        return self.find(filters={"task_id": task_id})

    def get_by_method(self, method: str):
        return self.find(filters={"method": method})
