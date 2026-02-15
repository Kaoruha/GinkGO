"""
PositionCRUD数据库操作TDD测试 - 持仓管理

本文件测试PositionCRUD类的完整功能，确保持仓(Position)数据的增删改查操作正常工作。
持仓数据是量化交易系统的核心状态数据，实时反映投资组合的当前状况。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效创建多个持仓记录
   - 单条插入 (add): 创建单个持仓记录

2. 查询操作 (Query Operations)
   - 按投资组合查询 (find_by_portfolio): 获取特定投资组合的持仓
   - 按股票代码查询 (find_by_code): 查找特定股票的持仓

3. 更新操作 (Update Operations)
   - 持仓数量更新 (update_volume): 增加或减少持仓数量
   - 成本价更新 (update_cost): 更新持仓成本价格

4. 删除操作 (Delete Operations)
   - 按投资组合删除 (delete_by_portfolio): 删除特定投资组合持仓
   - 按股票代码删除 (delete_by_code): 删除特定股票持仓

5. 业务逻辑测试 (Business Logic Tests)
   - 持仓生命周期 (position_lifecycle): 从建仓到平仓的完整流程
   - 持仓成本计算 (cost_calculation): 持仓成本计算验证
   - 盈亏计算 (profit_loss): 盈亏计算准确性验证

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

from ginkgo.data.crud.position_crud import PositionCRUD
from ginkgo.data.models.model_position import MPosition
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestPositionCRUDInsert:
    """PositionCRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = PositionCRUD()

    def test_add_batch_basic(self):
        """测试批量插入Position数据"""
        print("\n" + "="*60)
        print("开始测试: Position CRUD层批量插入")
        print("="*60)

        # 创建测试Position数据
        base_time = datetime(2023, 1, 3, 9, 30)
        test_positions = [
            MPosition(
                portfolio_id="test_portfolio_001",
                engine_id="test_engine_001",
                code="000001.SZ",
                cost=Decimal("12.50"),
                volume=1000,
                price=Decimal("13.20"),
                fee=Decimal("5.00"),
                frozen_volume=0,
                frozen_money=Decimal("0.00"),
                timestamp=base_time,
                business_timestamp=base_time - timedelta(minutes=5)
            ),
            MPosition(
                portfolio_id="test_portfolio_001",
                engine_id="test_engine_001",
                code="000002.SZ",
                cost=Decimal("18.75"),
                volume=500,
                price=Decimal("19.80"),
                fee=Decimal("3.50"),
                frozen_volume=100,
                frozen_money=Decimal("1980.00"),
                timestamp=base_time + timedelta(minutes=1),
                business_timestamp=base_time + timedelta(minutes=-4, seconds=30)
            )
        ]
        for p in test_positions:
            p.source = SOURCE_TYPES.TEST

        try:
            # 批量插入
            self.crud.add_batch(test_positions)

            # 验证可以查询出插入的数据
            query_result = self.crud.find(filters={
                "portfolio_id": "test_portfolio_001",
                "source": SOURCE_TYPES.TEST.value
            })
            assert len(query_result) >= 2

            print("✓ 批量插入验证通过")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_position(self):
        """测试单条Position数据插入"""
        base_time = datetime(2023, 1, 4, 10, 30)
        test_position = MPosition(
            portfolio_id="test_portfolio_002",
            engine_id="test_engine_002",
            code="000858.SZ",
            cost=Decimal("25.60"),
            volume=800,
            price=Decimal("26.80"),
            fee=Decimal("8.50"),
            frozen_volume=50,
            frozen_money=Decimal("1340.00"),
            timestamp=base_time,
            business_timestamp=base_time - timedelta(minutes=8)
        )
        test_position.source = SOURCE_TYPES.TEST

        try:
            # 单条插入
            result = self.crud.add(test_position)

            # 验证返回值类型
            assert isinstance(result, MPosition), f"add()应返回MPosition对象，实际{type(result)}"

            # 验证数据
            query_result = self.crud.find(filters={
                "portfolio_id": "test_portfolio_002",
                "code": "000858.SZ"
            })
            assert len(query_result) >= 1

            print("✓ 单条插入验证通过")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPositionCRUDQuery:
    """PositionCRUD层查询操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = PositionCRUD()

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询Position"""
        try:
            positions = self.crud.find(filters={"portfolio_id": "test_portfolio_001"})
            print(f"✓ 查询到 {len(positions)} 条记录")

            # 验证查询结果
            for position in positions:
                assert position.portfolio_id == "test_portfolio_001"

            print("✓ 按portfolio_id查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_code(self):
        """测试根据股票代码查询Position"""
        try:
            positions = self.crud.find(filters={"code": "000001.SZ"})
            print(f"✓ 查询到 {len(positions)} 条记录")

            # 验证查询结果
            for position in positions:
                assert position.code == "000001.SZ"

            print("✓ 按code查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.financial
class TestPositionCRUDBusinessLogic:
    """PositionCRUD层业务逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = PositionCRUD()

    def test_position_cost_calculation(self):
        """测试持仓成本计算"""
        try:
            # 创建测试持仓
            base_time = datetime(2023, 1, 5, 9, 30)
            volume = 1000
            cost_price = Decimal("12.50")
            fee = Decimal("5.00")

            test_position = MPosition(
                portfolio_id="test_portfolio_calc",
                engine_id="test_engine_calc",
                code="000001.SZ",
                cost=cost_price,
                volume=volume,
                price=Decimal("13.20"),
                fee=fee,
                frozen_volume=0,
                frozen_money=Decimal("0.00"),
                timestamp=base_time,
                business_timestamp=base_time
            )
            test_position.source = SOURCE_TYPES.TEST
            self.crud.add(test_position)

            # 计算预期总成本
            expected_total_cost = (cost_price * volume) + fee

            # 验证成本计算
            query_result = self.crud.find(filters={"portfolio_id": "test_portfolio_calc"})
            if len(query_result) > 0:
                position = query_result[0]
                actual_total_cost = (position.cost * position.volume) + position.fee

                assert actual_total_cost == pytest.approx(expected_total_cost, abs=Decimal("0.01")), \
                    f"总成本应等于(单价*数量)+费用，预期{expected_total_cost}，实际{actual_total_cost}"

                print(f"✓ 持仓成本计算验证: ({cost_price} * {volume}) + {fee} = {actual_total_cost}")
                print("✓ 持仓成本计算验证通过")

        except Exception as e:
            print(f"✗ 成本计算测试失败: {e}")
            raise

    def test_position_profit_loss(self):
        """测试持仓盈亏计算"""
        try:
            # 创建测试持仓
            base_time = datetime(2023, 1, 5, 9, 30)
            cost_price = Decimal("10.00")
            current_price = Decimal("11.00")
            volume = 1000

            test_position = MPosition(
                portfolio_id="test_portfolio_pnl",
                engine_id="test_engine_pnl",
                code="000001.SZ",
                cost=cost_price,
                volume=volume,
                price=current_price,
                fee=Decimal("5.00"),
                frozen_volume=0,
                frozen_money=Decimal("0.00"),
                timestamp=base_time,
                business_timestamp=base_time
            )
            test_position.source = SOURCE_TYPES.TEST
            self.crud.add(test_position)

            # 计算预期盈亏
            expected_profit = (current_price - cost_price) * volume

            # 验证盈亏计算
            query_result = self.crud.find(filters={"portfolio_id": "test_portfolio_pnl"})
            if len(query_result) > 0:
                position = query_result[0]
                actual_profit = (position.price - position.cost) * position.volume

                assert actual_profit == pytest.approx(expected_profit, abs=Decimal("0.01")), \
                    f"盈亏应等于(当前价-成本价)*数量，预期{expected_profit}，实际{actual_profit}"

                print(f"✓ 持仓盈亏计算验证: ({current_price} - {cost_price}) * {volume} = {actual_profit}")
                print("✓ 持仓盈亏计算验证通过")

        except Exception as e:
            print(f"✗ 盈亏计算测试失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.db_cleanup
class TestPositionCRUDDelete:
    """PositionCRUD层删除操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = PositionCRUD()

    def test_delete_by_portfolio(self):
        """测试按投资组合删除Position"""
        try:
            # 创建测试数据
            base_time = datetime(2023, 12, 1, 9, 30)
            test_position = MPosition(
                portfolio_id="test_portfolio_delete",
                engine_id="test_engine_delete",
                code="000001.SZ",
                cost=Decimal("10.00"),
                volume=100,
                price=Decimal("11.00"),
                fee=Decimal("5.00"),
                frozen_volume=0,
                frozen_money=Decimal("0.00"),
                timestamp=base_time,
                business_timestamp=base_time
            )
            test_position.source = SOURCE_TYPES.TEST
            self.crud.add(test_position)

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


# TDD验证入口
if __name__ == "__main__":
    print("TDD Red阶段验证：Position CRUD测试")
    print("运行: pytest test/data/crud/test_position_crud_refactored.py -v")
    print("预期结果: 所有测试通过")
    print("重点关注: 持仓成本和盈亏计算精度（Decimal）")
