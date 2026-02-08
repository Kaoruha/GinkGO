"""
Saga 事务管理器测试

测试 Saga 模式的事务一致性和补偿机制。
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from services.saga_transaction import SagaTransaction, SagaStep, PortfolioSagaFactory
from models.transaction import TransactionRecord


@pytest.mark.tdd
class TestSagaStep:
    """测试 SagaStep 数据类"""

    def test_saga_step_creation(self):
        """测试 SagaStep 创建"""
        execute = lambda: "result"
        compensate = lambda r: f"compensated: {r}"

        step = SagaStep(
            name="test_step",
            execute=execute,
            compensate=compensate
        )

        assert step.name == "test_step"
        assert step.execute == execute
        assert step.compensate == compensate
        assert not step.executed
        assert not step.compensated
        assert step.result is None
        assert step.error is None
        assert step.executed_at is None
        assert step.compensated_at is None


@pytest.mark.tdd
class TestSagaTransaction:
    """测试 SagaTransaction 事务管理器"""

    @pytest.fixture
    def saga(self):
        """创建 SagaTransaction 实例"""
        return SagaTransaction("test_transaction")

    def test_saga_init(self, saga):
        """测试 SagaTransaction 初始化"""
        assert saga.name == "test_transaction"
        assert saga.transaction_id is not None
        assert len(saga.steps) == 0
        assert len(saga.completed_steps) == 0
        assert not saga.failed
        assert saga.error is None
        assert isinstance(saga.created_at, datetime)

    def test_add_step(self, saga):
        """测试添加步骤"""
        execute = lambda: "result"
        compensate = lambda r: None

        result = saga.add_step("step1", execute, compensate)

        assert result is saga  # 支持链式调用
        assert len(saga.steps) == 1
        assert saga.steps[0].name == "step1"

    @pytest.mark.asyncio
    async def test_execute_success(self, saga):
        """测试成功执行所有步骤"""
        executed_order = []

        def step1():
            executed_order.append("step1")
            return "result1"

        def step2():
            executed_order.append("step2")
            return "result2"

        saga.add_step("step1", step1, lambda r: executed_order.append(f"compensate1"))
        saga.add_step("step2", step2, lambda r: executed_order.append(f"compensate2"))

        success = await saga.execute()

        assert success is True
        assert executed_order == ["step1", "step2"]
        assert len(saga.completed_steps) == 2
        assert not saga.failed

    @pytest.mark.asyncio
    async def test_execute_failure_with_compensation(self, saga):
        """测试失败时执行补偿"""
        executed_order = []

        def step1():
            executed_order.append("step1")
            return "result1"

        def step2():
            executed_order.append("step2")
            raise Exception("Step 2 failed")

        def compensate1(r):
            executed_order.append("compensate1")

        saga.add_step("step1", step1, compensate1)
        saga.add_step("step2", step2, lambda r: executed_order.append("compensate2"))

        success = await saga.execute()

        assert success is False
        assert executed_order == ["step1", "step2", "compensate1"]
        assert len(saga.completed_steps) == 1  # 只有 step1 完成
        assert saga.failed is True
        assert isinstance(saga.error, Exception)

    @pytest.mark.asyncio
    async def test_compensate_failure_continues(self, saga):
        """测试补偿失败时继续其他补偿"""
        executed_order = []

        def step1():
            return "result1"

        def step2():
            return "result2"

        def compensate1(r):
            executed_order.append("compensate1")
            raise Exception("Compensate 1 failed")

        def compensate2(r):
            executed_order.append("compensate2")

        saga.add_step("step1", step1, compensate1)
        saga.add_step("step2", step2, compensate2)

        # 让 step2 失败
        saga.steps[1].execute = lambda: (_ for _ in ()).throw(Exception("Step 2 failed"))

        success = await saga.execute()

        assert success is False
        # 两个补偿都应该尝试执行
        assert "compensate2" in executed_order

    @pytest.mark.asyncio
    async def test_async_execute(self, saga):
        """测试异步执行函数"""
        async def async_step():
            return "async_result"

        saga.add_step("async_step", async_step, lambda r: None)

        success = await saga.execute()

        assert success is True
        assert saga.completed_steps[0].result == "async_result"

    @pytest.mark.asyncio
    async def test_async_compensate(self, saga):
        """测试异步补偿函数"""
        async def async_step():
            raise Exception("Failed")

        async def async_compensate(r):
            return "compensated"

        saga.add_step("async_step", async_step, async_compensate)

        success = await saga.execute()

        assert success is False
        assert saga.completed_steps[0].compensated is True

    def test_to_record(self, saga):
        """测试转换为事务记录"""
        saga.add_step("step1", lambda: "result1", lambda r: None)

        record = saga.to_record()

        assert isinstance(record, TransactionRecord)
        assert record.transaction_id == saga.transaction_id
        assert len(record.steps) == 1
        assert record.steps[0].name == "step1"


@pytest.mark.tdd
class TestPortfolioSagaFactory:
    """测试 PortfolioSagaFactory 工厂类"""

    @pytest.fixture
    def mock_services(self):
        """Mock 服务实例"""
        portfolio_service = Mock()
        mapping_service = Mock()
        file_service = Mock()

        # Mock portfolio result
        portfolio_result = Mock()
        portfolio_result.is_success.return_value = True
        portfolio_result.data.uuid = "test-portfolio-uuid"
        portfolio_service.add.return_value = portfolio_result
        portfolio_service.get.return_value = portfolio_result

        return {
            'portfolio_service': portfolio_service,
            'mapping_service': mapping_service,
            'file_service': file_service
        }

    def test_create_portfolio_saga_structure(self, mock_services):
        """测试创建 Portfolio Saga 的结构"""
        with patch('services.saga_transaction.container') as mock_container:
            mock_container.portfolio_service.return_value = mock_services['portfolio_service']
            mock_container.portfolio_mapping_service.return_value = mock_services['mapping_service']

            saga = PortfolioSagaFactory.create_portfolio_saga(
                name="Test Portfolio",
                is_live=False,
                selectors=[{"component_uuid": "sel-1", "config": {}}],
                sizer={"component_uuid": "sz-1", "config": {}},
                strategies=[{"component_uuid": "str-1", "config": {}}],
                risk_managers=[{"component_uuid": "risk-1", "config": {}}],
                analyzers=[{"component_uuid": "ana-1", "config": {}}]
            )

            # 验证步骤数量
            # create_portfolio(1) + selector(1) + sizer(1) + strategy(1) + risk(1) + analyzer(1) = 6
            assert len(saga.steps) == 6

            # 验证第一步是创建 portfolio
            assert saga.steps[0].name == "create_portfolio"

            # 验证最后几步是添加组件
            step_names = [step.name for step in saga.steps]
            assert "add_selector_sel-1" in step_names
            assert "add_sizer" in step_names
            assert "add_strategy_str-1" in step_names

    @pytest.mark.asyncio
    async def test_create_portfolio_saga_success(self, mock_services):
        """测试成功创建 Portfolio"""
        with patch('services.saga_transaction.container') as mock_container:
            mock_container.portfolio_service.return_value = mock_services['portfolio_service']
            mock_container.portfolio_mapping_service.return_value = mock_services['mapping_service']

            saga = PortfolioSagaFactory.create_portfolio_saga(
                name="Test Portfolio",
                is_live=False,
                selectors=[{"component_uuid": "sel-1", "config": {}}],
                sizer=None,
                strategies=[{"component_uuid": "str-1", "config": {}}],
                risk_managers=[],
                analyzers=[]
            )

            success = await saga.execute()

            assert success is True
            assert mock_services['portfolio_service'].add.called
            assert mock_services['mapping_service'].add_file.call_count == 2  # 1 selector + 1 strategy

    @pytest.mark.asyncio
    async def test_create_portfolio_saga_failure_compensates(self, mock_services):
        """测试创建失败时执行补偿"""
        # 设置 mapping_service 在添加 strategy 时失败
        mock_services['mapping_service'].add_file.side_effect = [
            None,  # selector 成功
            Exception("Strategy add failed")  # strategy 失败
        ]

        with patch('services.saga_transaction.container') as mock_container:
            mock_container.portfolio_service.return_value = mock_services['portfolio_service']
            mock_container.portfolio_mapping_service.return_value = mock_services['mapping_service']

            saga = PortfolioSagaFactory.create_portfolio_saga(
                name="Test Portfolio",
                is_live=False,
                selectors=[{"component_uuid": "sel-1", "config": {}}],
                sizer=None,
                strategies=[{"component_uuid": "str-1", "config": {}}],
                risk_managers=[],
                analyzers=[]
            )

            success = await saga.execute()

            assert success is False
            # 验证 portfolio 被删除（补偿）
            mock_services['portfolio_service'].delete.assert_called_once()

    def test_delete_portfolio_saga_structure(self, mock_services):
        """测试删除 Portfolio Saga 的结构"""
        with patch('services.saga_transaction.container') as mock_container:
            mock_container.portfolio_service.return_value = mock_services['portfolio_service']
            mock_container.portfolio_mapping_service.return_value = mock_services['mapping_service']

            # Mock mapping_crud
            mock_mapping_crud = Mock()
            mock_mapping_crud.find_by_portfolio.return_value = []
            mock_container.mongo_driver.return_value = Mock()
            mock_container.PortfolioFileMappingCRUD.return_value = mock_mapping_crud

            saga = PortfolioSagaFactory.delete_portfolio_saga("test-uuid")

            assert len(saga.steps) == 3  # get_mappings, remove_mappings, delete_portfolio
            assert saga.steps[0].name == "get_mappings"
            assert saga.steps[1].name == "remove_mappings"
            assert saga.steps[2].name == "delete_portfolio"

    def test_update_portfolio_saga_structure(self, mock_services):
        """测试更新 Portfolio Saga 的结构"""
        with patch('services.saga_transaction.container') as mock_container:
            mock_container.portfolio_service.return_value = mock_services['portfolio_service']
            mock_container.portfolio_mapping_service.return_value = mock_services['mapping_service']

            # Mock mapping_crud
            mock_mapping_crud = Mock()
            mock_mapping_crud.find_by_portfolio.return_value = []
            mock_container.mongo_driver.return_value = Mock()
            mock_container.PortfolioFileMappingCRUD.return_value = mock_mapping_crud
            mock_container.file_service.return_value = mock_services['file_service']

            saga = PortfolioSagaFactory.update_portfolio_saga(
                portfolio_uuid="test-uuid",
                name="New Name",
                selectors=[{"component_uuid": "sel-1", "config": {}}],
                strategies=[]
            )

            # backup_state, update_basic_info, remove_old_mappings, add_selector
            assert len(saga.steps) >= 3
            assert saga.steps[0].name == "backup_state"
            assert saga.steps[1].name == "update_basic_info"
            assert saga.steps[2].name == "remove_old_mappings"
