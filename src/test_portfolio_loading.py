#!/usr/bin/env python3
"""
测试 Portfolio 加载流程

逐步验证 ExecutionNode.load_portfolio() 方法的每个步骤
"""

import sys
sys.path.insert(0, '/home/kaoru/Ginkgo/src')

from ginkgo.data.containers import container
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def test_step_1_get_portfolio_from_db():
    """步骤1: 从数据库获取 Portfolio"""
    console.print("\n[bold cyan]步骤1: 从数据库获取 Portfolio[/bold cyan]")

    try:
        portfolio_service = container.portfolio_service()

        # 获取所有 live portfolios
        result = portfolio_service.get(is_live=True)

        if not result.is_success():
            console.print(f"[red]✗ 失败: {result.error}[/red]")
            return None

        portfolios = result.data
        if not portfolios:
            console.print("[yellow]⚠ 没有找到 is_live=True 的 portfolio[/yellow]")
            return None

        portfolio = portfolios[0]
        console.print(f"[green]✓ 找到 Portfolio:[/green]")
        console.print(f"  UUID: {portfolio.uuid}")
        console.print(f"  Name: {portfolio.name}")
        console.print(f"  is_live: {portfolio.is_live}")

        # 检查所有属性
        console.print(f"\n[bold]Portfolio 属性:[/bold]")
        for attr in dir(portfolio):
            if not attr.startswith('_'):
                value = getattr(portfolio, attr, None)
                if not callable(value):
                    console.print(f"  {attr}: {value}")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None

def test_step_2_create_portfolio_live(portfolio_model):
    """步骤2: 创建 PortfolioLive 实例"""
    console.print("\n[bold cyan]步骤2: 创建 PortfolioLive 实例[/bold cyan]")

    try:
        from ginkgo.trading.portfolios.portfolio_live import PortfolioLive

        portfolio = PortfolioLive(
            portfolio_id=portfolio_model.uuid,
            name=portfolio_model.name
        )

        console.print(f"[green]✓ PortfolioLive 创建成功[/green]")

        # 检查 PortfolioLive 的属性
        console.print(f"\n[bold]PortfolioLive 属性:[/bold]")
        attrs_to_check = ['cash', 'frozen_cash', 'initial_capital', 'portfolio_id', 'name']
        for attr in attrs_to_check:
            if hasattr(portfolio, attr):
                value = getattr(portfolio, attr)
                console.print(f"  [green]✓[/green] {attr}: {value}")
            else:
                console.print(f"  [red]✗[/red] {attr}: [dim]不存在[/dim]")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None

def test_step_3_add_cash(portfolio, portfolio_model):
    """步骤3: 添加初始资金"""
    console.print("\n[bold cyan]步骤3: 添加初始资金[/bold cyan]")

    try:
        console.print(f"  初始资金: {portfolio_model.initial_capital}")
        portfolio.add_cash(portfolio_model.initial_capital)
        console.print(f"[green]✓ 添加资金成功[/green]")

        # 检查 cash 属性
        console.print(f"\n[bold]资金状态:[/bold]")
        console.print(f"  cash: {portfolio.cash}")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None

def test_step_4_add_missing_attributes(portfolio, portfolio_model):
    """步骤4: 添加缺失的属性"""
    console.print("\n[bold cyan]步骤4: 添加缺失的属性[/bold cyan]")

    try:
        # 添加 initial_capital
        if not hasattr(portfolio, 'initial_capital'):
            portfolio.initial_capital = portfolio_model.initial_capital
            console.print(f"  [green]✓[/green] 添加 initial_capital: {portfolio_model.initial_capital}")

        # 添加 frozen_cash（如果不存在）
        if not hasattr(portfolio, 'frozen_cash'):
            portfolio.frozen_cash = 0.0
            console.print(f"  [green]✓[/green] 添加 frozen_cash: 0.0")

        console.print(f"\n[bold]完整属性列表:[/bold]")
        attrs = ['portfolio_id', 'name', 'cash', 'frozen_cash', 'initial_capital']
        for attr in attrs:
            if hasattr(portfolio, attr):
                value = getattr(portfolio, attr)
                console.print(f"  [green]✓[/green] {attr}: {value}")

        return portfolio

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return None

def test_step_5_verify_portfolio(portfolio):
    """步骤5: 验证 Portfolio 对象完整性"""
    console.print("\n[bold cyan]步骤5: 验证 Portfolio 对象[/bold cyan]")

    try:
        # 检查所有必需属性
        required_attrs = {
            'portfolio_id': str,
            'name': str,
            'cash': (int, float),
            'frozen_cash': (int, float),
            'initial_capital': (int, float)
        }

        all_ok = True
        for attr, expected_type in required_attrs.items():
            if not hasattr(portfolio, attr):
                console.print(f"  [red]✗[/red] {attr}: [dim]缺失[/dim]")
                all_ok = False
            else:
                value = getattr(portfolio, attr)
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        console.print(f"  [red]✗[/red] {attr}: {type(value)} (期望: {expected_type})")
                        all_ok = False
                    else:
                        console.print(f"  [green]✓[/green] {attr}: {value}")
                else:
                    if not isinstance(value, expected_type):
                        console.print(f"  [red]✗[/red] {attr}: {type(value)} (期望: {expected_type})")
                        all_ok = False
                    else:
                        console.print(f"  [green]✓[/green] {attr}: {value}")

        if all_ok:
            console.print("\n[bold green]✓ Portfolio 对象完整[/bold green]")
        else:
            console.print("\n[bold red]✗ Portfolio 对象不完整[/bold red]")

        return all_ok

    except Exception as e:
        console.print(f"[red]✗ 异常: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

def main():
    console.print(Panel.fit(
        "[bold cyan]Portfolio 加载测试[/bold cyan]\n"
        "逐步验证 ExecutionNode.load_portfolio() 流程",
        title="测试"
    ))

    # 步骤1: 从数据库获取
    portfolio_model = test_step_1_get_portfolio_from_db()
    if not portfolio_model:
        console.print("\n[red]✗ 测试失败: 无法从数据库获取 Portfolio[/red]")
        return

    # 步骤2: 创建 PortfolioLive
    portfolio = test_step_2_create_portfolio_live(portfolio_model)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法创建 PortfolioLive[/red]")
        return

    # 步骤3: 添加资金
    portfolio = test_step_3_add_cash(portfolio, portfolio_model)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法添加资金[/red]")
        return

    # 步骤4: 添加缺失属性
    portfolio = test_step_4_add_missing_attributes(portfolio, portfolio_model)
    if not portfolio:
        console.print("\n[red]✗ 测试失败: 无法添加属性[/red]")
        return

    # 步骤5: 验证
    success = test_step_5_verify_portfolio(portfolio)

    console.print("\n" + "="*70)
    if success:
        console.print("[bold green]✓ 所有测试通过[/bold green]")
        console.print("[bold]解决方案:[/bold] 在 load_portfolio() 中添加缺失的属性")
    else:
        console.print("[bold red]✗ 测试失败[/bold red]")

if __name__ == "__main__":
    main()
