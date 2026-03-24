#!/usr/bin/env python3
"""
订阅交易对示例脚本

演示如何订阅 OKX 交易对的实时数据
"""

import sys
sys.path.insert(0, '/home/kaoru/Ginkgo')

from ginkgo.livecore.data_manager import DataManager
from ginkgo.libs import GLOG
import time

def main():
    print("=" * 60)
    print("交易对订阅示例")
    print("=" * 60)

    # 1. 创建 DataManager（包含 OKX 数据源）
    print("\n[1] 创建 DataManager（包含 OKX 数据源）...")
    dm = DataManager(feeder_types=["okx"])

    # 2. 启动 DataManager
    print("[2] 启动 DataManager...")
    if not dm.start():
        print("❌ DataManager 启动失败")
        return

    print("✅ DataManager 启动成功")

    # 3. 订阅交易对
    print("\n[3] 订阅 OKX 交易对...")

    # 加密货币交易对
    crypto_pairs = [
        "BTC-USDT",
        "ETH-USDT",
        "SOL-USDT",
        "DOGE-USDT",
        "PEPE-USDT"
    ]

    dm.subscribe_live_data(
        symbols=crypto_pairs,
        source="okx"  # 指定使用 OKX
    )

    print(f"✅ 已订阅 {len(crypto_pairs)} 个交易对:")
    for pair in crypto_pairs:
        print(f"   - {pair}")

    # 4. 查看订阅状态
    print("\n[4] 当前订阅状态:")
    status = dm.get_status()
    print(f"   数据源: {list(status.get('sources', {}).keys())}")
    print(f"   总订阅数: {status.get('total_symbols', 0)}")

    # 5. 动态添加订阅
    print("\n[5] 动态添加更多交易对...")
    new_pairs = ["BNB-USDT", "ADA-USDT"]
    dm.subscribe_live_data(symbols=new_pairs, source="okx")
    print(f"✅ 已添加: {', '.join(new_pairs)}")

    # 6. 等待一段时间接收数据
    print("\n[6] 接收实时数据（10秒）...")
    print("   提示：数据将通过 Kafka 发送到 ExecutionNode")

    time.sleep(10)

    # 7. 停止 DataManager
    print("\n[7] 停止 DataManager...")
    dm.stop()
    print("✅ 已停止")

    print("\n" + "=" * 60)
    print("订阅示例完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
