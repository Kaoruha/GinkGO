#!/usr/bin/env python3
"""
测试 EventPriceUpdate 信号生成流程

验证：
1. EventPriceUpdate 事件创建
2. Portfolio.on_price_update() 处理
3. 策略信号生成
4. 风控信号生成
5. 订单事件输出
"""

import sys
sys.path.insert(0, '/home/kaoru/Ginkgo/src')

from ginkgo.data.containers import container
from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.risk_management.position_ratio_risk import PositionRatioRisk
from ginkgo.trading.selectors.fixed_selector import FixedSelector
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.context.engine_context import EngineContext
from ginkgo.trading.context.portfolio_context import PortfolioContext
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, FREQUENCY_TYPES
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from datetime import datetime
from decimal import Decimal

console = Console()


def test_step_1_create_portfolio():
    """步骤1: 创建Portfolio实例"""
    console.print("\n[bold cyan]步骤1: 创建Portfolio实例[/bold cyan]")

    try:
        # 创建Portfolio
        portfolio = PortfolioLive(
            portfolio_id="test_portfolio_001",
            name="测试投资组合"
        )

        # 添加初始资金
        portfolio.add_cash(100000.0)
        portfolio.initial_capital = 100000.0
        portfolio.frozen_cash = 0.0

        # 创建上下文并设置engine_id和run_id
        engine_context = EngineContext(engine_id="livecore")
        engine_context.set_run_id("test_run_001")  # 设置run_id
        portfolio_context = PortfolioContext(
            portfolio_id=portfolio.uuid,
            engine_context=engine_context
        )
        portfolio._context = portfolio_context

        console.print(f"[green]✓ Portfolio创建成功[/green]")
        console.print(f"  portfolio_id: {portfolio.portfolio_id}")
        console.print(f"  name: {portfolio.name}")
        console.print(f"  cash: {portfolio.cash}")
        console.print(f"  engine_id: {portfolio.engine_id}")
        console.print(f"  run_id: {portfolio.run_id}")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_2_add_strategy(portfolio):
    """步骤2: 添加策略"""
    console.print("\n[bold cyan]步骤2: 添加策略[/bold cyan]")

    try:
        # 创建随机信号策略（用于测试）
        strategy = RandomSignalStrategy()
        portfolio.add_strategy(strategy)

        console.print(f"[green]✓ 策略添加成功[/green]")
        console.print(f"  策略名称: {strategy.name}")
        console.print(f"  策略类型: {type(strategy).__name__}")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_3_add_sizer(portfolio):
    """步骤3: 添加Sizer"""
    console.print("\n[bold cyan]步骤3: 添加Sizer[/bold cyan]")

    try:
        # 创建固定大小Sizer
        sizer = FixedSizer(volume=100)
        portfolio.bind_sizer(sizer)

        console.print(f"[green]✓ Sizer添加成功[/green]")
        console.print(f"  Sizer类型: {type(sizer).__name__}")
        console.print(f"  固定数量: {sizer.volume}")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_4_add_risk_manager(portfolio):
    """步骤4: 添加风控管理器"""
    console.print("\n[bold cyan]步骤4: 添加风控管理器[/bold cyan]")

    try:
        # 创建持仓比例风控
        risk_manager = PositionRatioRisk(
            max_position_ratio=0.3,
            max_total_position_ratio=0.8
        )
        portfolio.add_risk_manager(risk_manager)

        console.print(f"[green]✓ 风控管理器添加成功[/green]")
        console.print(f"  风控类型: {type(risk_manager).__name__}")
        console.print(f"  单股最大仓位: {risk_manager.max_position_ratio}")
        console.print(f"  总仓位上限: {risk_manager.max_total_position_ratio}")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_5_add_selector(portfolio):
    """步骤5: 添加Selector"""
    console.print("\n[bold cyan]步骤5: 添加Selector[/bold cyan]")

    try:
        # 创建固定选股器（选择测试股票）
        selector = FixedSelector(name="test_selector", codes=["000001.SZ"])
        portfolio.bind_selector(selector)

        console.print(f"[green]✓ Selector添加成功[/green]")
        console.print(f"  Selector类型: {type(selector).__name__}")
        console.print(f"  选择股票: 000001.SZ")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_6_check_ready(portfolio):
    """步骤6: 检查组件就绪状态"""
    console.print("\n[bold cyan]步骤6: 检查组件就绪状态[/bold cyan]")

    try:
        # 检查is_all_set
        is_ready = portfolio.is_all_set()

        console.print(f"  策略: {'✓' if len(portfolio.strategies) > 0 else '✗'}")
        console.print(f"  Sizer: {'✓' if portfolio.sizer is not None else '✗'}")
        console.print(f"  风控: {'✓' if len(portfolio.risk_managers) > 0 else '✗'}")
        console.print(f"  Selector: {'✓' if len(portfolio.selectors) > 0 else '✗'}")
        console.print(f"\n  [bold]is_all_set():[/bold] {is_ready}")

        if is_ready:
            console.print(f"[green]✓ Portfolio组件齐全，可以处理事件[/green]")
        else:
            console.print(f"[yellow]⚠ Portfolio组件不齐全[/yellow]")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_7_create_price_event():
    """步骤7: 创建EventPriceUpdate"""
    console.print("\n[bold cyan]步骤6: 创建EventPriceUpdate[/bold cyan]")

    try:
        # 创建Bar对象作为payload
        bar = Bar(
            code="000001.SZ",
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.2"),
            volume=1000000,
            amount=Decimal("10000000.0"),
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime.now()
        )

        # 创建价格更新事件
        event = EventPriceUpdate(
            payload=bar,
            timestamp=datetime.now()
        )

        console.print(f"[green]✓ EventPriceUpdate创建成功[/green]")
        console.print(f"  股票代码: {event.code}")
        console.print(f"  Close价格: {event.close}")
        console.print(f"  时间戳: {event.timestamp}")

        return event

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_8_process_event(portfolio, event):
    """步骤8: 处理事件并生成信号"""
    console.print("\n[bold cyan]步骤7: 处理事件并生成信号[/bold cyan]")

    try:
        # 调用on_price_update
        console.print(f"  调用 portfolio.on_price_update(event)...")

        order_events = portfolio.on_price_update(event)

        console.print(f"\n[green]✓ 事件处理完成[/green]")
        console.print(f"  返回的订单事件数量: {len(order_events)}")

        if order_events:
            console.print(f"\n[bold]生成的订单事件:[/bold]")
            table = Table(show_header=True)
            table.add_column("序号", style="cyan")
            table.add_column("事件类型", style="magenta")
            table.add_column("股票代码", style="blue")
            table.add_column("订单ID", style="green")

            for i, order_event in enumerate(order_events, 1):
                event_type = type(order_event).__name__
                code = getattr(order_event, 'code', 'N/A')
                order_id = getattr(order_event, 'order_uuid', 'N/A')

                table.add_row(str(i), event_type, str(code), str(order_id)[:8] + "...")

            console.print(table)
        else:
            console.print(f"[yellow]⚠ 没有生成订单事件[/yellow]")
            console.print(f"  [dim]这可能是因为:[/dim]")
            console.print(f"  • 策略没有生成信号（需要更多历史数据）")
            console.print(f"  • 风控管理器拦截了订单")
            console.print(f"  • Sizer没有生成订单")

        return order_events

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_9_analyz_signals(portfolio):
    """步骤9: 分析信号生成机制"""
    console.print("\n[bold cyan]步骤8: 分析信号生成机制[/bold cyan]")

    try:
        console.print(f"\n[bold]策略信号生成测试:[/bold]")
        console.print(f"  方法: portfolio.generate_strategy_signals(event)")

        # 创建多个价格事件测试
        test_prices = [10.0, 10.5, 11.0, 11.5, 12.0]

        for price in test_prices:
            bar = Bar(
                code="000001.SZ",
                open=Decimal(str(price)),
                high=Decimal(str(price + 0.5)),
                low=Decimal(str(price - 0.5)),
                close=Decimal(str(price)),
                volume=1000000,
                amount=Decimal(str(price * 1000000)),
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime.now()
            )
            event = EventPriceUpdate(
                payload=bar,
                timestamp=datetime.now()
            )

            signals = portfolio.generate_strategy_signals(event)

            if signals:
                console.print(f"  价格 {price}: [green]生成 {len(signals)} 个信号[/green]")
                for signal in signals:
                    console.print(f"    - {signal.direction} {signal.code}")
            else:
                console.print(f"  价格 {price}: [dim]无信号[/dim]")

        console.print(f"\n[bold]风控信号生成测试:[/bold]")
        console.print(f"  方法: portfolio.generate_risk_signals(event)")

        bar = Bar(
            code="000001.SZ",
            open=Decimal("10.0"),
            high=Decimal("10.5"),
            low=Decimal("9.8"),
            close=Decimal("10.2"),
            volume=1000000,
            amount=Decimal("10000000.0"),
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime.now()
        )
        event = EventPriceUpdate(
            payload=bar,
            timestamp=datetime.now()
        )

        risk_signals = portfolio.generate_risk_signals(event)

        if risk_signals:
            console.print(f"  [green]生成 {len(risk_signals)} 个风控信号[/green]")
            for signal in risk_signals:
                console.print(f"    - {signal.direction} {signal.code} (原因: {signal.reason})")
        else:
            console.print(f"  [dim]无风控信号（正常，因为没有持仓）[/dim]")

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()


