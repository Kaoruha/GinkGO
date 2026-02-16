# Upstream: ginkgo.trading.optimization, ginkgo.trading.strategies
# Downstream: CLI用户
# Role: 参数优化CLI - 提供网格搜索、遗传算法、贝叶斯优化等命令

"""
Ginkgo Optimization CLI - 参数优化命令行接口

提供策略参数优化命令：
- ginkgo optimize grid         # 网格搜索
- ginkgo optimize genetic      # 遗传算法
- ginkgo optimize bayesian     # 贝叶斯优化
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help=":dart: 参数优化模块 - 网格搜索、遗传算法、贝叶斯优化",
    no_args_is_help=True,
)
console = Console()


@app.command("grid")
def grid_search(
    strategy: str = typer.Argument(..., help="策略名称或文件路径"),
    params: List[str] = typer.Option(..., "--param", "-p", help="参数范围 (name:min:max:step 或 name:val1,val2,val3)"),
    start: str = typer.Option(None, "--start", "-s", help="回测开始日期 (YYYYMMDD)"),
    end: str = typer.Option(None, "--end", "-e", help="回测结束日期 (YYYYMMDD)"),
    metric: str = typer.Option("sharpe", "--metric", "-m", help="优化目标 (sharpe/return/drawdown)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """
    :grid: 网格搜索优化

    Examples:
      ginkgo optimize grid MyStrategy -p fast:5:20:5 -p slow:20:60:10
      ginkgo optimize grid strategy.py -p period:5,10,15,20 -m return
    """
    console.print(f":grid: 网格搜索: {strategy}")
    console.print(f"   参数: {params}")
    console.print(f"   目标: {metric}")
    console.print("[yellow]TODO: 实现 GridSearchOptimizer 集成[/yellow]")


@app.command("genetic")
def genetic_optimize(
    strategy: str = typer.Argument(..., help="策略名称或文件路径"),
    params: List[str] = typer.Option(..., "--param", "-p", help="参数范围 (name:min:max)"),
    population: int = typer.Option(50, "--population", help="种群大小"),
    generations: int = typer.Option(20, "--generations", "-g", help="迭代次数"),
    mutation: float = typer.Option(0.1, "--mutation", help="变异率"),
    start: str = typer.Option(None, "--start", "-s", help="回测开始日期 (YYYYMMDD)"),
    end: str = typer.Option(None, "--end", "-e", help="回测结束日期 (YYYYMMDD)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """
    :dna: 遗传算法优化

    Examples:
      ginkgo optimize genetic MyStrategy -p fast:5:50 -p slow:20:100 --population 100 -g 50
    """
    console.print(f":dna: 遗传算法优化: {strategy}")
    console.print(f"   参数: {params}, 种群: {population}, 代数: {generations}")
    console.print("[yellow]TODO: 实现 GeneticOptimizer 集成[/yellow]")


@app.command("bayesian")
def bayesian_optimize(
    strategy: str = typer.Argument(..., help="策略名称或文件路径"),
    params: List[str] = typer.Option(..., "--param", "-p", help="参数范围 (name:min:max)"),
    iterations: int = typer.Option(50, "--iterations", "-i", help="迭代次数"),
    start: str = typer.Option(None, "--start", "-s", help="回测开始日期 (YYYYMMDD)"),
    end: str = typer.Option(None, "--end", "-e", help="回测结束日期 (YYYYMMDD)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """
    :brain: 贝叶斯优化

    Examples:
      ginkgo optimize bayesian MyStrategy -p fast:5:50 -p slow:20:100 -i 100
    """
    console.print(f":brain: 贝叶斯优化: {strategy}")
    console.print(f"   参数: {params}, 迭代次数: {iterations}")
    console.print("[yellow]TODO: 实现 BayesianOptimizer 集成[/yellow]")


if __name__ == "__main__":
    app()
