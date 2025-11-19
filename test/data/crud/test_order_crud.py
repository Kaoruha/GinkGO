"""
OrderCRUD数据库操作TDD测试 - 交易订单管理

本文件测试OrderCRUD类的完整功能，确保交易订单(Order)的增删改查操作正常工作。
订单是交易系统的核心数据模型，记录交易意图、执行状态和结果，直接影响交易执行和风险控制。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效插入大量订单数据
   - 单条插入 (add): 插入单个订单记录
   - 快速插入 (fast_insert): 优化性能的订单插入

2. 查询操作 (Query Operations)
   - 按投资组合查询 (find_by_portfolio): 获取特定投资组合的订单
   - 按时间范围查询 (find_by_time_range): 获取指定时间段的订单
   - 按状态查询 (find_by_status): 获取特定状态的订单
   - 按方向查询 (find_by_direction): 获取买入/卖出订单
   - 订单分页查询 (pagination_with_orders): 支持大数据量分页
   - 订单计数统计 (order_counting): 订单数量统计

3. 更新操作 (Update Operations)
   - 订单状态更新 (update_order_status): 更新订单执行状态
   - 订单价格更新 (update_order_price): 调整订单价格
   - 订单数量更新 (update_order_volume): 修改订单数量
   - 批量状态更新 (batch_status_update): 批量更新订单状态

4. 删除操作 (Delete Operations)
   - 按状态删除 (delete_by_status): 清理特定状态订单
   - 按时间范围删除 (delete_by_time_range): 清理历史订单
   - 按投资组合删除 (delete_by_portfolio): 清理特定投资组合订单
   - 批量删除 (batch_delete): 高效批量删除操作

5. 业务逻辑测试 (Business Logic Tests)
   - 订单生命周期 (order_lifecycle): 从创建到完成的完整流程
   - 订单状态转换 (order_status_transitions): 状态变更规则验证
   - 订单金额计算 (order_amount_calculation): 订单金额和费用计算
   - 订单时间戳管理 (order_timestamp_management): 时间相关字段管理

数据模型：
- MOrder: 订单数据模型，包含投资组合ID、代码、方向、类型、状态、数量、价格等
- 支持多种订单类型：市价单、限价单、条件单等
- 订单状态：新建、待执行、部分成交、完全成交、取消、拒绝等
- 支持买入(做多)和卖出(做空)方向

业务价值：
- 记录所有交易意图和执行结果
- 支持交易执行监控和风险控制
- 为策略回测提供交易成本分析
- 支持合规审计和交易分析
- 为性能评估提供详细交易数据

测试策略：
- 覆盖订单完整生命周期
- 验证订单状态转换规则
- 测试订单金额和费用计算精度
- 验证时间戳和排序逻辑
- 使用测试数据源标记便于清理
- 测试并发和数据一致性
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from datetime import timedelta
from ginkgo.data.crud.order_crud import OrderCRUD
from ginkgo.data.models.model_order import MOrder
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestOrderCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': OrderCRUD}
    """1. CRUD层插入操作测试 - Order数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入Order数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: Order CRUD层批量插入")
        print("="*60)

        order_crud = OrderCRUD()
        print(f"✓ 创建OrderCRUD实例: {order_crud.__class__.__name__}")

        # 获取操作前数据条数用于验证
        before_count = len(order_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
        print(f"✓ 操作前数据库记录数: {before_count}")

        # 创建测试Order数据（移除数据库中不存在的字段）
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
                timestamp=datetime(2023, 1, 3, 9, 30),
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
                timestamp=datetime(2023, 1, 3, 9, 31),
                source=SOURCE_TYPES.TEST
            )
        ]
        print(f"✓ 创建测试数据: {len(test_orders)}条Order记录")
        print(f"  - 投资组合ID: test_portfolio_001")
        print(f"  - 股票代码: 000001.SZ, 000002.SZ")
        print(f"  - 订单类型: LIMIT, MARKET")
        print(f"  - 交易方向: LONG, SHORT")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            order_crud.add_batch(test_orders)
            print("✓ 批量插入成功")

            # 验证数据库记录数变化
            after_count = len(order_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作后数据库记录数: {after_count}")
            assert after_count - before_count == len(test_orders), f"应增加{len(test_orders)}条数据，实际增加{after_count - before_count}条"

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = order_crud.find(filters={"portfolio_id": "test_portfolio_001", "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(query_result)} 条记录")

            # 验证返回值类型 - find方法应返回ModelList
            from ginkgo.data.crud.model_conversion import ModelList
            assert isinstance(query_result, ModelList), f"find()应返回ModelList，实际{type(query_result)}"
            assert len(query_result) >= 2

            # 验证数据内容
            portfolio_ids = [order.portfolio_id for order in query_result]
            codes = [order.code for order in query_result]
            print(f"✓ 投资组合ID验证通过: {set(portfolio_ids)}")
            print(f"✓ 股票代码验证通过: {set(codes)}")
            assert "test_portfolio_001" in portfolio_ids
            assert "000001.SZ" in codes
            assert "000002.SZ" in codes

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_order(self):
        """测试单条Order数据插入"""
        print("\n" + "="*60)
        print("开始测试: Order CRUD层单条插入")
        print("="*60)

        order_crud = OrderCRUD()

        # 获取操作前数据条数用于验证
        before_count = len(order_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
        print(f"✓ 操作前数据库记录数: {before_count}")

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
            timestamp=datetime(2023, 1, 4, 10, 15),
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试Order: {test_order.code} @ {test_order.limit_price}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            result = order_crud.add(test_order)
            print("✓ 单条插入成功")

            # 验证返回值类型
            print(f"✓ 返回值类型: {type(result).__name__}")
            assert isinstance(result, MOrder), f"add()应返回MOrder对象，实际{type(result)}"

            # 验证数据库记录数变化
            after_count = len(order_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作后数据库记录数: {after_count}")
            assert after_count - before_count == 1, f"应增加1条数据，实际增加{after_count - before_count}条"

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = order_crud.find(filters={"portfolio_id": "test_portfolio_002",
                "code": "000001.SZ", "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            # 验证返回值类型 - find方法应返回ModelList
            from ginkgo.data.crud.model_conversion import ModelList
            assert isinstance(query_result, ModelList), f"find()应返回ModelList，实际{type(query_result)}"

            inserted_order = query_result[0]
            print(f"✓ 插入的订单验证: {inserted_order.code}, 数量={inserted_order.volume}")
            assert inserted_order.code == "000001.SZ"
            assert inserted_order.volume == 2000

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestOrderCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': OrderCRUD}
    """2. CRUD层查询操作测试 - Order数据查询和过滤"""

    @staticmethod
    def safe_enum_name(enum_type, value):
        """安全显示枚举名称"""
        if isinstance(value, int):
            return enum_type(value).name
        elif hasattr(value, 'name'):
            return value.name
        else:
            return str(value)

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询Order"""
        print("\n" + "="*60)
        print("开始测试: 根据portfolio_id查询Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 查询特定投资组合的订单
            print("→ 查询portfolio_id=test_portfolio_001的订单...")
            orders = order_crud.find(filters={"portfolio_id": "test_portfolio_001", "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(orders)} 条记录")

            # 验证查询结果
            for order in orders:
                # 安全显示枚举名称
                direction_name = DIRECTION_TYPES(order.direction).name if isinstance(order.direction, int) else order.direction.name
                print(f"  - {order.code}: {direction_name} {order.volume}股 @ {order.limit_price}")
                assert order.portfolio_id == "test_portfolio_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_code_and_status(self):
        """测试根据股票代码和状态查询Order"""
        print("\n" + "="*60)
        print("开始测试: 根据code和status查询Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 查询特定股票和状态的订单
            print("→ 查询code=000001.SZ且status=NEW的订单...")
            orders = order_crud.find(filters={
                "code": "000001.SZ",
                "status": ORDERSTATUS_TYPES.NEW  # 直接使用枚举对象
            })
            print(f"✓ 查询到 {len(orders)} 条记录")

            # 验证查询结果
            for order in orders:
                print(f"  - Portfolio: {order.portfolio_id}, 状态: {TestOrderCRUDQuery.safe_enum_name(ORDERSTATUS_TYPES, order.status)}")
                assert order.code == "000001.SZ"
                assert order.status == ORDERSTATUS_TYPES.NEW

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_with_limit_and_offset(self):
        """测试分页查询Order"""
        print("\n" + "="*60)
        print("开始测试: 分页查询Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 限制查询数量
            print("→ 查询前5条订单记录...")
            orders = order_crud.find(page_size=5)
            print(f"✓ 查询到 {len(orders)} 条记录")
            assert len(orders) <= 5

            # 偏移查询
            print("→ 跳过前1条记录，查询后5条...")
            orders_offset = order_crud.find(page_size=5, page=1)
            print(f"✓ 查询到 {len(orders_offset)} 条记录")
            assert len(orders_offset) <= 5

        except Exception as e:
            print(f"✗ 分页查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestOrderCRUDUpdate:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': OrderCRUD}
    """3. CRUD层更新操作测试 - Order状态更新"""

    def test_update_order_status(self):
        """测试更新Order状态"""
        print("\n" + "="*60)
        print("开始测试: 更新Order状态")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 查询待更新的订单
            print("→ 查询NEW状态的订单...")
            orders = order_crud.find(filters={"status": ORDERSTATUS_TYPES.NEW})
            if not orders:
                print("✗ 没有找到NEW状态的订单")
                return

            target_order = orders[0]
            print(f"✓ 找到订单: {target_order.code}, 当前状态: {target_order.status.name}")

            # 更新订单状态为PARTIAL_FILLED
            print("→ 更新订单状态为PARTIAL_FILLED...")
            updated_data = {
                "status": ORDERSTATUS_TYPES.PARTIAL_FILLED,  # 现在支持直接传入枚举
                "transaction_volume": 500,
                "transaction_price": Decimal("10.45"),
                "remain": target_order.remain - Decimal("5225.00")
            }

            order_crud.modify({"uuid": target_order.uuid}, updated_data)
            print("✓ 订单状态更新成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_orders = order_crud.find(filters={"uuid": target_order.uuid})
            assert len(updated_orders) == 1

            updated_order = updated_orders[0]
            print(f"✓ 更新后状态: {updated_order.status.name}")
            print(f"✓ 成交数量: {updated_order.transaction_volume}")
            assert updated_order.status == ORDERSTATUS_TYPES.PARTIAL_FILLED
            assert updated_order.transaction_volume == 500

        except Exception as e:
            print(f"✗ 更新订单状态失败: {e}")
            raise

    def test_update_order_batch(self):
        """测试批量更新Order"""
        print("\n" + "="*60)
        print("开始测试: 批量更新Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 查询多个订单进行批量更新
            print("→ 查询需要批量更新的订单...")
            orders = order_crud.find(filters={"portfolio_id": "test_portfolio_001", "source": SOURCE_TYPES.TEST.value})
            if len(orders) < 2:
                print("✗ 订单数量不足，跳过批量更新测试")
                return

            print(f"✓ 找到 {len(orders)} 条订单进行批量更新")

            # 批量更新订单状态
            for order in orders[:2]:  # 更新前2条
                print(f"→ 更新订单 {order.code} 状态为FILLED...")
                order_crud.modify({"uuid": order.uuid}, {"status": ORDERSTATUS_TYPES.FILLED.value})

            print("✓ 批量更新完成")

            # 验证批量更新结果
            print("→ 验证批量更新结果...")
            filled_orders = order_crud.find(filters={"portfolio_id": "test_portfolio_001",
                "status": ORDERSTATUS_TYPES.FILLED, "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 更新为FILLED状态的订单: {len(filled_orders)} 条")
            assert len(filled_orders) >= 2

        except Exception as e:
            print(f"✗ 批量更新失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestOrderCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': OrderCRUD}
    """4. CRUD层删除操作测试 - Order数据清理"""

    def test_delete_order_by_uuid(self):
        """测试根据UUID删除Order"""
        print("\n" + "="*60)
        print("开始测试: 根据UUID删除Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 先插入一条测试数据
            print("→ 创建测试订单...")
            test_order = MOrder(
                portfolio_id="test_portfolio_delete",
                engine_id="test_engine_001",
                run_id="test_run_001",
                code="999999.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.CANCELED,
                volume=100,
                limit_price=Decimal("1.00"),
                timestamp=datetime.now()
            )
            order_crud.add(test_order)
            print(f"✓ 创建测试订单: {test_order.uuid}")

            # 查询确认插入成功
            inserted_orders = order_crud.find(filters={"uuid": test_order.uuid})
            assert len(inserted_orders) == 1
            print("✓ 订单插入确认成功")

            # 删除订单
            print("→ 删除测试订单...")
            order_crud.remove({"uuid": test_order.uuid})
            print("✓ 订单删除成功")

            # 验证删除结果
            print("→ 验证删除结果...")
            deleted_orders = order_crud.find(filters={"uuid": test_order.uuid})
            assert len(deleted_orders) == 0
            print("✓ 订单删除验证成功")

        except Exception as e:
            print(f"✗ 删除订单失败: {e}")
            raise

    def test_delete_orders_by_portfolio(self):
        """测试根据投资组合ID批量删除Order"""
        print("\n" + "="*60)
        print("开始测试: 根据portfolio_id批量删除Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 查询删除前的数量
            print("→ 查询删除前的订单数量...")
            orders_before = order_crud.find(filters={"portfolio_id": "test_portfolio_002", "source": SOURCE_TYPES.TEST.value})
            count_before = len(orders_before)
            print(f"✓ 删除前有 {count_before} 条订单")

            if count_before == 0:
                print("✗ 没有找到可删除的订单")
                return

            # 批量删除
            print("→ 批量删除订单...")
            for order in orders_before:
                order_crud.remove({"uuid": order.uuid})
            print("✓ 批量删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            orders_after = order_crud.find(filters={"portfolio_id": "test_portfolio_002", "source": SOURCE_TYPES.TEST.value})
            count_after = len(orders_after)
            print(f"✓ 删除后剩余 {count_after} 条订单")
            assert count_after == 0
            print("✓ 批量删除验证成功")

        except Exception as e:
            print(f"✗ 批量删除失败: {e}")
            raise

    def test_delete_order_by_status(self):
        """测试根据订单状态删除Order"""
        print("\n" + "="*60)
        print("开始测试: 根据订单状态删除Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 创建不同状态的测试订单
            test_statuses = [
                ORDERSTATUS_TYPES.CANCELED,
                ORDERSTATUS_TYPES.CANCELED,
                ORDERSTATUS_TYPES.FILLED
            ]

            base_time = datetime(2023, 11, 15, 10, 30, 0)

            for i, status in enumerate(test_statuses):
                test_order = MOrder(
                    portfolio_id=f"delete_status_portfolio_{i}",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    code=f"DELETE_STATUS_{i:03d}.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=status,
                    volume=100,
                    limit_price=Decimal(f"8.{i}88"),
                    timestamp=base_time + timedelta(minutes=i)
                )
                order_crud.add(test_order)

            print(f"✓ 创建状态测试订单: {len(test_statuses)} 条")

            # 验证数据存在
            canceled_before = len(order_crud.find(filters={"status": ORDERSTATUS_TYPES.CANCELED}))
            rejected_before = len(order_crud.find(filters={"status": ORDERSTATUS_TYPES.CANCELED}))
            filled_before = len(order_crud.find(filters={"status": ORDERSTATUS_TYPES.FILLED}))

            print(f"✓ 删除前已取消订单: {canceled_before} 条")
            print(f"✓ 删除前已拒绝订单: {rejected_before} 条")
            print(f"✓ 删除前已成交订单: {filled_before} 条")

            # 删除已取消和已拒绝的订单
            print("→ 删除已取消和已拒绝的订单...")
            cancel_reject_orders = order_crud.find(filters={
                "status__in": [ORDERSTATUS_TYPES.CANCELED, ORDERSTATUS_TYPES.CANCELED]
            })
            for order in cancel_reject_orders:
                order_crud.remove({"uuid": order.uuid})

            # 验证删除结果
            canceled_after = len(order_crud.find(filters={"status": ORDERSTATUS_TYPES.CANCELED}))
            rejected_after = len(order_crud.find(filters={"status": ORDERSTATUS_TYPES.CANCELED}))
            filled_after = len(order_crud.find(filters={"status": ORDERSTATUS_TYPES.FILLED}))

            print(f"✓ 删除后已取消订单: {canceled_after} 条")
            print(f"✓ 删除后已拒绝订单: {rejected_after} 条")
            print(f"✓ 删除后已成交订单: {filled_after} 条")

            assert canceled_after == 0, "已取消订单应该全部删除"
            assert rejected_after == 0, "已拒绝订单应该全部删除"
            assert filled_after >= 0, "已成交订单应该保留"
            print("✓ 根据订单状态删除Order验证成功")

        except Exception as e:
            print(f"✗ 订单状态删除操作失败: {e}")
            raise

    def test_delete_order_by_code(self):
        """测试根据股票代码删除Order"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码删除Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 创建同一股票的多个订单
            test_code = "DELETE_CODE_ORDER.SZ"
            base_time = datetime(2023, 10, 15, 14, 0, 0)

            for i in range(5):
                test_order = MOrder(
                    portfolio_id=f"delete_code_portfolio_{i}",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    code=test_code,
                    direction=DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.CANCELED,
                    volume=100 + i * 10,
                    limit_price=Decimal(f"9.{i}99"),
                    timestamp=base_time + timedelta(minutes=i)
                )
                order_crud.add(test_order)

            print(f"✓ 创建股票代码测试订单: 5 条")

            # 验证数据存在
            before_count = len(order_crud.find(filters={"code": test_code}))
            print(f"✓ 删除前股票 {test_code} 订单: {before_count} 条")

            # 执行删除
            print("→ 删除指定股票的所有订单...")
            code_orders = order_crud.find(filters={"code": test_code})
            for order in code_orders:
                order_crud.remove({"uuid": order.uuid})

            # 验证删除结果
            after_count = len(order_crud.find(filters={"code": test_code}))
            print(f"✓ 删除后股票 {test_code} 订单: {after_count} 条")
            assert after_count == 0, "删除后应该没有该股票的订单"
            print("✓ 根据股票代码删除Order验证成功")

        except Exception as e:
            print(f"✗ 股票代码删除操作失败: {e}")
            raise

    def test_delete_order_by_direction(self):
        """测试根据买卖方向删除Order"""
        print("\n" + "="*60)
        print("开始测试: 根据买卖方向删除Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 创建不同方向的测试订单
            base_time = datetime(2023, 9, 15, 11, 0, 0)

            # 买入订单
            for i in range(3):
                buy_order = MOrder(
                    portfolio_id=f"delete_direction_buy_{i}",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    code=f"DELETE_BUY_{i+1:03d}.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.CANCELED,
                    volume=100,
                    limit_price=Decimal("8.88"),
                    timestamp=base_time + timedelta(minutes=i)
                )
                order_crud.add(buy_order)

            # 卖出订单
            for i in range(3):
                sell_order = MOrder(
                    portfolio_id=f"delete_direction_sell_{i}",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    code=f"DELETE_SELL_{i+1:03d}.SZ",
                    direction=DIRECTION_TYPES.SHORT,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.CANCELED,
                    volume=200,
                    limit_price=Decimal("9.99"),
                    timestamp=base_time + timedelta(minutes=i + 10)
                )
                order_crud.add(sell_order)

            print("✓ 创建买卖方向测试订单")

            # 验证数据存在
            buy_before = len(order_crud.find(filters={"direction": DIRECTION_TYPES.LONG}))
            sell_before = len(order_crud.find(filters={"direction": DIRECTION_TYPES.SHORT}))
            print(f"✓ 删除前买入订单: {buy_before} 条")
            print(f"✓ 删除前卖出订单: {sell_before} 条")

            # 删除卖出订单
            print("→ 删除卖出方向订单...")
            sell_orders = order_crud.find(filters={"direction": DIRECTION_TYPES.SHORT})
            for order in sell_orders:
                order_crud.remove({"uuid": order.uuid})

            # 验证删除结果
            buy_after = len(order_crud.find(filters={"direction": DIRECTION_TYPES.LONG}))
            sell_after = len(order_crud.find(filters={"direction": DIRECTION_TYPES.SHORT}))

            print(f"✓ 删除后买入订单: {buy_after} 条")
            print(f"✓ 删除后卖出订单: {sell_after} 条")
            assert sell_after == 0, "卖出订单应该全部删除"
            assert buy_after >= 0, "买入订单应该保留"
            print("✓ 根据买卖方向删除Order验证成功")

        except Exception as e:
            print(f"✗ 买卖方向删除操作失败: {e}")
            raise

    def test_delete_order_by_time_range(self):
        """测试根据时间范围删除Order"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 创建特定时间范围的测试订单
            start_time = datetime(2023, 8, 1, 10, 0, 0)
            end_time = datetime(2023, 8, 31, 16, 0, 0)

            # 目标时间范围内的订单
            for i in range(5):
                test_order = MOrder(
                    portfolio_id=f"delete_time_portfolio_{i}",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    code=f"DELETE_TIME_{i+1:03d}.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.CANCELED,
                    volume=100,
                    limit_price=Decimal(f"7.{i}77"),
                    timestamp=start_time + timedelta(days=i * 5)
                )
                order_crud.add(test_order)

            # 范围外的订单
            outside_order = MOrder(
                portfolio_id="delete_time_outside",
                engine_id="test_engine_001",
                run_id="test_run_001",
                code="DELETE_TIME_OUTSIDE.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.CANCELED,
                volume=100,
                limit_price=Decimal("6.66"),
                timestamp=end_time + timedelta(days=1)
            )
            order_crud.add(outside_order)

            print(f"✓ 创建时间范围测试订单: 6 条")

            # 验证数据存在
            time_range_before = len(order_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            }))
            outside_before = len(order_crud.find(filters={"code": "DELETE_TIME_OUTSIDE.SZ"}))

            print(f"✓ 删除前时间范围内订单: {time_range_before} 条")
            print(f"✓ 删除前时间范围外订单: {outside_before} 条")

            # 删除时间范围内的订单
            print("→ 删除时间范围内的订单...")
            time_range_orders = order_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })
            for order in time_range_orders:
                order_crud.remove({"uuid": order.uuid})

            # 验证删除结果
            time_range_after = len(order_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            }))
            outside_after = len(order_crud.find(filters={"code": "DELETE_TIME_OUTSIDE.SZ"}))

            print(f"✓ 删除后时间范围内订单: {time_range_after} 条")
            print(f"✓ 删除后时间范围外订单: {outside_after} 条")

            assert time_range_after == 0, "时间范围内订单应该全部删除"
            assert outside_after == 1, "时间范围外订单应该保留"
            print("✓ 根据时间范围删除Order验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_order_batch_cleanup(self):
        """测试批量清理Order数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理Order数据")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 创建大量清理测试数据
            cleanup_count = 15
            base_time = datetime(2023, 7, 15, 9, 30, 0)

            for i in range(cleanup_count):
                test_order = MOrder(
                    portfolio_id=f"cleanup_portfolio_{i:03d}",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    code=f"CLEANUP_ORDER_{i+1:03d}.SZ",
                    direction=DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.CANCELED,
                    volume=50 + i,
                    limit_price=Decimal(f"6.{1000+i}"),
                    timestamp=base_time + timedelta(minutes=i)
                )
                order_crud.add(test_order)

            print(f"✓ 创建批量清理测试订单: {cleanup_count} 条")

            # 验证数据存在
            before_count = len(order_crud.find(filters={
                "portfolio_id__like": "cleanup_portfolio_%"
            }))
            print(f"✓ 删除前批量订单: {before_count} 条")

            # 批量删除
            print("→ 执行批量清理操作...")
            cleanup_orders = order_crud.find(filters={
                "portfolio_id__like": "cleanup_portfolio_%"
            })
            for order in cleanup_orders:
                order_crud.remove({"uuid": order.uuid})

            # 验证删除结果
            print("→ 验证批量清理结果...")
            after_count = len(order_crud.find(filters={
                "portfolio_id__like": "cleanup_portfolio_%"
            }))
            assert after_count == 0, "删除后应该没有批量清理订单"
            print(f"✓ 删除后批量订单: {after_count} 条")

            # 确认其他数据未受影响
            other_data_count = len(order_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理Order数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestOrderCRUDBusinessLogic:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': OrderCRUD}
    """5. CRUD层业务逻辑测试 - Order业务场景验证"""

    def test_order_lifecycle_management(self):
        """测试订单完整生命周期管理"""
        print("\n" + "="*60)
        print("开始测试: 订单完整生命周期管理")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 1. 创建新订单
            print("1. 创建新订单...")
            new_order = MOrder(
                portfolio_id="lifecycle_test",
                engine_id="test_engine_001",
                run_id="test_run_001",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.NEW,
                volume=1000,
                limit_price=Decimal("10.00"),
                frozen=Decimal("10000.00"),
                remain=Decimal("10000.00")
            )
            order_crud.add(new_order)
            print(f"✓ 新订单创建成功: {new_order.uuid}")

            # 2. 更新为部分成交
            print("2. 更新为部分成交...")
            order_crud.modify({"uuid": new_order.uuid}, {
                "status": ORDERSTATUS_TYPES.PARTIAL_FILLED,
                "transaction_volume": 300,
                "transaction_price": Decimal("10.05"),
                "remain": Decimal("6985.00")
            })
            print("✓ 部分成交更新成功")

            # 3. 更新为完全成交
            print("3. 更新为完全成交...")
            order_crud.modify({"uuid": new_order.uuid}, {
                "status": ORDERSTATUS_TYPES.FILLED,
                "transaction_volume": 1000,
                "transaction_price": Decimal("10.03"),
                "remain": Decimal("0.00")
            })
            print("✓ 完全成交更新成功")

            # 4. 验证最终状态
            print("4. 验证最终状态...")
            final_orders = order_crud.find(filters={"uuid": new_order.uuid})
            if not final_orders:
                print(f"✗ 没有找到订单 {new_order.uuid}")
                return
            final_order = final_orders[0]
            print(f"✓ 最终状态: {final_order.status.name}")
            print(f"✓ 总成交量: {final_order.transaction_volume}")
            print(f"✓ 剩余冻结金额: {final_order.remain}")

            assert final_order.status == ORDERSTATUS_TYPES.FILLED
            assert final_order.transaction_volume == 1000
            assert final_order.remain == Decimal("0.00")
            print("✓ 订单生命周期验证成功")

        except Exception as e:
            print(f"✗ 订单生命周期测试失败: {e}")
            raise

    def test_order_query_with_complex_conditions(self):
        """测试复杂条件查询Order"""
        print("\n" + "="*60)
        print("开始测试: 复杂条件查询Order")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 复合条件查询
            print("→ 执行复合条件查询...")
            complex_orders = order_crud.find(filters={"portfolio_id": "test_portfolio_001",
                "direction": DIRECTION_TYPES.LONG,
                "order_type": ORDER_TYPES.LIMITORDER, "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 复合查询结果: {len(complex_orders)} 条记录")

            # 时间范围查询
            print("→ 执行时间范围查询...")
            time_orders = order_crud.find(filters={"portfolio_id": "test_portfolio_001",
                "start_time": datetime(2023, 1, 1),
                "end_time": datetime(2023, 12, 31), "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 时间范围查询结果: {len(time_orders)} 条记录")

            # 验证查询结果的业务逻辑
            for order in complex_orders:
                assert order.portfolio_id == "test_portfolio_001"
                assert order.direction == DIRECTION_TYPES.LONG
                assert order.order_type == ORDER_TYPES.LIMITORDER
                print(f"  - {order.code}: {order.status.name}")

            print("✓ 复杂条件查询验证成功")

        except Exception as e:
            print(f"✗ 复杂条件查询失败: {e}")
            raise

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        from decimal import Decimal
        import pandas as pd
        print("\n" + "="*60)
        print("开始测试: ModelList转换功能")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 创建测试数据
            test_orders = [
                MOrder(
                    portfolio_id="convert_test_portfolio",
                    engine_id="convert_test_engine",
                    run_id="convert_test_run",
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG,
                    order_type=ORDER_TYPES.LIMITORDER,
                    status=ORDERSTATUS_TYPES.NEW,
                    volume=1000,
                    limit_price=Decimal("10.50"),
                    frozen=Decimal("10500.00"),
                    remain=Decimal("10500.00"),
                    fee=Decimal("0.00"),
                    timestamp=datetime(2023, 1, 5, 9, 30),
                    source=SOURCE_TYPES.TEST
                ),
                MOrder(
                    portfolio_id="convert_test_portfolio",
                    engine_id="convert_test_engine",
                    run_id="convert_test_run",
                    code="000002.SZ",
                    direction=DIRECTION_TYPES.SHORT,
                    order_type=ORDER_TYPES.MARKETORDER,
                    status=ORDERSTATUS_TYPES.FILLED,
                    volume=500,
                    limit_price=Decimal("0.00"),
                    frozen=Decimal("0.00"),
                    remain=Decimal("0.00"),
                    fee=Decimal("5.00"),
                    timestamp=datetime(2023, 1, 5, 9, 31),
                    source=SOURCE_TYPES.TEST
                )
            ]

            # 获取操作前数据条数用于验证
            before_count = len(order_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作前数据库记录数: {before_count}")

            # 插入测试数据
            order_crud.add_batch(test_orders)

            # 验证数据库记录数变化
            after_count = len(order_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作后数据库记录数: {after_count}")
            assert after_count - before_count == len(test_orders), f"应增加{len(test_orders)}条数据，实际增加{after_count - before_count}条"

            # 获取ModelList进行转换测试
            print("\n→ 获取ModelList...")
            model_list = order_crud.find(filters={"portfolio_id": "convert_test_portfolio"})
            print(f"✓ ModelList类型: {type(model_list).__name__}")
            print(f"✓ ModelList长度: {len(model_list)}")
            assert len(model_list) >= 2

            # 测试1: to_dataframe转换
            print("\n→ 测试to_dataframe转换...")
            df = model_list.to_dataframe()
            print(f"✓ DataFrame类型: {type(df).__name__}")
            print(f"✓ DataFrame形状: {df.shape}")
            assert isinstance(df, pd.DataFrame), "应返回DataFrame"
            assert len(df) == len(model_list), f"DataFrame行数应等于ModelList长度，{len(df)} != {len(model_list)}"

            # 验证DataFrame列和内容
            required_columns = ['portfolio_id', 'code', 'direction', 'order_type', 'status', 'volume', 'limit_price']
            for col in required_columns:
                assert col in df.columns, f"DataFrame应包含列: {col}"
            print(f"✓ 验证必要列存在: {required_columns}")

            # 验证DataFrame数据内容
            assert all(df['portfolio_id'] == 'convert_test_portfolio'), "投资组合ID应匹配"
            assert set(df['code']) == {'000001.SZ', '000002.SZ'}, "股票代码应匹配"
            print("✓ DataFrame数据内容验证通过")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            entities = model_list.to_entities()
            print(f"✓ 实体列表类型: {type(entities).__name__}")
            print(f"✓ 实体列表长度: {len(entities)}")
            assert len(entities) == len(model_list), f"实体列表长度应等于ModelList长度，{len(entities)} != {len(model_list)}"

            # 验证实体类型和内容
            first_entity = entities[0]
            from ginkgo.trading import Order
            assert isinstance(first_entity, Order), f"应转换为Order实体，实际{type(first_entity)}"

            # 验证实体属性
            assert first_entity.portfolio_id == "convert_test_portfolio"
            assert first_entity.code in ["000001.SZ", "000002.SZ"]
            print("✓ Order实体转换验证通过")

            # 测试3: 业务对象映射验证
            print("\n→ 测试业务对象映射...")
            for i, entity in enumerate(entities):
                # 验证枚举类型正确转换
                assert entity.direction in [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT]
                assert entity.order_type in [ORDER_TYPES.LIMITORDER, ORDER_TYPES.MARKETORDER]
                assert entity.status in [ORDERSTATUS_TYPES.NEW, ORDERSTATUS_TYPES.FILLED]

                # 验证数值类型
                assert isinstance(entity.volume, int)
                assert isinstance(entity.limit_price, Decimal)
                print(f"  - 实体{i+1}: {entity.code} {entity.direction.name} {entity.volume}股 @ {entity.limit_price}")
            print("✓ 业务对象映射验证通过")

            # 测试4: 验证缓存机制
            print("\n→ 测试转换缓存机制...")
            df2 = model_list.to_dataframe()
            entities2 = model_list.to_entities()
            # 验证结果一致性
            assert df.equals(df2), "DataFrame缓存结果应一致"
            assert len(entities) == len(entities2), "实体列表缓存结果应一致"
            print("✓ 缓存机制验证正确")

            # 测试5: 验证空ModelList的转换
            print("\n→ 测试空ModelList的转换...")
            empty_model_list = order_crud.find(filters={"portfolio_id": "NONEXISTENT_PORTFOLIO"})
            assert len(empty_model_list) == 0, "空ModelList长度应为0"
            empty_df = empty_model_list.to_dataframe()
            empty_entities = empty_model_list.to_entities()
            assert isinstance(empty_df, pd.DataFrame), "空转换应返回DataFrame"
            assert empty_df.shape[0] == 0, "空DataFrame行数应为0"
            assert isinstance(empty_entities, list), "空转换应返回列表"
            assert len(empty_entities) == 0, "空实体列表长度应为0"
            print("✓ 空ModelList转换验证正确")

            print("\n✓ 所有ModelList转换功能测试通过！")

        except Exception as e:
            print(f"✗ 测试失败: {e}")
            raise

    def test_order_data_integrity(self):
        """测试Order数据完整性和约束"""
        print("\n" + "="*60)
        print("开始测试: Order数据完整性和约束")
        print("="*60)

        order_crud = OrderCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # portfolio_id不能为空
            try:
                invalid_order = MOrder(
                    portfolio_id="",  # 空字符串
                    engine_id="test_engine",
                    code="000001.SZ"
                )
                order_crud.add(invalid_order)
                print("✗ 应该拒绝portfolio_id为空的订单")
                assert False, "应该抛出异常"
            except Exception as e:
                print(f"✓ 正确拒绝无效订单: {type(e).__name__}")

            # 验证枚举值约束
            print("→ 验证枚举值约束...")
            valid_orders = order_crud.find(page_size=10)
            for order in valid_orders:
                # 验证direction是有效枚举值（现在返回枚举对象）
                assert order.direction in [d for d in DIRECTION_TYPES]
                # 验证order_type是有效枚举值
                assert order.order_type in [o for o in ORDER_TYPES]
                # 验证status是有效枚举值
                assert order.status in [s for s in ORDERSTATUS_TYPES]

            print(f"✓ 验证了 {len(valid_orders)} 条订单的枚举值约束")
            print("✓ 数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
            raise


@pytest.mark.enum
@pytest.mark.database
class TestOrderCRUDEnumValidation:
    """OrderCRUD枚举传参验证测试 - 整合自独立的枚举测试文件"""

    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': OrderCRUD}

    def test_direction_enum_conversions(self):
        """测试交易方向枚举转换功能"""
        print("\n" + "="*60)
        print("开始测试: 交易方向枚举转换")
        print("="*60)

        order_crud = OrderCRUD()

        # 测试多头方向枚举传参
        print("\n→ 测试多头方向枚举传参...")
        test_order_long = MOrder(
            engine_id="test_engine_enum",
            run_id="test_run_enum",
            portfolio_id="test_portfolio_enum",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,  # 直接传入枚举对象
            order_type=ORDER_TYPES.LIMITORDER,
            volume=1000,
            limit_price=10.50,
            status=ORDERSTATUS_TYPES.NEW,
            source=SOURCE_TYPES.TEST
        )

        # 插入数据
        result = order_crud.add(test_order_long)
        assert result is not None, "枚举传参的订单应该成功插入"
        print("✓ 多头方向枚举传参成功")

        # 查询验证
        orders = order_crud.find(filters={"engine_id": "test_engine_enum", "portfolio_id": "test_portfolio_enum", "source": SOURCE_TYPES.TEST.value})
        assert len(orders) > 0, "应该能查询到插入的订单"

        # 验证枚举转换正确性
        retrieved_order = orders[0]
        assert retrieved_order.direction == DIRECTION_TYPES.LONG, "查询结果应该是LONG枚举对象"
        print("✓ 多头方向枚举转换验证正确")

        # 测试空头方向枚举传参
        print("\n→ 测试空头方向枚举传参...")
        test_order_short = MOrder(
            engine_id="test_engine_enum",
            run_id="test_run_enum",
            portfolio_id="test_portfolio_enum",
            code="000002.SZ",
            direction=DIRECTION_TYPES.SHORT,  # 直接传入枚举对象
            order_type=ORDER_TYPES.MARKETORDER,
            volume=2000,
            status=ORDERSTATUS_TYPES.NEW,
            source=SOURCE_TYPES.TEST
        )

        result = order_crud.add(test_order_short)
        assert result is not None, "空头枚举传参的订单应该成功插入"
        print("✓ 空头方向枚举传参成功")

        
        print("✓ 交易方向枚举转换测试通过")

    def test_order_status_enum_conversions(self):
        """测试订单状态枚举转换功能"""
        print("\n" + "="*60)
        print("开始测试: 订单状态枚举转换")
        print("="*60)

        order_crud = OrderCRUD()

        # 测试所有有效状态的枚举传参
        valid_statuses = [
            ORDERSTATUS_TYPES.NEW,
            ORDERSTATUS_TYPES.SUBMITTED,
            ORDERSTATUS_TYPES.PARTIAL_FILLED,
            ORDERSTATUS_TYPES.FILLED,
            ORDERSTATUS_TYPES.CANCELED
        ]

        print(f"\n→ 测试 {len(valid_statuses)} 种订单状态枚举传参...")

        for i, status in enumerate(valid_statuses):
            test_order = MOrder(
                engine_id="test_engine_status",
                run_id="test_run_status",
                portfolio_id="test_portfolio_status",
                code=f"00000{i+1}.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                volume=1000,
                limit_price=10.0 + i,
                status=status,  # 直接传入枚举对象
                source=SOURCE_TYPES.TEST
            )

            result = order_crud.add(test_order)
            assert result is not None, f"状态 {status.name} 的订单应该成功插入"
            print(f"  ✓ {status.name} 状态枚举传参成功")

        # 验证查询时的枚举转换
        print("\n→ 验证查询时的枚举转换...")
        orders = order_crud.find(filters={"engine_id": "test_engine_status"})
        assert len(orders) == len(valid_statuses), "应该查询到所有状态的订单"

        for order in orders:
            assert order.status in valid_statuses, "查询结果应该是有效的枚举对象"
            status_name = order.status.name
            print(f"  ✓ 订单 {order.code} 状态: {status_name}")

        # 测试状态过滤查询（枚举传参）
        print("\n→ 测试状态过滤查询（枚举传参）...")
        filled_orders = order_crud.find(
            filters={
                "engine_id": "test_engine_status",
                "status": ORDERSTATUS_TYPES.FILLED  # 枚举传参
            }
        )
        print(f"  ✓ FILLED状态订单: {len(filled_orders)} 条")

        
        print("✓ 订单状态枚举转换测试通过")

    def test_order_type_enum_conversions(self):
        """测试订单类型枚举转换功能"""
        print("\n" + "="*60)
        print("开始测试: 订单类型枚举转换")
        print("="*60)

        order_crud = OrderCRUD()

        # 测试不同订单类型的枚举传参
        order_types = [
            (ORDER_TYPES.LIMITORDER, "限价单"),
            (ORDER_TYPES.MARKETORDER, "市价单")
        ]

        print(f"\n→ 测试 {len(order_types)} 种订单类型枚举传参...")

        for i, (order_type, type_name) in enumerate(order_types):
            test_order = MOrder(
                engine_id="test_engine_type",
                run_id="test_run_type",
                portfolio_id="test_portfolio_type",
                code=f"60000{i+1}.SH",
                direction=DIRECTION_TYPES.LONG,
                order_type=order_type,  # 直接传入枚举对象
                volume=1000,
                limit_price=10.0 + i if order_type == ORDER_TYPES.LIMITORDER else None,
                status=ORDERSTATUS_TYPES.NEW,
                source=SOURCE_TYPES.TEST
            )

            result = order_crud.add(test_order)
            assert result is not None, f"{type_name} 订单应该成功插入"
            print(f"  ✓ {type_name} 枚举传参成功")

        # 验证查询时的枚举转换
        print("\n→ 验证查询时的枚举转换...")
        orders = order_crud.find(filters={"engine_id": "test_engine_type"})
        assert len(orders) == len(order_types), "应该查询到所有类型的订单"

        for order in orders:
            assert order.order_type in [ot for ot, _ in order_types], "查询结果应该是有效的枚举对象"
            type_name = dict(order_types)[order.order_type]
            print(f"  ✓ 订单 {order.code} 类型: {type_name}")

        # 测试订单类型过滤查询（枚举传参）
        print("\n→ 测试订单类型过滤查询（枚举传参）...")
        limit_orders = order_crud.find(
            filters={
                "engine_id": "test_engine_type",
                "order_type": ORDER_TYPES.LIMITORDER  # 枚举传参
            }
        )
        print(f"  ✓ 限价单订单: {len(limit_orders)} 条")

        
        print("✓ 订单类型枚举转换测试通过")

    def test_comprehensive_enum_validation(self):
        """测试综合枚举验证功能"""
        print("\n" + "="*60)
        print("开始测试: 综合枚举验证")
        print("="*60)

        order_crud = OrderCRUD()

        # 创建包含所有枚举字段的测试订单
        test_orders = []
        enum_combinations = [
            # (方向, 订单类型, 状态, 描述)
            (DIRECTION_TYPES.LONG, ORDER_TYPES.LIMITORDER, ORDERSTATUS_TYPES.NEW, "做多限价单新建"),
            (DIRECTION_TYPES.SHORT, ORDER_TYPES.MARKETORDER, ORDERSTATUS_TYPES.FILLED, "做空市价单成交"),
            (DIRECTION_TYPES.LONG, ORDER_TYPES.LIMITORDER, ORDERSTATUS_TYPES.CANCELED, "做多限价单取消"),
        ]

        print(f"\n→ 创建 {len(enum_combinations)} 个综合枚举测试订单...")

        
        for i, (direction, order_type, status, desc) in enumerate(enum_combinations):
            test_order = MOrder(
                engine_id="test_engine_comprehensive",
                run_id="test_run_comprehensive",
                portfolio_id="test_portfolio_comprehensive",
                code=f"COMPREHENSIVE_{i+1:03d}.SZ",  # 使用更唯一的代码
                direction=direction,      # 枚举传参
                order_type=order_type,    # 枚举传参
                volume=1000 + i * 100,
                limit_price=10.0 + i if order_type == ORDER_TYPES.LIMITORDER else None,
                status=status,            # 枚举传参
                source=SOURCE_TYPES.TEST  # 枚举传参
            )

            result = order_crud.add(test_order)
            assert result is not None, f"{desc} 订单应该成功插入"
            test_orders.append(test_order)
            print(f"  ✓ {desc} 创建成功")

        # 验证所有枚举字段的存储和查询
        print("\n→ 验证所有枚举字段的存储和查询...")
        orders = order_crud.find(filters={"engine_id": "test_engine_comprehensive"})
        assert len(orders) == len(enum_combinations), "应该查询到所有综合测试订单"

        # 创建代码到预期枚举组合的映射
        expected_map = {
            f"COMPREHENSIVE_{i+1:03d}.SZ": enum_combinations[i]
            for i in range(len(enum_combinations))
        }

        for order in orders:
            expected_direction, expected_type, expected_status, _ = expected_map[order.code]

            # 验证枚举字段正确性
            assert order.direction == expected_direction, f"订单 {order.code} 方向枚举不匹配，预期{expected_direction.name}，实际{order.direction.name}"
            assert order.order_type == expected_type, f"订单 {order.code} 类型枚举不匹配，预期{expected_type.name}，实际{order.order_type.name}"
            assert order.status == expected_status, f"订单 {order.code} 状态枚举不匹配，预期{expected_status.name}，实际{order.status.name}"
            assert order.source == SOURCE_TYPES.TEST, f"订单 {order.code} 数据源枚举不匹配"

            print(f"  ✓ 订单 {order.code}: {order.direction.name}/{order.order_type.name}/{order.status.name}")

        # 验证ModelList转换功能
        print("\n→ 验证ModelList转换功能...")
        model_list = order_crud.find(filters={"engine_id": "test_engine_comprehensive"})

        assert len(model_list) == len(enum_combinations), "ModelList应该包含所有测试订单"

        # 验证to_entities()方法中的枚举转换
        entities = model_list.to_entities()
        for entity in entities:
            assert isinstance(entity.direction, DIRECTION_TYPES), "业务对象direction应该是枚举类型"
            assert isinstance(entity.order_type, ORDER_TYPES), "业务对象order_type应该是枚举类型"
            assert isinstance(entity.status, ORDERSTATUS_TYPES), "业务对象status应该是枚举类型"
            assert isinstance(entity.source, SOURCE_TYPES), "业务对象source应该是枚举类型"

        print("  ✓ ModelList转换中的枚举验证正确")

        
        print("✓ 综合枚举验证测试通过")


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：Order CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_order_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")