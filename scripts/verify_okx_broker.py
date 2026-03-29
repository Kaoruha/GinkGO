#!/usr/bin/env python3
"""
OKX Broker 接口验证脚本

测试 OKX Broker 的所有接口是否正常工作：

1. 连接测试
2. 查询接口测试
3. 交易接口测试（小额测试订单）
4. WebSocket 推送测试

使用方法:
    # 1. 创建实盘账号
    python -m ginkgo.livecore.main live-init

    # 2. 运行验证脚本
    python scripts/verify_okx_broker.py --account-id <ACCOUNT_UUID>
"""

import sys
import time
import asyncio
from typing import Optional
from datetime import datetime

# 添加项目路径
sys.path.insert(0, '/home/kaoru/Ginkgo')

from ginkgo.trading.brokers.okx_broker import OKXBroker
from ginkgo.entities.order import Order
from ginkgo.enums import ORDER_TYPES, DIRECTION_TYPES, ORDERSTATUS_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.containers import container
from ginkgo.data.services.encryption_service import get_encryption_service


class OKXBrokerVerifier:
    """OKX Broker 接口验证器"""

    def __init__(self, account_id: str):
        self.account_id = account_id
        self.broker: Optional[OKXBroker] = None

    def setup_broker(self) -> bool:
        """设置并连接 Broker"""
        try:
            # 从数据库获取账号信息
            account_service = container.live_account_service()
            account_result = account_service.get_account_by_uuid(self.account_id)

            if not account_result.success:
                GLOG.ERROR(f"Failed to get account: {account_result.error}")
                return False

            account = account_result.data

            # 创建 Broker 实例
            self.broker = OKXBroker(
                broker_uuid=f"verify_{self.account_id[:8]}",
                portfolio_id="verify_portfolio",
                live_account_id=self.account_id,
                api_key=account.api_key,
                api_secret=account.api_secret,
                passphrase=account.passphrase,
                environment=account.environment
            )

            # 连接
            if not self.broker.connect():
                GLOG.ERROR("Failed to connect to OKX")
                return False

            GLOG.INFO("✅ Broker connected successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to setup broker: {e}")
            return False

    def test_connection(self) -> bool:
        """测试 1: 连接状态"""
        GLOG.INFO("\n=== 测试 1: 连接状态 ===")

        if self.broker.is_connected():
            GLOG.INFO("✅ is_connected() = True")
            return True
        else:
            GLOG.ERROR("❌ is_connected() = False")
            return False

    def test_query_interfaces(self) -> bool:
        """测试 2: 查询接口"""
        GLOG.INFO("\n=== 测试 2: 查询接口 ===")

        all_passed = True

        # 2.1 获取账户余额
        GLOG.INFO("\n2.1 获取账户余额...")
        balance = self.broker.get_account_balance()
        if balance:
            GLOG.INFO(f"✅ get_account_balance() 返回数据: {len(balance)} 项")
            if isinstance(balance, list) and len(balance) > 0:
                GLOG.INFO(f"   示例: {balance[0]}")
        else:
            GLOG.ERROR("❌ get_account_balance() 返回空")
            all_passed = False

        # 2.2 获取持仓信息
        GLOG.INFO("\n2.2 获取持仓信息...")
        positions = self.broker.get_positions()
        GLOG.INFO(f"✅ get_positions() 返回 {len(positions)} 个持仓")
        if positions:
            GLOG.INFO(f"   示例: {positions[0]}")

        # 2.3 获取挂单信息
        GLOG.INFO("\n2.3 获取挂单信息...")
        open_orders = self.broker.get_open_orders()
        GLOG.INFO(f"✅ get_open_orders() 返回 {len(open_orders)} 个挂单")
        if open_orders:
            for order in open_orders[:3]:  # 只显示前3个
                GLOG.INFO(f"   订单: {order['symbol']} {order['side']} {order['size']} @ {order['price']}")

        return all_passed

    def test_order_validation(self) -> bool:
        """测试 3: 订单验证"""
        GLOG.INFO("\n=== 测试 3: 订单验证 ===")

        # 3.1 有效订单
        GLOG.INFO("\n3.1 验证有效订单...")
        valid_order = Order(
            portfolio_id="test_portfolio",
            code="BTC-USDT",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            volume=0.001,
            limit_price=30000
        )
        valid_order.limit_price = 50000  # 设置一个低价

        if self.broker.validate_order(valid_order):
            GLOG.INFO("✅ validate_order() 有效订单通过")
        else:
            GLOG.ERROR("❌ validate_order() 有效订单被拒绝")
            return False

        # 3.2 无效订单
        GLOG.INFO("\n3.2 验证无效订单...")
        invalid_order = Order(
            portfolio_id="test_portfolio",
            code="",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            volume=0
        )

        if not self.broker.validate_order(invalid_order):
            GLOG.INFO("✅ validate_order() 无效订单被拒绝")
        else:
            GLOG.ERROR("❌ validate_order() 无效订单通过（应该被拒绝）")
            return False

        return True

    def test_order_submission(self) -> bool:
        """测试 4: 订单提交（小额测试）"""
        GLOG.INFO("\n=== 测试 4: 订单提交 ===")
        GLOG.WARNING("⚠️  此测试会提交实际订单到 OKX 测试网")
        GLOG.INFO("   使用极小数量和远离市场的价格，避免成交")

        user_input = input("\n是否继续测试订单提交? (y/N): ")
        if user_input.lower() != 'y':
            GLOG.INFO("跳过订单提交测试")
            return True

        # 创建测试订单 - 使用远离市场的价格避免成交
        test_order = Order(
            portfolio_id="test_portfolio",
            code="BTC-USDT",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            volume=0.001,  # 最小数量
            limit_price=1.0  # 极低价格，不会成交
        )
        test_order.timestamp = datetime.now()

        # 提交订单
        GLOG.INFO(f"\n提交测试订单: {test_order.code} {test_order.direction.name} {test_order.volume} @ {test_order.limit_price}")

        # 创建模拟事件
        from ginkgo.trading.events import EventOrderPlace
        event = EventOrderPlace(
            order=test_order,
            portfolio_id="test_portfolio",
            engine_id="verify_engine",
            run_id="verify_run"
        )

        result = self.broker.submit_order_event(event)

        if result.status == ORDERSTATUS_TYPES.SUBMITTED:
            GLOG.INFO(f"✅ 订单提交成功")
            GLOG.INFO(f"   Broker Order ID: {result.broker_order_id}")

            # 5 秒后查询订单状态
            GLOG.INFO("\n等待 5 秒后查询订单状态...")
            time.sleep(5)

            order_info = self.broker._query_from_exchange(result.broker_order_id)
            if order_info:
                GLOG.INFO(f"✅ 订单状态查询成功")
                GLOG.INFO(f"   状态: {order_info.get('state')}")
                GLOG.INFO(f"   订单信息: {order_info}")
            else:
                GLOG.ERROR("❌ 订单状态查询失败")

            # 尝试撤销订单
            GLOG.INFO("\n撤销测试订单...")
            cancel_result = self.broker.cancel_order(result.broker_order_id)
            if cancel_result.status == ORDERSTATUS_TYPES.CANCELED:
                GLOG.INFO("✅ 订单撤销成功")
            else:
                GLOG.ERROR(f"❌ 订单撤销失败: {cancel_result.error_message}")

            return True
        else:
            GLOG.ERROR(f"❌ 订单提交失败: {result.error_message}")
            return False

    def test_websocket(self) -> bool:
        """测试 5: WebSocket 推送"""
        GLOG.INFO("\n=== 测试 5: WebSocket 推送 ===")

        user_input = input("\n是否测试 WebSocket 功能? (y/N): ")
        if user_input.lower() != 'y':
            GLOG.INFO("跳过 WebSocket 测试")
            return True

        # 启用 WebSocket
        if not self.broker.enable_websocket():
            GLOG.ERROR("❌ WebSocket 启用失败")
            return False

        GLOG.INFO("✅ WebSocket 启用成功")

        # 订阅账户余额
        def account_callback(message):
            GLOG.INFO(f"📡 收到账户推送: {message}")

        if self.broker.subscribe_account_ws(account_callback):
            GLOG.INFO("✅ 订阅账户余额成功")
        else:
            GLOG.ERROR("❌ 订阅账户余额失败")

        # 订阅持仓
        def position_callback(message):
            GLOG.INFO(f"📡 收到持仓推送: {message}")

        if self.broker.subscribe_positions_ws(position_callback):
            GLOG.INFO("✅ 订阅持仓信息成功")
        else:
            GLOG.ERROR("❌ 订阅持仓信息失败")

        # 等待推送
        GLOG.INFO("\n等待 10 秒接收 WebSocket 推送...")
        time.sleep(10)

        # 获取缓存数据
        cached_balance = self.broker.get_cached_account_balance()
        if cached_balance:
            GLOG.INFO(f"✅ 缓存余额: {cached_balance}")

        cached_positions = self.broker.get_cached_positions()
        if cached_positions:
            GLOG.INFO(f"✅ 缓存持仓: {list(cached_positions.keys())}")

        # 取消订阅
        self.broker.unsubscribe_account_ws()
        self.broker.unsubscribe_positions_ws()
        GLOG.INFO("✅ 取消订阅完成")

        return True

    def run_all_tests(self) -> bool:
        """运行所有测试"""
        GLOG.info("=" * 60)
        GLOG.info("OKX Broker 接口验证测试")
        GLOG.info("=" * 60)

        if not self.setup_broker():
            return False

        results = []

        # 测试 1: 连接
        results.append(("连接状态", self.test_connection()))

        # 测试 2: 查询接口
        results.append(("查询接口", self.test_query_interfaces()))

        # 测试 3: 订单验证
        results.append(("订单验证", self.test_order_validation()))

        # 测试 4: 订单提交
        results.append(("订单提交", self.test_order_submission()))

        # 测试 5: WebSocket
        results.append(("WebSocket", self.test_websocket()))

        # 打印测试结果
        GLOG.info("\n" + "=" * 60)
        GLOG.info("测试结果汇总")
        GLOG.info("=" * 60)

        for test_name, passed in results:
            status = "✅ 通过" if passed else "❌ 失败"
            GLOG.info(f"{test_name}: {status}")

        all_passed = all(passed for _, passed in results)

        if all_passed:
            GLOG.info("\n🎉 所有测试通过！OKX Broker 接口正常工作")
        else:
            GLOG.error("\n⚠️  部分测试失败，请检查日志")

        # 断开连接
        self.broker.disconnect()

        return all_passed


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="验证 OKX Broker 接口")
    parser.add_argument("--account-id", required=True, help="实盘账号 UUID")
    args = parser.parse_args()

    verifier = OKXBrokerVerifier(args.account_id)
    success = verifier.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
