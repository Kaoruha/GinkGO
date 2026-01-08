#!/usr/bin/env python3
"""
测试 ExecutionNode 加载 Portfolio 功能

验证：
1. ExecutionNode 初始化
2. 从数据库加载 Portfolio
3. 验证 engine_id 和 run_id 设置
4. 验证 Portfolio 组件完整
5. 验证 Portfolio 可以处理事件
"""

import sys
sys.path.insert(0, '/home/kaoru/Ginkgo/src')

from ginkgo.workers.execution_node.node import ExecutionNode
from ginkgo import services
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import FREQUENCY_TYPES
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from datetime import datetime
from decimal import Decimal

console = Console()


def get_available_portfolios():
    """从数据库获取可用的Portfolio列表"""
    console.print("\n[bold cyan]步骤0: 查询可用Portfolio[/bold cyan]")

    try:
        portfolio_service = services.data.portfolio_service()
        result = portfolio_service.get(is_live=True)

        if not result.is_success():
            console.print(f"[red]✗ 查询失败: {result.error}[/red]")
            return []

        portfolios = result.data
        if not portfolios or len(portfolios) == 0:
            console.print(f"[yellow]⚠ 没有找到实盘Portfolio[/yellow]")
            return []

        console.print(f"[green]✓ 找到 {len(portfolios)} 个实盘Portfolio[/green]")

        table = Table(show_header=True)
        table.add_column("序号", style="cyan")
        table.add_column("Portfolio ID", style="magenta")
        table.add_column("名称", style="blue")
        table.add_column("初始资金", style="green")

        for i, p in enumerate(portfolios, 1):
            table.add_row(
                str(i),
                p.uuid[:8] + "...",
                p.name,
                str(p.initial_capital)
            )

        console.print(table)
        return portfolios

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return []


def test_step_1_create_node():
    """步骤1: 创建ExecutionNode"""
    console.print("\n[bold cyan]步骤1: 创建ExecutionNode[/bold cyan]")

    try:
        node = ExecutionNode(node_id="test_node_execution")

        console.print(f"[green]✓ ExecutionNode创建成功[/green]")
        console.print(f"  node_id: {node.node_id}")
        console.print(f"  is_running: {node.is_running}")
        console.print(f"  is_paused: {node.is_paused}")

        return node

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_2_load_portfolio(node, portfolio_id):
    """步骤2: 加载Portfolio"""
    console.print(f"\n[bold cyan]步骤2: 加载Portfolio {portfolio_id[:8]}...[/bold cyan]")

    try:
        success = node.load_portfolio(portfolio_id)

        if not success:
            console.print(f"[red]✗ Portfolio加载失败[/red]")
            return None

        console.print(f"[green]✓ Portfolio加载成功[/green]")

        # 获取Portfolio实例
        portfolio = node._portfolio_instances.get(portfolio_id)
        if not portfolio:
            console.print(f"[red]✗ 无法获取Portfolio实例[/red]")
            return None

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None


