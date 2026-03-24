#!/usr/bin/env python3
"""
查询可用交易对列表

从各个数据源获取可用的交易对列表：
- OKX: 加密货币交易对（BTC-USDT, ETH-USDT 等）
- EastMoney: A股股票列表
"""

import sys
import pandas as pd
sys.path.insert(0, '/home/kaoru/Ginkgo')

from ginkgo.trading.feeders.okx_feeder import OKXMarketDataFeeder
from ginkgo.libs import GLOG


def list_okx_pairs():
    """查询 OKX 可用交易对"""
    print("\n" + "=" * 60)
    print("OKX 可用交易对")
    print("=" * 60)

    try:
        # 创建 OKX Feeder
        feeder = OKXMarketDataFeeder(environment="testnet")

        # 获取现货交易对
        instruments = feeder.get_instruments(inst_type="SPOT")

        if not instruments:
            print("❌ 未获取到交易对数据")
            return []

        # 转换为 DataFrame
        df = pd.DataFrame(instruments)

        print(f"\n总计: {len(df)} 个 OKX 现货交易对\n")

        # 显示主要交易对（按交易量排序）
        # 显示前 20 个
        display_df = df[['instId', 'baseCcy', 'quoteCcy', 'state']].head(20)

        print("前 20 个交易对:")
        print(display_df.to_string(index=False))

        # 按基础货币分组统计
        print(f"\n按基础货币统计:")
        base_counts = df['baseCcy'].value_counts().head(10)
        for base, count in base_counts.items():
            print(f"  {base}: {count} 个交易对")

        # 热门交易对（常见的 USDT 交易对）
        popular_pairs = [
            'BTC-USDT', 'ETH-USDT', 'SOL-USDT', 'BNB-USDT',
            'XRP-USDT', 'ADA-USDT', 'DOGE-USDT', 'AVAX-USDT',
            'DOT-USDT', 'LINK-USDT', 'MATIC-USDT', 'UNI-USDT'
        ]

        print(f"\n推荐订阅的热门交易对:")
        for pair in popular_pairs:
            # 检查是否存在
            exists = df['instId'].str.contains(pair).any()
            status = "✅" if exists else "❌"
            print(f"  {status} {pair}")

        return df['instId'].tolist()

    except Exception as e:
        GLOG.ERROR(f"查询 OKX 交易对失败: {e}")
        return []


def list_a_stocks():
    """查询 A 股股票（需要 EastMoney）"""
    print("\n" + "=" * 60)
    print("A 股股票列表")
    print("=" * 60)

    # TODO: 实现从 EastMoney 获取股票列表
    print("\nA 股股票查询功能待实现")
    print("提示: 可以从数据库中查询已同步的股票列表")

    # 查询数据库中已有的股票
    try:
        from ginkgo.data.containers import container
        stockinfo_crud = container.stockinfo_crud()
        stocks = stockinfo_crud.find(limit=100)

        if stocks:
            print(f"\n数据库中有 {len(stocks)} 只股票:")
            for stock in stocks[:20]:
                print(f"  {stock.code} - {stock.name}")
        else:
            print("数据库中没有股票数据")

    except Exception as e:
        GLOG.ERROR(f"查询股票列表失败: {e}")


def show_subscription_tips():
    """显示订阅提示"""
    print("\n" + "=" * 60)
    print("订阅提示")
    print("=" * 60)

    print("\n如何订阅交易对:")
    print("1. 运行 DataManager:")
    print("   python -m ginkgo.livecore.main live-start")
    print()
    print("2. 在另一个终端订阅交易对:")
    print("   python scripts/subscribe_symbols.py")
    print()
    print("3. 或者通过代码订阅:")
    print("   from ginkgo.livecore.data_manager import DataManager")
    print("   dm = DataManager(feeder_types=['okx'])")
    print("   dm.start()")
    print("   dm.subscribe_live_data(symbols=['BTC-USDT', 'ETH-USDT'], source='okx')")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="查询可用交易对列表")
    parser.add_argument("--source", choices=["okx", "stocks", "all"],
                        default="okx", help="数据源选择")
    parser.add_argument("--export", action="store_true", help="导出到文件")

    args = parser.parse_args()

    # 查询交易对
    if args.source in ["okx", "all"]:
        okx_pairs = list_okx_pairs()

    if args.source in ["stocks", "all"]:
        list_a_stocks()

    # 显示订阅提示
    show_subscription_tips()

    # 导出
    if args.export:
        export_file = "/tmp/trading_pairs.txt"
        with open(export_file, "w") as f:
            f.write("可用交易对列表\n")
            f.write("=" * 60 + "\n\n")

            if args.source in ["okx", "all"]:
                f.write("OKX 交易对:\n")
                if 'okx_pairs' in locals():
                    for pair in okx_pairs:
                        f.write(f"  {pair}\n")

        print(f"\n✅ 已导出到: {export_file}")


if __name__ == "__main__":
    main()
