"""
ExecutionNode 完整事件流转测试（含策略配置）

测试 ExecutionNode 加载 Portfolio 并配置策略后的完整事件流：
1. 启动 ExecutionNode
2. 从数据库加载 Portfolio
3. 配置策略、Sizer、RiskManager
4. 创建并发送价格更新事件
5. 验证订单生成

运行方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python examples/test_execution_event_flow_with_strategy.py
"""

from decimal import Decimal
from datetime import datetime
import time

from ginkgo.workers.execution_node.node import ExecutionNode
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.entities.bar import Bar
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.trading.bases.sizer_base import SizerBase
from ginkgo.trading.bases.risk_base import RiskBase
from ginkgo.trading.bases.selector_base import SelectorBase
from ginkgo.entities.signal import Signal
from ginkgo.entities.order import Order
from ginkgo.enums import DIRECTION_TYPES, FREQUENCY_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


class SimpleBuyStrategy(BaseStrategy):
    """简单买入策略：价格 > 10 时买入"""
    def cal(self, portfolio_info, event):
        if event.payload and event.payload.close > Decimal("10.0"):
            # 直接使用默认值，不依赖 Portfolio 属性
            return [Signal(
                portfolio_id="test_portfolio",
                engine_id="test_engine",
                task_id="test_run",
                code=event.payload.code,
                direction=DIRECTION_TYPES.LONG
            )]
        return []


class AllStockSelector(SelectorBase):
    """选择所有股票"""
    def pick(self, time=None, *args, **kwargs):
        return ["*"]  # 通配符表示所有股票


class FixedSizer(SizerBase):
    """固定买入100股"""
    def cal(self, portfolio_info, signal):
        # signal 是 Signal 对象
        return Order(
            portfolio_id=signal.portfolio_id,
            engine_id=signal.engine_id,
            task_id=signal.task_id,
            code=signal.code,
            direction=signal.direction,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=100,
            limit_price=Decimal("10.5")
        )


class NoRisk(RiskBase):
    """无风控，放行所有订单"""
    def cal(self, portfolio_info, order):
        return order