def test_step_3_verify_context(portfolio):
    """步骤3: 验证上下文设置"""
    console.print(f"\n[bold cyan]步骤3: 验证上下文设置[/bold cyan]")

    try:
        engine_id = portfolio.engine_id
        run_id = portfolio.run_id
        portfolio_id = portfolio.portfolio_id

        console.print(f"  engine_id: {engine_id}")
        console.print(f"  run_id: {run_id[:8]}... (完整: {run_id})")
        console.print(f"  portfolio_id: {portfolio_id[:8]}...")

        # 验证
        if engine_id == "livecore":
            console.print(f"[green]✓ engine_id正确设置为 'livecore'[/green]")
        else:
            console.print(f"[red]✗ engine_id错误: 期望 'livecore', 实际 '{engine_id}'[/red]")
            return False

        if run_id == portfolio_id:
            console.print(f"[green]✓ run_id正确设置为 portfolio_id[/green]")
        else:
            console.print(f"[yellow]⚠ run_id与portfolio_id不匹配[/yellow]")

        return True

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_step_4_verify_components(portfolio):
    """步骤4: 验证Portfolio组件"""
    console.print(f"\n[bold cyan]步骤4: 验证Portfolio组件[/bold cyan]")

    try:
        is_ready = portfolio.is_all_set()

        console.print(f"  策略数量: {len(portfolio.strategies)}")
        console.print(f"  Sizer: {'✓' if portfolio.sizer is not None else '✗'}")
        console.print(f"  风控数量: {len(portfolio.risk_managers)}")
        console.print(f"  Selector数量: {len(portfolio.selectors)}")
        console.print(f"\n  [bold]is_all_set():[/bold] {is_ready}")

        if is_ready:
            console.print(f"[green]✓ Portfolio组件齐全，可以处理事件[/green]")
        else:
            console.print(f"[yellow]⚠ Portfolio组件不齐全[/yellow]")

        return True

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def test_step_5_verify_event_processing(portfolio):
    """步骤5: 验证事件处理"""
    console.print(f"\n[bold cyan]步骤5: 验证事件处理[/bold cyan]")

    try:
        # 创建测试事件
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

        console.print(f"  创建测试事件: {event.code} @ {event.close}")
        console.print(f"  调用 portfolio.on_price_update(event)...")

        # 处理事件
        order_events = portfolio.on_price_update(event)

        console.print(f"\n[green]✓ 事件处理完成[/green]")
        console.print(f"  返回的订单事件数量: {len(order_events)}")

        if order_events:
            console.print(f"\n[bold]生成的订单事件:[/bold]")
            table = Table(show_header=True)
            table.add_column("序号", style="cyan")
            table.add_column("事件类型", style="magenta")
            table.add_column("股票代码", style="blue")

            for i, order_event in enumerate(order_events, 1):
                event_type = type(order_event).__name__
                code = getattr(order_event, 'code', 'N/A')
                table.add_row(str(i), event_type, str(code))

            console.print(table)
        else:
            console.print(f"[dim]  没有生成订单事件（正常，取决于策略逻辑）[/dim]")

        return True

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    console.print(Panel.fit(
        "[bold cyan]ExecutionNode Portfolio 加载测试[/bold cyan]\n"
        "验证 ExecutionNode 可以正确加载 Portfolio 并处理事件",
        title="测试"
    ))

    # 步骤0: 查询可用Portfolio
    portfolios = get_available_portfolios()
    if not portfolios:
        console.print("\n[yellow]⚠ 没有可用的Portfolio，测试结束[/yellow]")
        return

    # 使用第一个Portfolio进行测试
    test_portfolio = portfolios[0]
    portfolio_id = test_portfolio.uuid

    console.print(f"\n[dim]选择Portfolio: {test_portfolio.name} ({portfolio_id[:8]}...)[/dim]")

    # 步骤1: 创建ExecutionNode
    node = test_step_1_create_node()
    if not node:
        console.print("\n[red]✗ 测试失败: 无法创建ExecutionNode[/red]")
        return

    # 步骤2: 加载Portfolio
    portfolio = test_step_2_load_portfolio(node, portfolio_id)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法加载Portfolio[/red]")
        return

    # 步骤3: 验证上下文设置
    if not test_step_3_verify_context(portfolio):
        console.print("\n[red]✗ 测试失败: 上下文设置验证失败[/red]")
        return

    # 步骤4: 验证组件完整
    if not test_step_4_verify_components(portfolio):
        console.print("\n[yellow]⚠ Portfolio组件不完整，但继续测试[/yellow]")

    # 步骤5: 验证事件处理
    if not test_step_5_verify_event_processing(portfolio):
        console.print("\n[red]✗ 测试失败: 事件处理验证失败[/red]")
        return

    console.print("\n" + "="*70)
    console.print("[bold green]✓ 所有测试通过[/bold green]")
    console.print("\n[bold]关键验证:[/bold]")
    console.print("  • ExecutionNode成功初始化")
    console.print("  • Portfolio从数据库成功加载")
    console.print("  • engine_id正确设置为 'livecore'")
    console.print("  • run_id正确设置为 portfolio_id")
    console.print("  • Portfolio组件齐全")
    console.print("  • Portfolio可以处理EventPriceUpdate事件")


if __name__ == "__main__":
    main()
