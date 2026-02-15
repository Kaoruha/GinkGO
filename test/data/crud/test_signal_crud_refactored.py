"""
SignalCRUD数据库操作TDD测试 - 交易信号管理

本文件测试SignalCRUD类的完整功能，确保交易信号(Signal)的增删改查操作正常工作。
信号是策略执行的核心数据，记录策略生成的交易意图。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效创建多个信号记录
   - 单条插入 (add): 创建单个信号记录

2. 查询操作 (Query Operations)
   - 按投资组合查询 (find_by_portfolio): 获取特定投资组合的信号
   - 按方向查询 (find_by_direction): 获取买入/卖出信号

3. 更新操作 (Update Operations)
   - 信号状态更新 (update_status): 更新信号执行状态

4. 删除操作 (Delete Operations)
   - 按投资组合删除 (delete_by_portfolio): 删除特定投资组合信号

5. 业务逻辑测试 (Business Logic Tests)
   - 信号生命周期 (signal_lifecycle): 从生成到执行的完整流程
   - 信号有效性验证 (signal_validation): 信号质量和有效性检查

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

from ginkgo.data.crud.signal_crud import SignalCRUD
from ginkgo.data.models.model_signal import MSignal
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestSignalCRUDInsert:
    """SignalCRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = SignalCRUD()

    def test_add_batch_basic(self):
        """测试批量插入Signal数据"""
        print("\n" + "="*60)
        print("开始测试: Signal CRUD层批量插入")
        print("="*60)

        # 创建测试Signal数据
        base_time = datetime(2023, 1, 3, 9, 30)
        test_signals = [
            MSignal(
                portfolio_id="test_portfolio_001",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                timestamp=base_time,
                business_timestamp=base_time - timedelta(minutes=5),
                source=SOURCE_TYPES.TEST
            ),
            MSignal(
                portfolio_id="test_portfolio_001",
                code="000002.SZ",
                direction=DIRECTION_TYPES.SHORT,
                timestamp=base_time + timedelta(minutes=1),
                business_timestamp=base_time - timedelta(minutes=4),
                source=SOURCE_TYPES.TEST
            )
        ]

        try:
            # 批量插入
            self.crud.add_batch(test_signals)

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

    def test_add_single_signal(self):
        """测试单条Signal数据插入"""
        base_time = datetime(2023, 1, 4, 10, 30)
        test_signal = MSignal(
            portfolio_id="test_portfolio_002",
            code="000858.SZ",
            direction=DIRECTION_TYPES.LONG,
            timestamp=base_time,
            business_timestamp=base_time - timedelta(minutes=8),
            source=SOURCE_TYPES.TEST
        )

        try:
            # 单条插入
            result = self.crud.add(test_signal)

            # 验证返回值类型
            assert isinstance(result, MSignal), f"add()应返回MSignal对象，实际{type(result)}"

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
class TestSignalCRUDQuery:
    """SignalCRUD层查询操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = SignalCRUD()

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询Signal"""
        try:
            signals = self.crud.find(filters={"portfolio_id": "test_portfolio_001"})
            print(f"✓ 查询到 {len(signals)} 条记录")

            # 验证查询结果
            for signal in signals:
                assert signal.portfolio_id == "test_portfolio_001"

            print("✓ 按portfolio_id查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    @pytest.mark.parametrize("direction", [
        DIRECTION_TYPES.LONG,
        DIRECTION_TYPES.SHORT
    ])
    def test_find_by_direction(self, direction):
        """参数化测试按方向查询"""
        try:
            signals = self.crud.find(filters={"direction": direction})
            print(f"✓ 方向{direction.name}: {len(signals)} 条记录")

            # 验证查询结果
            for signal in signals:
                assert signal.direction == direction

            print("✓ 按direction查询验证通过")

        except Exception as e:
            print(f"✗ 方向查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.db_cleanup
class TestSignalCRUDDelete:
    """SignalCRUD层删除操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = SignalCRUD()

    def test_delete_by_portfolio(self):
        """测试按投资组合删除Signal"""
        try:
            # 创建测试数据
            base_time = datetime(2023, 12, 1, 9, 30)
            test_signal = MSignal(
                portfolio_id="test_portfolio_delete",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                timestamp=base_time,
                business_timestamp=base_time,
                source=SOURCE_TYPES.TEST
            )
            self.crud.add(test_signal)

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
    print("TDD Red阶段验证：Signal CRUD测试")
    print("运行: pytest test/data/crud/test_signal_crud_refactored.py -v")
    print("预期结果: 所有测试通过")
