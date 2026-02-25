# Upstream: ginkgo.trading.comparison, ginkgo.data.cruds
# Downstream: CLI用户
# Role: 回测对比CLI - 提供回测结果对比命令

"""
Ginkgo Comparison CLI - 回测对比命令行接口

提供回测结果对比命令：
- ginkgo compare <ids...>      # 对比多个回测结果
- ginkgo compare top --n 5     # 显示前 5 个最佳表现
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help=":balance_scale: 回测对比模块 - 对比多个回测结果",
    no_args_is_help=True,
)
console = Console()


@app.command("run")
def compare_backtests(
    backtest_ids: List[str] = typer.Argument(..., help="回测 ID 列表"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件路径 (html/json/csv)"),
    normalize: bool = typer.Option(True, "--normalize/--no-normalize", help="是否归一化净值曲线"),
    metrics: Optional[str] = typer.Option(None, "--metrics", "-m", help="指定对比指标 (逗号分隔)"),
):
    """
    :balance_scale: 对比多个回测结果

    Examples:
      ginkgo compare run bt_001 bt_002 bt_003
      ginkgo compare run bt_001 bt_002 --output report.html
      ginkgo compare run bt_001 bt_002 --metrics total_return,sharpe_ratio
    """
    from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

    console.print(f":balance_scale: 对比回测: {', '.join(backtest_ids)}")

    comparator = BacktestComparator()
    result = comparator.compare(backtest_ids)

    # 显示对比表格
    _display_comparison_table(result, metrics)

    # 输出文件
    if output:
        _save_result(result, output)
        console.print(f":file_folder: 结果已保存到: {output}")


@app.command("top")
def show_top_performers(
    n: int = typer.Option(5, "--n", "-n", help="显示前 N 个"),
    metric: str = typer.Option("total_return", "--metric", "-m", help="排序指标"),
    backtest_ids: Optional[List[str]] = typer.Argument(None, help="回测 ID 列表 (可选)"),
):
    """
    :trophy: 显示最佳表现

    Examples:
      ginkgo compare top --n 5 --metric sharpe_ratio
      ginkgo compare top bt_001 bt_002 bt_003 --metric total_return
    """
    from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

    console.print(f":trophy: 按指标 {metric} 排名前 {n}")

    # TODO: 从数据库获取所有回测
    if not backtest_ids:
        console.print("[yellow]请提供回测 ID 列表[/yellow]")
        return

    comparator = BacktestComparator()
    result = comparator.compare(list(backtest_ids))

    ranking = result.get_ranking(metric)[:n]

    table = Table(title=f"Top {n} by {metric}")
    table.add_column("排名", style="cyan")
    table.add_column("回测 ID", style="green")
    table.add_column(metric, style="yellow")

    for i, bt_id in enumerate(ranking, 1):
        value = result.get_metric(metric, bt_id)
        table.add_row(str(i), bt_id, f"{float(value):.4f}" if value else "N/A")

    console.print(table)


@app.command("net-values")
def show_net_values(
    backtest_ids: List[str] = typer.Argument(..., help="回测 ID 列表"),
    normalized: bool = typer.Option(True, "--normalize/--no-normalize", help="是否归一化"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="输出文件 (csv)"),
):
    """
    :chart_with_upwards_trend: 显示净值曲线

    Examples:
      ginkgo compare net-values bt_001 bt_002
      ginkgo compare net-values bt_001 --no-normalize --output net_values.csv
    """
    from ginkgo.trading.comparison.backtest_comparator import BacktestComparator

    comparator = BacktestComparator()
    net_values = comparator.get_net_values(backtest_ids, normalized=normalized)

    if not any(net_values.values()):
        console.print("[yellow]没有可用的净值曲线数据[/yellow]")
        return

    # 显示概览
    table = Table(title="净值曲线概览")
    table.add_column("回测 ID", style="cyan")
    table.add_column("数据点数", style="green")
    table.add_column("起点", style="yellow")
    table.add_column("终点", style="yellow")

    for bt_id, curve in net_values.items():
        if curve:
            table.add_row(
                bt_id,
                str(len(curve)),
                f"{float(curve[0][1]):.4f}",
                f"{float(curve[-1][1]):.4f}",
            )

    console.print(table)

    # 输出文件
    if output and output.endswith(".csv"):
        _save_net_values_csv(net_values, output)
        console.print(f":file_folder: 净值曲线已保存到: {output}")


def _display_comparison_table(result, metrics: Optional[str] = None):
    """显示对比表格"""
    table = Table(title="回测对比结果")
    table.add_column("指标", style="cyan")

    # 添加回测 ID 列
    for bt_id in result.backtest_ids:
        table.add_column(bt_id, style="green")

    # 确定要显示的指标
    if metrics:
        metric_list = [m.strip() for m in metrics.split(",")]
    else:
        metric_list = list(result.metrics_table.keys())

    # 填充表格
    for metric in metric_list:
        if metric not in result.metrics_table:
            continue

        row = [metric]
        values = result.metrics_table[metric]
        best_id = result.best_performers.get(metric)

        for bt_id in result.backtest_ids:
            value = values.get(bt_id)
            if value is not None:
                cell = f"{float(value):.4f}"
                if bt_id == best_id:
                    cell = f"[bold green]{cell}[/bold green]"
            else:
                cell = "N/A"
            row.append(cell)

        table.add_row(*row)

    console.print(table)


def _save_result(result, output: str):
    """保存对比结果"""
    if output.endswith(".html"):
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>回测对比报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .comparison-table {{ border-collapse: collapse; width: 100%; }}
        .comparison-table th, .comparison-table td {{
            border: 1px solid #ddd; padding: 8px; text-align: center;
        }}
        .comparison-table .best {{ background-color: #d4edda; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>回测对比报告</h1>
    <p>生成时间: {result.created_at}</p>
    {result.to_html_table()}
</body>
</html>"""
        with open(output, "w") as f:
            f.write(html_content)
    elif output.endswith(".json"):
        import json
        with open(output, "w") as f:
            json.dump(result.to_dict(), f, indent=2, default=str)
    else:
        # 默认保存为文本
        with open(output, "w") as f:
            f.write(str(result.to_dict()))


def _save_net_values_csv(net_values: dict, output: str):
    """保存净值曲线为 CSV"""
    import csv

    # 收集所有日期
    all_dates = set()
    for curve in net_values.values():
        for date, _ in curve:
            all_dates.add(date)

    all_dates = sorted(all_dates)

    with open(output, "w", newline="") as f:
        writer = csv.writer(f)
        # 表头
        header = ["date"] + list(net_values.keys())
        writer.writerow(header)

        # 数据
        for date in all_dates:
            row = [date]
            for bt_id, curve in net_values.items():
                value = next((v for d, v in curve if d == date), "")
                row.append(str(float(value)) if value else "")
            writer.writerow(row)


if __name__ == "__main__":
    app()
