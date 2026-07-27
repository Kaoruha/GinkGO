#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Upstream: ginkgo CLI (main.py 注册)
# Downstream: FeatureContainer.factor_service (features 层, 增量物化),
#             DataContainer.factor_crud (data 层, 已物化 entity 查询),
#             factor_registry (库/因子元数据)
# Role: ginkgo factor 子命令 — 因子库物化与管理 (#6792)

"""
Factor CLI — 因子物化与管理命令。

命令:
  ginkgo factor materialize  物化指定库的因子到 MFactor (增量: 二次运行写入为零)
  ginkgo factor libraries    列出已注册因子库 (供 materialize 选 --library)
"""

import typer
from typing import List
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help=":chart_with_upwards_trend: Factor materialization & management (#6792)",
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console(emoji=True, legacy_windows=False)


def _get_factor_service():
    """延迟拿 features 层 FactorService (注入 FactorEngine/ExpressionEngine, 支持增量物化)。

    测试可 monkeypatch 此函数注入 mock service, 避免触发 container/DB 初始化。
    """
    from ginkgo.features.containers import feature_container
    return feature_container.factor_service()


def _get_factor_crud():
    """延迟拿 data 层 FactorCRUD (增量物化决策: 查已物化 entity 集合)。

    测试可 monkeypatch 此函数注入 mock crud。
    """
    from ginkgo.data.containers import container
    return container.factor_crud()


def _get_factor_analysis_service():
    """延迟拿 FactorAnalysisService (因子效果分析编排器, #6794)。

    纯编排器无构造依赖, 直接 new。测试可 monkeypatch。
    """
    from ginkgo.features.services.factor_analysis_service import FactorAnalysisService
    return FactorAnalysisService()


def _get_bar_service():
    """延迟拿 data 层 BarService (读 bars 算前瞻收益, #6794)。"""
    from ginkgo.data.containers import container
    return container.bar_service()


@app.command()
def materialize(
    library: str = typer.Argument(..., help="因子库名 (如 alpha158), 见 `ginkgo factor libraries`"),
    start: str = typer.Option(..., "--start", "-s", help="起始日期 YYYY-MM-DD"),
    end: str = typer.Option(..., "--end", "-e", help="截止日期 YYYY-MM-DD"),
    entities: List[str] = typer.Option(
        None, "--entity", "-c",
        help="实体代码 (可多次指定, 如 -c 000001.SZ -c 000002.SZ)",
    ),
    entity_type: str = typer.Option("stock", "--entity-type", "-t", help="实体类型 (默认 stock)"),
    full: bool = typer.Option(
        False, "--full",
        help="全量重算 (忽略已物化; 默认增量跳过已物化 entity)",
    ),
):
    """物化指定库的因子到 MFactor 表。

    默认增量: 跳过 [start, end] 内已对该库因子有数据的 entity (二次运行写入为零, #6792)。
    --full 强制全量重算 (不查已物化, 全部重算)。
    """
    from ginkgo.enums import ENTITY_TYPES

    if not entities:
        console.print("[red]✗ 必须指定至少一个 --entity (如 -c 000001.SZ)[/]")
        raise typer.Exit(1)

    et = ENTITY_TYPES.enum_convert(entity_type)
    if et is None:
        console.print(f"[red]✗ 未知 entity_type: {entity_type}[/]")
        raise typer.Exit(1)

    svc = _get_factor_service()
    factor_crud = _get_factor_crud()

    mode = "全量" if full else "增量"
    console.print(
        f"[cyan]▶ 物化库 {library}[/]: {len(entities)} entity, "
        f"{start} ~ {end}, entity_type={entity_type}, 模式={mode}"
    )

    result = svc.calculate_factors_by_library(
        library_name=library,
        entity_ids=entities,
        start_date=start,
        end_date=end,
        entity_type=et,
        incremental=not full,
        factor_crud=factor_crud,
    )

    if not result.success:
        console.print(f"[red]✗ 物化失败: {result.error}[/]")
        raise typer.Exit(1)

    data = result.data or {}
    skipped = data.get("skipped_entities", 0)
    table = Table(title=f"因子物化结果 — {library}", show_header=True, header_style="bold cyan")
    table.add_column("指标", style="cyan", no_wrap=True)
    table.add_column("值", style="green")
    table.add_row("因子数", str(data.get("factor_count", 0)))
    table.add_row("已处理 entity", str(data.get("processed_entities", 0)))
    table.add_row("跳过 (已物化)", str(skipped))
    table.add_row("存储因子记录", str(data.get("total_factors_stored", 0)))
    console.print(table)

    if skipped > 0 and not full:
        console.print(f"[dim]增量跳过 {skipped} 个已物化 entity (用 --full 强制重算)[/]")
    elif full:
        console.print("[dim]--full: 忽略已物化, 全部重算[/]")

    console.print("[green]✓ 物化完成[/]")


