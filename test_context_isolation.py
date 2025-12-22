"""
测试上下文隔离机制
验证：
1. 同一个 Engine 下的不同 Portfolio 是否有不同的 portfolio_id
2. 不同 Portfolio 是否共享同一个 engine_id 和 run_id
"""

import sys
sys.path.insert(0, '/home/kaoru/Ginkgo/src')

from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest


def test_context_isolation():
    print("=" * 60)
    print("测试上下文隔离机制")
    print("=" * 60)

    # 创建引擎
    engine = TimeControlledEventEngine(name="test_engine")
    engine.set_engine_id("test_engine_123")

    # 创建两个不同的 Portfolio
    portfolio1 = PortfolioT1Backtest(name="portfolio_1")
    portfolio2 = PortfolioT1Backtest(name="portfolio_2")

    print(f"\nPortfolio 1 UUID: {portfolio1.uuid[:8]}...")
    print(f"Portfolio 2 UUID: {portfolio2.uuid[:8]}...")

    # 添加到引擎
    engine.add_portfolio(portfolio1)
    engine.add_portfolio(portfolio2)

    # 生成 run_id
    engine.generate_run_id()

    print(f"\nEngine ID: {engine.engine_id}")
    print(f"Run ID: {engine.run_id}")

    # 检查 Portfolio 的上下文
    print("\n" + "=" * 60)
    print("Portfolio 1 上下文:")
    print("=" * 60)
    print(f"  engine_id: {portfolio1.engine_id}")
    print(f"  run_id: {portfolio1.run_id}")
    print(f"  portfolio_id: {portfolio1.portfolio_id}")
    print(f"  _context 类型: {type(portfolio1._context).__name__}")

    print("\n" + "=" * 60)
    print("Portfolio 2 上下文:")
    print("=" * 60)
    print(f"  engine_id: {portfolio2.engine_id}")
    print(f"  run_id: {portfolio2.run_id}")
    print(f"  portfolio_id: {portfolio2.portfolio_id}")
    print(f"  _context 类型: {type(portfolio2._context).__name__}")

    # 验证隔离
    print("\n" + "=" * 60)
    print("验证结果:")
    print("=" * 60)

    # 检查 engine_id 和 run_id 是否共享
    shared_engine_id = portfolio1.engine_id == portfolio2.engine_id == engine.engine_id
    shared_run_id = portfolio1.run_id == portfolio2.run_id == engine.run_id

    # 检查 portfolio_id 是否隔离
    isolated_portfolio_id = portfolio1.portfolio_id != portfolio2.portfolio_id

    # 检查 PortfolioContext 是否独立
    independent_context = portfolio1._context is not portfolio2._context

    # 检查 EngineContext 是否共享
    shared_engine_context = portfolio1._context._engine_context is portfolio2._context._engine_context

    print(f"✅ engine_id 共享: {shared_engine_id}")
    print(f"✅ run_id 共享: {shared_run_id}")
    print(f"✅ portfolio_id 隔离: {isolated_portfolio_id}")
    print(f"✅ PortfolioContext 独立: {independent_context}")
    print(f"✅ EngineContext 共享: {shared_engine_context}")

    all_passed = all([
        shared_engine_id,
        shared_run_id,
        isolated_portfolio_id,
        independent_context,
        shared_engine_context
    ])

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！上下文隔离机制正常工作")
    else:
        print("❌ 测试失败！存在以下问题：")
        if not shared_engine_id:
            print("   - engine_id 未正确共享")
        if not shared_run_id:
            print("   - run_id 未正确共享")
        if not isolated_portfolio_id:
            print("   - portfolio_id 未正确隔离")
        if not independent_context:
            print("   - PortfolioContext 未独立")
        if not shared_engine_context:
            print("   - EngineContext 未共享")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = test_context_isolation()
    sys.exit(0 if success else 1)