def print_separator(title: str):
    """打印分隔线"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_execution_with_strategy():
    """测试 ExecutionNode 加载 Portfolio 并配置策略后的事件流转"""

    print_separator("🚀 ExecutionNode 完整事件流转测试（含策略）")

    # ============================================================
    # 步骤1: 创建并启动 ExecutionNode
    # ============================================================
    print("📦 步骤1: 创建 ExecutionNode")
    execution_node = ExecutionNode('test_strategy_node')
    print(f"✅ ExecutionNode 创建成功: {execution_node.node_id}")

    # ============================================================
    # 步骤2: 从数据库加载 Portfolio
    # ============================================================
    print("\n📊 步骤2: 从数据库加载 Portfolio")

    portfolio_id = 'e65895d3947c4e96884232b7f3715809'

    print(f"正在加载 Portfolio: {portfolio_id[:8]}...")
    load_result = execution_node.load_portfolio(portfolio_id)

    if not load_result:
        print("❌ Portfolio 加载失败，测试终止")
        return

    print(f"✅ Portfolio 加载成功")

    # ============================================================
    # 步骤3: 配置策略、Sizer、RiskManager
    # ============================================================
    print("\n⚙️  步骤3: 配置策略组件")

    portfolio = execution_node._portfolio_instances[portfolio_id]

    # 确保 Portfolio 有 engine_id 和 task_id
    # 注意：这些是只读属性，需要在创建时设置或使用默认值
    print(f"   Portfolio ID: {portfolio.portfolio_id}")
    print(f"   Engine ID: {portfolio.engine_id if portfolio.engine_id else 'N/A (will use default)'}")
    print(f"   Task ID: {portfolio.task_id if portfolio.task_id else 'N/A (will use default)'}")

    # 添加策略
    strategy = SimpleBuyStrategy()
    portfolio.add_strategy(strategy)
    print(f"✅ 策略已添加: {strategy.name}")

    # 绑定 Selector
    selector = AllStockSelector()
    portfolio.bind_selector(selector)
    print(f"✅ Selector 已绑定: {type(selector).__name__}")

    # 绑定 Sizer
    sizer = FixedSizer()
    portfolio.bind_sizer(sizer)
    print(f"✅ Sizer 已绑定: {type(sizer).__name__}")

    # 添加风控
    risk_mgr = NoRisk()
    portfolio.add_risk_manager(risk_mgr)
    print(f"✅ RiskManager 已添加: {type(risk_mgr).__name__}")

    # 验证配置
    print(f"\nPortfolio 配置状态:")
    print(f"   策略数量: {len(portfolio._strategies)}")
    print(f"   Selectors: {len(portfolio._selectors)}")
    print(f"   Sizer: {portfolio._sizer is not None}")
    print(f"   RiskManagers: {len(portfolio._risk_managers)}")

    # ============================================================
    # 步骤4: 获取订阅信息
    # ============================================================
    print(f"\n🗺️  步骤4: 检查订阅信息")
    subscribed_codes = list(execution_node.interest_map.interest_map.keys())
    test_code = subscribed_codes[0]
    print(f"测试用股票: {test_code}")

    # ============================================================
    # 步骤5: 创建并发送价格事件
    # ============================================================
    print(f"\n📈 步骤5: 创建价格事件（{test_code}, 价格=10.5）")

    bar = Bar(
        code=test_code,
        timestamp=datetime.now(),
        open=Decimal("10.0"),
        high=Decimal("10.8"),
        low=Decimal("10.0"),
        close=Decimal("10.5"),  # 价格 > 10，触发买入
        volume=1000000,
        amount=Decimal("10500000"),
        frequency=FREQUENCY_TYPES.DAY
    )

    price_event = EventPriceUpdate(payload=bar)
    print(f"✅ 事件创建: {bar.code} @ {bar.close}")

    # ============================================================
    # 步骤6: 发送到 Input Queue
    # ============================================================
    print(f"\n📤 步骤6: 发送到 Input Queue")

    processor = execution_node.portfolios[portfolio_id]
    processor.input_queue.put(price_event)

    print(f"✅ 事件已发送")
    print(f"   Input Queue: {processor.input_queue.qsize()}")

    # ============================================================
    # 步骤7: 等待处理
    # ============================================================
    print(f"\n⏳ 步骤7: 等待处理（2秒）...")
    time.sleep(2.0)

    print(f"处理完成:")
    print(f"   Input Queue: {processor.input_queue.qsize()}")
    print(f"   Output Queue: {processor.output_queue.qsize()}")

    # ============================================================
    # 步骤8: 检查生成的订单
    # ============================================================
    print(f"\n📥 步骤8: 检查 Output Queue")

    orders = []
    while not processor.output_queue.empty():
        try:
            event = processor.output_queue.get_nowait()
            orders.append(event)

            if hasattr(event, 'order'):
                order = event.order
                print(f"✅ 订单生成:")
                print(f"   订单 ID: {order.uuid[:8]}...")
                print(f"   股票: {order.code}")
                print(f"   方向: {order.direction.name}")
                print(f"   数量: {order.volume}")
                print(f"   限价: {order.limit_price}")
                print(f"   状态: {order.status.name}")
        except:
            break

    # ============================================================
    # 步骤9: 验证结果
    # ============================================================
    print_separator("✅ 测试结果")

    if orders:
        print(f"""
🎉 完整事件流转验证成功！

📊 事件流转路径：

   EventPriceUpdate (000001.SZ @ 10.5)
            ↓
   InterestMap 路由
            ↓
   Input Queue (1 事件)
            ↓
   PortfolioProcessor.cal()
            ↓
   Strategy.cal() → Signal (买入)
            ↓
   Sizer.cal() → Order (100股 @ 10.5)
            ↓
   RiskManager.cal() → 放行
            ↓
   Output Queue ({len(orders)} 个订单)

✅ 生成订单数量: {len(orders)}
        """)
    else:
        print("⚠️  未生成订单")

    # ============================================================
    # 步骤10: 清理
    # ============================================================
    print(f"\n🛑 步骤10: 清理")

    execution_node.stop()
    print("✅ ExecutionNode 已停止")

    print_separator("测试完成 🎉")


if __name__ == "__main__":
    try:
        test_execution_with_strategy()
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