@app.command(name="analyze")
def analyze(
    name: str = typer.Argument(..., help="因子名 (已物化的 MFactor.factor_name)"),
    start: str = typer.Option(..., "--start", "-s", help="起始日期 YYYY-MM-DD"),
    end: str = typer.Option(..., "--end", "-e", help="截止日期 YYYY-MM-DD (PIT: 前瞻收益在此截断)"),
    entities: List[str] = typer.Option(
        None, "--entity", "-c",
        help="实体代码 (可多次, 如 -c 000001.SZ -c 000002.SZ)",
    ),
    entity_type: str = typer.Option("stock", "--entity-type", "-t", help="实体类型 (默认 stock)"),
    fmt: str = typer.Option("table", "--format", help="输出格式: table | csv | json"),
    periods: List[int] = typer.Option(
        [1, 5, 10, 20], "--period", help="前瞻收益周期 (日, 可多次)",
    ),
    n_groups: int = typer.Option(5, "--n-groups", help="分层数"),
):
    """分析已物化因子的效果: IC/IR/decay/turnover/分层 (#6794)。

    PIT: 前瞻收益按 --end 截断 (realized_cutoff), 防前瞻泄漏 (验收2)。
    需先 `ginkgo factor materialize` 物化因子 (验收4: 已物化因子跑通非空报告)。
    """
    if not entities:
        console.print("[red]✗ 必须指定至少一个 --entity (如 -c 000001.SZ)[/]")
        raise typer.Exit(1)
    if fmt not in ("table", "csv", "json"):
        console.print(f"[red]✗ --format 仅支持 table/csv/json, 得到 {fmt}[/]")
        raise typer.Exit(1)

    from ginkgo.enums import ENTITY_TYPES
    et = ENTITY_TYPES.enum_convert(entity_type)
    if et is None:
        console.print(f"[red]✗ 未知 entity_type: {entity_type}[/]")
        raise typer.Exit(1)

    svc = _get_factor_analysis_service()
    factor_crud = _get_factor_crud()
    bar_service = _get_bar_service()

    console.print(
        f"[cyan]▶ 分析因子 {name}[/]: {len(entities)} entity, {start} ~ {end}, "
        f"periods={list(periods)}, n_groups={n_groups}, format={fmt}"
    )

    result = svc.analyze_factor(
        factor_name=name,
        entity_ids=entities,
        start_date=start,
        end_date=end,
        factor_crud=factor_crud,
        bar_service=bar_service,
        entity_type=et,
        periods=list(periods),
        n_groups=n_groups,
    )

    if not result.success:
        console.print(f"[red]✗ 分析失败: {result.error}[/]")
        raise typer.Exit(1)

    data = result.data or {}
    if fmt == "json":
        import json
        console.print_json(json.dumps(data, default=str, ensure_ascii=False))
    elif fmt == "csv":
        _print_analysis_csv(data)
    else:
        _print_analysis_table(data, name)

    console.print("[green]✓ 分析完成[/]")


def _print_analysis_table(data: dict, factor_name: str):
    """表格输出 IC/IR/decay/turnover/分位 (验收3 可读输出)。"""
    table = Table(title=f"因子效果分析 — {factor_name}", show_header=True, header_style="bold cyan")
    table.add_column("指标", style="cyan", no_wrap=True)
    table.add_column("值", style="green")
    table.add_row("IC (primary)", _fmt(data.get("ic")))
    table.add_row("IR (primary)", _fmt(data.get("ir")))
    table.add_row("turnover", _fmt(data.get("turnover")))
    table.add_row("分层多空 spread", _fmt(data.get("layering_spread")))
    ic_all = data.get("ic_by_period", {}) or {}
    if ic_all:
        table.add_row("IC (各周期)", ", ".join(f"{k}d={_fmt(v)}" for k, v in ic_all.items()))
    decay = data.get("decay", {}) or {}
    if decay.get("half_life") is not None:
        table.add_row("decay half_life", _fmt(decay.get("half_life")))
    console.print(table)


def _print_analysis_csv(data: dict):
    """CSV 输出 (验收3 结构化, 供管道消费)。"""
    console.print("metric,value")
    core_metrics = [
        ("ic_primary", data.get("ic")),
        ("ir_primary", data.get("ir")),
        ("turnover", data.get("turnover")),
        ("layering_spread", data.get("layering_spread")),
    ]
    for k, v in core_metrics:
        console.print(f"{k},{_fmt(v)}")
    for k, v in (data.get("ic_by_period") or {}).items():
        console.print(f"ic_{k}d,{_fmt(v)}")


def _fmt(v):
    """数值格式化: None→N/A, float→round 6, 其他 str。"""
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:.6f}"
    return str(v)


@app.command(name="libraries")
def list_libraries():
    """列出已注册的因子库及其因子数 (供 materialize 选 --library)。"""
    svc = _get_factor_service()
    registry = svc.factor_registry
    libs = registry.get_registered_libraries()
    if not libs:
        console.print("[yellow]未发现任何因子库[/]")
        return

    table = Table(title="已注册因子库", show_header=True, header_style="bold cyan")
    table.add_column("库名", style="cyan")
    table.add_column("因子数", style="green", justify="right")
    for name in sorted(libs.keys()):
        factors = registry.get_factors_by_library(name)
        table.add_row(name, str(len(factors)))
    console.print(table)


if __name__ == "__main__":
    app()
