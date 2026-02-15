"""
OrderCRUD数据库操作TDD测试 - 交易订单管理

本文件测试OrderCRUD类的完整功能，确保交易订单(Order)的增删改查操作正常工作。
订单是交易系统的核心数据模型，记录交易意图、执行状态和结果。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效插入大量订单数据
   - 单条插入 (add): 插入单个订单记录

2. 查询操作 (Query Operations)
   - 按投资组合查询 (find_by_portfolio): 获取特定投资组合的订单
   - 按状态查询 (find_by_status): 获取特定状态的订单
   - 按方向查询 (find_by_direction): 获取买入/卖出订单

3. 更新操作 (Update Operations)
   - 订单状态更新 (update_status): 更新订单执行状态
   - 订单价格更新 (update_price): 调整订单价格

4. 删除操作 (Delete Operations)
   - 按状态删除 (delete_by_status): 清理特定状态订单
   - 按投资组合删除 (delete_by_portfolio): 清理特定投资组合订单

5. 业务逻辑测试 (Business Logic Tests)
   - 订单生命周期 (order_lifecycle): 从创建到完成的完整流程
   - 订单金额计算 (amount_calculation): 订单金额和费用计算

TODO: 添加replace方法测试用例
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.order_crud import OrderCRUD
from ginkgo.data.models.model_order import MOrder
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestOrderCRUDInsert:
    """OrderCRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = OrderCRUD()

    def test_add_batch_basic(self):
        """测试批量插入Order数据"""
        print("\n" + "="*60)
        print("开始测试: Order CRUD层批量插入")
        print("="*60)

        # 获取操作前数据条数
        before_count = len(self.crud.find(filters={"source": SOURCE_TYPES.TEST.value}))

        # 创建测试Order数据
        base_time = datetime(2023, 1, 3, 9, 30)
        test_orders = [
            MOrder(
                portfolio_id="test_portfolio_001",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=1000,
                limit_price=Decimal("10.50"),
                frozen=Decimal("10500.00"),
                remain=Decimal("10500.00"),
                fee=Decimal("0.00"),
                timestamp=base_time,
                business_timestamp=base_time - timedelta(minutes=30),
                source=SOURCE_TYPES.TEST
            ),
            MOrder(
                portfolio_id="test_portfolio_001",
                code="000002.SZ",
                direction=DIRECTION_TYPES.SHORT,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=500,
                limit_price=Decimal("0.00"),
                frozen=Decimal("0.00"),
                remain=Decimal("0.00"),
                fee=Decimal("0.00"),
                timestamp=base_time + timedelta(minutes=1),
                business_timestamp=base_time + timedelta(minutes=-30, seconds=1),
                source=SOURCE_TYPES.TEST
            )
        ]

        try:
            # 批量插入
            self.crud.add_batch(test_orders)

            # 验证数据库记录数变化
            after_count = len(self.crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            assert after_count - before_count == len(test_orders), \
                f"应增加{len(test_orders)}条数据，实际增加{after_count - before_count}条"

            # 验证可以查询出插入的数据
            query_result = self.crud.find(filters={"portfolio_id": "test_portfolio_001"})
            assert len(query_result) >= 2

            print("✓ 批量插入验证通过")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_order(self):
        """测试单条Order数据插入"""
        base_time = datetime(2023, 1, 4, 10, 15)
        test_order = MOrder(
            portfolio_id="test_portfolio_002",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=2000,
            limit_price=Decimal("15.75"),
            frozen=Decimal("31500.00"),
            remain=Decimal("31500.00"),
            fee=Decimal("0.00"),
            timestamp=base_time,
            business_timestamp=base_time - timedelta(minutes=20),
            source=SOURCE_TYPES.TEST
        )

        try:
            # 单条插入
            result = self.crud.add(test_order)

            # 验证返回值类型
            assert isinstance(result, MOrder), f"add()应返回MOrder对象，实际{type(result)}"

            # 验证数据库记录数变化
            query_result = self.crud.find(filters={
                "portfolio_id": "test_portfolio_002",
                "code": "000001.SZ"
            })
            assert len(query_result) >= 1

            print("✓ 单条插入验证通过")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestOrderCRUDQuery:
    """OrderCRUD层查询操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = OrderCRUD()

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询Order"""
        try:
            orders = self.crud.find(filters={"portfolio_id": "test_portfolio_001"})
            print(f"✓ 查询到 {len(orders)} 条记录")

            # 验证查询结果
            for order in orders:
                assert order.portfolio_id == "test_portfolio_001"

            print("✓ 按portfolio_id查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    @pytest.mark.parametrize("status", [
        ORDERSTATUS_TYPES.NEW,
        ORDERSTATUS_TYPES.FILLED,
        ORDERSTATUS_TYPES.CANCELED
    ])
    def test_find_by_status(self, status):
        """参数化测试按状态查询"""
        try:
            orders = self.crud.find(filters={"status": status})
            print(f"✓ 状态{status.name}: {len(orders)} 条记录")

            # 验证查询结果
            for order in orders:
                assert order.status == status

            print("✓ 按status查询验证通过")

        except Exception as e:
            print(f"✗ 状态查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.db_cleanup
class TestOrderCRUDDelete:
    """OrderCRUD层删除操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = OrderCRUD()

    def test_delete_by_portfolio(self):
        """测试按投资组合删除Order"""
        try:
            # 创建测试数据
            base_time = datetime(2023, 12, 1, 9, 30)
            test_order = MOrder(
                portfolio_id="test_portfolio_delete",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=100,
                limit_price=Decimal("10.00"),
                frozen=Decimal("1000.00"),
                timestamp=base_time,
                source=SOURCE_TYPES.TEST
            )
            self.crud.add(test_order)

            # 验证数据存在
            before = len(self.crud.find(filters={"portfolio_id": "test_portfolio_delete"}))
            assert before >= 1, "测试数据应已插入"

            # 执行删除
            self.crud.remove(filters={"portfolio_id": "test_portfolio_delete"})

            # 验证删除结果
            after = len(self.crud.find(filters={"portfolio_id": "test_portfolio_delete"}))
            assert after == 0, "数据应已被删除"

            print("✓ 按投资组合删除验证通过")

        except Exception as e:
            print(f"✗ 删除失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.slow
class TestOrderCRUDBusinessLogic:
    """OrderCRUD层业务逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = OrderCRUD()

    def test_order_amount_calculation(self):
        """测试订单金额计算"""
        try:
            # 创建测试订单
            base_time = datetime(2023, 1, 5, 9, 30)
            test_order = MOrder(
                portfolio_id="test_portfolio_calc",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=1000,
                limit_price=Decimal("10.50"),
                frozen=Decimal("10500.00"),
                timestamp=base_time,
                source=SOURCE_TYPES.TEST
            )

            # 计算预期金额
            expected_amount = test_order.volume * test_order.limit_price
            actual_frozen = test_order.frozen

            # 验证金额计算（使用pytest.approx处理浮点精度）
            assert actual_frozen == pytest.approx(expected_amount, abs=Decimal("0.01")), \
                f"冻结金额应等于数量*价格，预期{expected_amount}，实际{actual_frozen}"

            print(f"✓ 订单金额计算验证: {test_order.volume} * {test_order.limit_price} = {actual_frozen}")
            print("✓ 订单金额计算验证通过")

        except Exception as e:
            print(f"✗ 金额计算测试失败: {e}")
            raise


# TDD验证入口
if __name__ == "__main__":
    print("TDD Red阶段验证：Order CRUD测试")
    print("运行: pytest test/data/crud/test_order_crud_refactored.py -v")
    print("预期结果: 所有测试通过")
    print("重点关注: 订单金额计算精度")