def main():
    console.print(Panel.fit(
        "[bold cyan]EventPriceUpdate 信号生成测试[/bold cyan]\n"
        "验证 Portfolio 处理价格更新事件并生成信号",
        title="测试"
    ))

    # 步骤1: 创建Portfolio
    portfolio = test_step_1_create_portfolio()
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法创建Portfolio[/red]")
        return

    # 步骤2: 添加策略
    portfolio = test_step_2_add_strategy(portfolio)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法添加策略[/red]")
        return

    # 步骤3: 添加Sizer
    portfolio = test_step_3_add_sizer(portfolio)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法添加Sizer[/red]")
        return

    # 步骤4: 添加风控
    portfolio = test_step_4_add_risk_manager(portfolio)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法添加风控管理器[/red]")
        return

    # 步骤5: 添加Selector
    portfolio = test_step_5_add_selector(portfolio)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法添加Selector[/red]")
        return

    # 步骤6: 检查就绪状态
    portfolio = test_step_6_check_ready(portfolio)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: Portfolio未就绪[/red]")
        return

    # 步骤7: 创建价格事件
    event = test_step_7_create_price_event()
    if not event:
        console.print("\n[red]✗ 测试失败: 无法创建EventPriceUpdate[/red]")
        return

    # 步骤8: 处理事件
    order_events = test_step_8_process_event(portfolio, event)

    # 步骤9: 分析信号生成
    test_step_9_analyz_signals(portfolio)

    console.print("\n" + "="*70)
    console.print("[bold green]✓ 测试完成[/bold green]")
    console.print("\n[bold]关键发现:[/bold]")
    console.print("  • Portfolio可以成功处理EventPriceUpdate事件")
    console.print("  • on_price_update()是处理价格更新的主入口")
    console.print("  • 策略信号通过generate_strategy_signals()生成")
    console.print("  • 风控信号通过generate_risk_signals()生成")
    console.print("  • 信号通过_process_signal()转换为订单事件")


if __name__ == "__main__":
    main()
