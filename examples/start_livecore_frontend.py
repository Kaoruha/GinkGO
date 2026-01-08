#!/usr/bin/env python
"""
前台启动 LiveCore 进行测试

启动方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python examples/start_livecore_frontend.py

功能：
    - 前台启动 LiveCore（非daemon模式）
    - 显示实时日志输出
    - 支持 Ctrl+C 优雅停止
    - 展示各组件运行状态
"""

import sys
import time
import signal
import logging
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ginkgo.livecore.main import LiveCore


def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def print_banner():
    """打印启动横幅"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║           🚀 Ginkgo 实盘交易系统 - LiveCore 前台启动               ║
║                                                                    ║
║  组件: ExecutionNode, PortfolioProcessor, TradeGatewayAdapter       ║
║                                                                    ║
║  控制: Ctrl+C 停止                                                ║
║                                                                    ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n\n{'='*70}")
    print(f"📛 收到停止信号: {signum}")
    print(f"{'='*70}\n")


def main():
    """主函数"""

    # 配置日志
    setup_logging()

    # 打印横幅
    print_banner()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建 LiveCore 实例
    print("📦 正在创建 LiveCore 实例...")
    livecore = LiveCore()

    # 显示配置信息
    print("\n" + "="*70)
    print("📋 LiveCore 配置信息")
    print("="*70)
    print(f"   组件数量: {len(livecore.components) if hasattr(livecore, 'components') else 'N/A'}")
    print(f"   运行模式: 前台（非daemon）")
    print(f"   日志级别: INFO")
    print("="*70 + "\n")

    # 启动 LiveCore
    print("🚀 正在启动 LiveCore...")
    print("   " + "·"*30)
    print()

    try:
        livecore.start()

        print("✅ LiveCore 启动成功！")
        print()
        print("📊 组件状态:")
        print("   " + "-"*50)

        # 显示各组件状态
        for name, component in livecore.components.items():
            status = "🟢 运行中" if component and component.is_alive() else "🔴 未启动"
            print(f"   • {name:20s}: {status}")

        print("   " + "-"*50)
        print()
        print("📝 LiveCore 正在运行，按 Ctrl+C 停止...")
        print()

        # 等待（阻塞直到收到停止信号）
        livecore.wait()

    except KeyboardInterrupt:
        print("\n\n⚠️  检测到键盘中断 (Ctrl+C)")

    except Exception as e:
        print(f"\n\n❌ LiveCore 运行出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 优雅停止
        print()
        print("="*70)
        print("🛑 正在停止 LiveCore...")
        print("="*70)

        livecore.stop()

        print()
        print("✅ LiveCore 已停止")
        print()
        print("📊 最终统计:")
        print("   " + "-"*50)

        # 显示最终统计
        for name, component in livecore.components.items():
            if component and hasattr(component, 'get_statistics'):
                try:
                    stats = component.get_statistics()
                    print(f"   • {name:20s}: {stats}")
                except:
                    status = "🟢 已停止" if not component.is_alive() else "🔴 仍在运行"
                    print(f"   • {name:20s}: {status}")
            else:
                status = "🟢 已停止" if not component or not component.is_alive() else "🔴 仍在运行"
                print(f"   • {name:20s}: {status}")

        print("   " + "-"*50)
        print()
        print("👋 再见！")


if __name__ == "__main__":
    main()
