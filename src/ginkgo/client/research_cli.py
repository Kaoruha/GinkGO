# Upstream: ginkgo.data.cruds, ginkgo.research
# Downstream: CLI用户
# Role: 因子研究CLI - 提供IC分析、分层、正交化等命令

"""
Ginkgo Research CLI - 因子研究命令行接口

提供因子研究和分析命令：
- ginkgo research ic           # IC 分析
- ginkgo research layering     # 因子分层
- ginkgo research orthogonalize # 因子正交化
- ginkgo research compare      # 因子对比
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help=":chart_with_upwards_trend: 因子研究模块 - IC分析、分层、正交化等",
    no_args_is_help=True,
)
console = Console()


@app.command("ic")
def analyze_ic(
    factor: str = typer.Argument(..., help="因子名称或数据文件路径"),
    start: str = typer.Option(None, "--start", "-s", help="开始日期 (YYYYMMDD)"),
    end: str = typer.Option(None, "--end", "-e", help="结束日期 (YYYYMMDD)"),
    code: str = typer.Option(None, "--code", "-c", help="股票代码 (可选，默认全市场)"),
    method: str = typer.Option("spearman", "--method", "-m", help="IC计算方法 (spearman/pearson)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """
    :bar_chart: 计算因子 IC (Information Coefficient)

    Examples:
      ginkgo research ic momentum --start 20230101 --end 20231231
      ginkgo research ic factor.csv -m pearman -o ic_result.json
    """
    console.print(f":chart_with_upwards_trend: 计算 IC: {factor}")
    console.print(f"   方法: {method}, 日期范围: {start} ~ {end}")
    console.print("[yellow]TODO: 实现 ICAnalyzer 集成[/yellow]")


@app.command("layering")
def factor_layering(
    factor: str = typer.Argument(..., help="因子名称或数据文件路径"),
    n_groups: int = typer.Option(5, "--groups", "-g", help="分组数量"),
    start: str = typer.Option(None, "--start", "-s", help="开始日期 (YYYYMMDD)"),
    end: str = typer.Option(None, "--end", "-e", help="结束日期 (YYYYMMDD)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """
    :chart: 因子分层分析

    Examples:
      ginkgo research layering momentum --groups 10
      ginkgo research layering factor.csv -g 5 -o layering.json
    """
    console.print(f":chart: 因子分层: {factor}")
    console.print(f"   分组数: {n_groups}, 日期范围: {start} ~ {end}")
    console.print("[yellow]TODO: 实现 FactorLayering 集成[/yellow]")


@app.command("orthogonalize")
def orthogonalize(
    factors: str = typer.Argument(..., help="因子列表 (逗号分隔)"),
    method: str = typer.Option("pca", "--method", "-m", help="正交化方法 (gram_schmidt/pca/residualize)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径"),
):
    """
    :recycle: 因子正交化

    Examples:
      ginkgo research orthogonalize factor1,factor2,factor3 -m pca
      ginkgo research orthogonalize factors.csv -m gram_schmidt
    """
    factor_list = [f.strip() for f in factors.split(",")]
    console.print(f":recycle: 因子正交化: {factor_list}")
    console.print(f"   方法: {method}")
    console.print("[yellow]TODO: 实现 FactorOrthogonalizer 集成[/yellow]")


@app.command("compare")
def compare_factors(
    factors: str = typer.Argument(..., help="因子列表 (逗号分隔)"),
    metric: str = typer.Option("ic", "--metric", "-m", help="对比指标 (ic/return/turnover)"),
    start: str = typer.Option(None, "--start", "-s", help="开始日期 (YYYYMMDD)"),
    end: str = typer.Option(None, "--end", "-e", help="结束日期 (YYYYMMDD)"),
):
    """
    :balance_scale: 因子对比分析

    Examples:
      ginkgo research compare factor1,factor2,factor3 -m ic
      ginkgo research compare factors.csv --metric return
    """
    factor_list = [f.strip() for f in factors.split(",")]
    console.print(f":balance_scale: 因子对比: {factor_list}")
    console.print(f"   指标: {metric}")
    console.print("[yellow]TODO: 实现 FactorComparator 集成[/yellow]")


if __name__ == "__main__":
    app()
