# Upstream: CLI主入口(ginkgo data命令调用)
# Downstream: 数据服务层(通过container访问StockinfoService/BarService)、KafkaService(后台队列同步)、数据获取模块(fetch_and_update_cn_daybar/fetch_and_update_tick_incremental等)、Rich库(表格/进度条显示)
# Role: 数据管理CLI，提供init初始化、update更新、sync同步、list列表等命令，支持股票信息、K线、Tick等多维度数据管理






"""
Ginkgo Data CLI - 数据管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

app = typer.Typer(help=":page_facing_up: Data management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


def _normalize_stock_code(code: str) -> str:
    """#5920: 归一化 A 股代码到**后缀形式** ``NNNNNN.SH``/``NNNNNN.SZ``（DB stockinfo 存后缀）。

    项目内并存两种记法（见 [[arch_ashare_code_market_prefix_gap]]）：
    - 后缀 ``600000.SH``（stockinfo 表、data get stockinfo -c）
    - 前缀 ``SH600000``（策略/回测组件、position/adjustfactor/tick mapper）

    get（读取侧）应兼容两种，故前缀 → 后缀归一化后查询。已是后缀或无法识别的原样返回
    （读取侧不因格式惩罚用户；无效格式交由下游 ``No bar data`` 提示）。纯字符串变换，
    不依赖 mootdx 首位推断（前缀已带市场标记）。
    """
    import re
    if not code:
        return code
    m = re.fullmatch(r"(SH|SZ)(\d{6})", code)
    if m:
        return f"{m.group(2)}.{m.group(1)}"
    return code


@app.command()
def get(
    data_type: str = typer.Argument(..., help="Data type to get (stockinfo/day/tick/adjustfactor/sources) \\[planned: calendar]"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="Stock code (required for bars/ticks)"),
    start: Optional[str] = typer.Option(None, "--start", "-s", help="Start date (YYYYMMDD)"),
    end: Optional[str] = typer.Option(None, "--end", "-e", help="End date (YYYYMMDD)"),
    page_size: Optional[int] = typer.Option(None, "--page-size", "-p", help="Page size for interactive mode (default: all)"),
    filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter by fuzzy matching (code, industry, name)"),
    market: Optional[str] = typer.Option(None, "--market", help="Filter by market"),
    exchange: Optional[str] = typer.Option(None, "--exchange", help="Filter by exchange"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :inbox_tray: Get data from database.
    """
    try:
        if data_type == "stockinfo":
            from ginkgo.data.containers import container
            from ginkgo.libs.utils.display import display_dataframe_interactive
            import pandas as pd

            stockinfo_service = container.stockinfo_service()
            # ADR-010：此处消费 DataFrame（后续 iloc/columns/过滤），走 DF 出口
            result = stockinfo_service.get_stockinfos_df(code=code, market=market, exchange=exchange)
            if result.success:
                df = result.data

                # Raw output mode
                if raw:
                    import json
                    raw_data = df.to_dict('records')
                    console.print(json.dumps(raw_data, indent=2, ensure_ascii=False, default=str))
                    return

                # 应用模糊过滤
                if filter:
                    console.print(f":mag: Applying filter: '{filter}'")
                    filter_lower = filter.lower()

                    # 创建过滤条件
                    mask = pd.Series([False] * len(df))

                    # 按代码过滤
                    if 'code' in df.columns:
                        mask |= df['code'].astype(str).str.lower().str.contains(filter_lower, na=False)

                    # 按名称过滤
                    if 'code_name' in df.columns:
                        mask |= df['code_name'].astype(str).str.lower().str.contains(filter_lower, na=False)

                    # 按行业过滤
                    if 'industry' in df.columns:
                        mask |= df['industry'].astype(str).str.lower().str.contains(filter_lower, na=False)

                    df = df[mask]

                    if df.empty:
                        console.print(":memo: No matching records found for the filter.")
                        return

                    console.print(f":white_check_mark: Filter matched {len(df)} records")

                # 配置列显示
                columns_config = {
                    "code": {"display_name": "代码", "style": "cyan", "width": 12},
                    "code_name": {"display_name": "名称", "style": "green", "width": 12},
                    "industry": {"display_name": "行业", "style": "yellow", "width": 10},
                    "market": {"display_name": "市场", "style": "blue", "width": 8, "justify": "center"},
                    "list_date": {"display_name": "上市日期", "style": "dim", "width": 15, "justify": "center"}
                }

                # 数据处理函数
                def format_data_for_display(df_original):
                    df = df_original.copy()

                    # 格式化代码
                    if 'code' in df.columns:
                        df['code'] = df['code'].astype(str)

                    # 格式化名称
                    if 'code_name' in df.columns:
                        df['code_name'] = df['code_name'].astype(str)

                    # 格式化行业
                    if 'industry' in df.columns:
                        df['industry'] = df['industry'].astype(str)

                    # 格式化市场
                    if 'market' in df.columns:
                        df['market'] = df['market'].astype(str)
                        # 提取市场名称（取最后一部分）
                        df['market'] = df['market'].apply(lambda x: str(x).split('.')[-1] if '.' in str(x) else str(x))

                    # 格式化上市日期
                    if 'list_date' in df.columns:
                        df['list_date'] = df['list_date'].astype(str).str[:10]
                        # 确保日期格式为YYYY-MM-DD，去除时间部分
                        df['list_date'] = df['list_date'].apply(lambda x: x[:10] if len(x) > 10 else x)

                    return df

                # 格式化数据
                formatted_df = format_data_for_display(df)

                # 按code排序
                formatted_df = formatted_df.sort_values('code')

                # 如果设置了page_size，使用交互式翻页
                if page_size and page_size > 0:
                    console.print(f":information: Interactive mode enabled (page size: {page_size})")
                    console.print(":information: Single-key navigation: n=next, p=prev, q=quit")

                    # 简化的交互式翻页逻辑
                    from rich.prompt import Prompt

                    current_page = 0
                    total_pages = (len(formatted_df) + page_size - 1) // page_size

                    while True:
                        # 计算当前页数据
                        start_idx = current_page * page_size
                        end_idx = min(start_idx + page_size, len(formatted_df))
                        current_data = formatted_df.iloc[start_idx:end_idx]

                        # 创建Rich表格
                        table = Table(show_header=True, header_style="bold magenta",
                                     title=f":page_facing_up: Stock Information - Page {current_page + 1}/{total_pages} ({start_idx + 1}-{end_idx}/{len(formatted_df)})")

                        # 添加列
                        for col_name, config in columns_config.items():
                            if col_name in current_data.columns:
                                justify = config.get("justify", "left")
                                table.add_column(
                                    config["display_name"],
                                    style=config["style"],
                                    width=config.get("width", None),
                                    justify=justify
                                )

                        # 添加行数据
                        for _, row in current_data.iterrows():
                            row_data = []
                            for col_name in columns_config.keys():
                                if col_name in current_data.columns:
                                    value = str(row.get(col_name, 'N/A'))
                                    # 截断过长的文本
                                    max_length = columns_config[col_name].get("width", 20) - 3
                                    if len(value) > max_length:
                                        value = value[:max_length] + "..."
                                    row_data.append(value)
                            table.add_row(*row_data)

                        # 显示表格
                        console.print(table)
                        console.print(f"\n[dim]Page {current_page + 1}/{total_pages} | Records {start_idx + 1}-{end_idx} of {len(formatted_df)}[/dim]")
                        console.print("[yellow]Options:[/] n=next, p=prev, q=quit, <Enter>=next")

                        # 简化输入处理
                        try:
                            action = Prompt.ask(
                                "[bold cyan]Action[/bold cyan] (n/p/q/Enter)",
                                choices=["n", "p", "q", ""],
                                default="",
                                show_default=False
                            ).strip().lower()

                            if action == 'n' or action == '':
                                # 下一页
                                if current_page < total_pages - 1:
                                    current_page += 1
                                else:
                                    console.print("\n[bold blue]Last page reached[/bold blue]")
                                    break
                            elif action == 'p':
                                # 上一页
                                if current_page > 0:
                                    current_page -= 1
                            elif action == 'q':
                                # 退出
                                console.print("\n[yellow]User quit[/yellow]")
                                break
                        except (KeyboardInterrupt, EOFError):
                            break
                        except Exception:
                            break
                else:
                    # 非交互式模式，显示前50条，按code排序
                    display_df = formatted_df.sort_values('code').head(50)

                    if display_df.empty:
                        console.print(":memo: No stock records found.")
                        return

                    console.print(f":information_source: Showing first {len(display_df)} of {len(formatted_df)} records (sorted by code)")

                    # 创建Rich表格
                    table = Table(show_header=True, header_style="bold magenta", title=f":page_facing_up: Stock Information")

                    # 添加列
                    for col_name, config in columns_config.items():
                        if col_name in display_df.columns:
                            justify = config.get("justify", "left")
                            table.add_column(
                                config["display_name"],
                                style=config["style"],
                                width=config.get("width", None),
                                justify=justify
                            )

                    # 添加行数据
                    for _, row in display_df.iterrows():
                        row_data = []
                        for col_name in columns_config.keys():
                            if col_name in display_df.columns:
                                value = str(row.get(col_name, 'N/A'))
                                # 截断过长的文本
                                max_length = columns_config[col_name].get("width", 20) - 3
                                if len(value) > max_length:
                                    value = value[:max_length] + "..."
                                row_data.append(value)
                        table.add_row(*row_data)

                    console.print(table)
                    console.print(f"\n:information_source: [dim]总记录数: {len(formatted_df)}[/dim]")
            else:
                console.print(f":x: Failed to get stock info: {result.error}")

        elif data_type in ["day", "bars"]:
            if not code:
                console.print(":x: Stock code required for bar data")
                raise typer.Exit(1)

            # #5920: 前缀 SH600000 → 后缀 600000.SH（DB 存后缀），与策略/回测组件格式对齐
            code = _normalize_stock_code(code)

            from datetime import datetime, timedelta
            if not end:
                end = datetime.now().strftime("%Y%m%d")
            if not start:
                start = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

            from ginkgo.data.containers import container
            bar_service = container.bar_service()
            result = bar_service.get_bars_df(code=code, start_date=start, end_date=end)

            if not result.success:
                console.print(f":x: Failed to get bar data: {result.error}")
                raise typer.Exit(1)

            import pandas as pd
            df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

            if df.empty:
                console.print(f":information: No bar data found for {code} ({start}-{end})")
                return

            display_cols = ["code", "timestamp", "open", "high", "low", "close", "volume", "amount"]
            show_cols = [c for c in display_cols if c in df.columns]
            df_display = df[show_cols].copy()
            if "timestamp" in df_display.columns:
                df_display["timestamp"] = df_display["timestamp"].astype(str).str[:10]

            table = Table(title=f"Bar Data: {code} ({start}-{end})", show_lines=False)
            for col in show_cols:
                table.add_column(col, style="cyan")
            for _, row in df_display.iterrows():
                table.add_row(*[str(v) for v in row])
            console.print(table)
            console.print(f":information: {len(df)} records")

        elif data_type == "tick":
            if not code:
                console.print(":x: Stock code required for tick data")
                raise typer.Exit(1)

            from datetime import datetime, timedelta
            if not end:
                end = datetime.now().strftime("%Y%m%d")
            if not start:
                start_date = datetime.now() - timedelta(days=7)
                start = start_date.strftime("%Y%m%d")

            from ginkgo.data.containers import container
            tick_service = container.tick_service()
            result = tick_service.get_ticks_df(code=code, start_date=start, end_date=end)

            if not result.success:
                console.print(f":x: Failed to get tick data: {result.error}")
                raise typer.Exit(1)

            import pandas as pd
            df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

            if df.empty:
                console.print(f":information: No tick data found for {code} ({start}-{end})")
                return

            limit = page_size or 50
            if len(df) > limit:
                console.print(f":information: Showing {limit} of {len(df)} records")
                df = df.tail(limit)

            table = Table(title=f"Tick Data: {code} ({start}-{end})", show_lines=False)
            display_cols = ["code", "timestamp", "price", "volume", "amount", "direction"]
            show_cols = [c for c in display_cols if c in df.columns]
            for col in show_cols:
                table.add_column(col, style="cyan")
            for _, row in df[show_cols].iterrows():
                table.add_row(*[str(v) for v in row])
            console.print(table)

        elif data_type == "adjustfactor":
            if not code:
                console.print(":x: Stock code required for adjustfactor data")
                raise typer.Exit(1)

            # 默认时间范围（对齐 day 分支：end 缺省补 now，start 缺省补 now-365d）
            from datetime import datetime, timedelta
            if not end:
                end = datetime.now().strftime("%Y%m%d")
            if not start:
                start = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

            # "YYYYMMDD" → datetime（DB timestamp__gte/lte 过滤需 datetime 类型，
            # 不可像 day 分支透传 str——adjustfactor_service.get_adjustfactors_df 签名为 datetime）
            start_dt = datetime.strptime(start, "%Y%m%d")
            end_dt = datetime.strptime(end, "%Y%m%d")

            from ginkgo.data.containers import container
            adjustfactor_service = container.adjustfactor_service()
            result = adjustfactor_service.get_adjustfactors_df(
                code=code, start_date=start_dt, end_date=end_dt
            )

            if not result.success:
                console.print(f":x: Failed to get adjustfactor data: {result.message}")
                raise typer.Exit(1)

            import pandas as pd
            df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

            if df.empty:
                console.print(f":information: No adjustfactor data found for {code} ({start}-{end})")
                return

            # Raw JSON 输出（对齐 stockinfo 分支）
            if raw:
                import json
                console.print(json.dumps(df.to_dict('records'), indent=2, ensure_ascii=False, default=str))
                return

            # 列名对齐 MAdjustfactor（foreadjustfactor/backadjustfactor/adjustfactor），
            # 对齐 day/tick 分支用 model 真实列名的写法——虚构列名会被 show_cols 过滤掉，
            # 导致表格只显示 code/timestamp、因子值全丢。
            display_cols = ["code", "timestamp", "foreadjustfactor", "backadjustfactor", "adjustfactor"]
            show_cols = [c for c in display_cols if c in df.columns]
            df_display = df[show_cols].copy()
            if "timestamp" in df_display.columns:
                df_display["timestamp"] = df_display["timestamp"].astype(str).str[:10]

            limit = page_size or 50
            if len(df_display) > limit:
                console.print(f":information: Showing {limit} of {len(df_display)} records")
                df_display = df_display.tail(limit)

            table = Table(title=f"Adjustfactor Data: {code} ({start}-{end})", show_lines=False)
            for col in show_cols:
                table.add_column(col, style="cyan")
            for _, row in df_display.iterrows():
                table.add_row(*[str(v) for v in row])
            console.print(table)
            console.print(f":information: {len(df)} records")

        elif data_type == "sources":
            from ginkgo.data.sources import GinkgoTushare, GinkgoTDX
            from ginkgo.libs import GCONF

            # 容器已注入的数据源（containers.py: ginkgo_tushare_source / ginkgo_tdx_source）。
            # 仅展示元信息，不实例化——避免触发 connect() 的网络/token 副作用。
            configured_sources = [
                ("tushare", GinkgoTushare, getattr(GCONF, "TUSHARETOKEN", None)),
                ("tdx", GinkgoTDX, None),  # TDX 无 token 依赖
            ]

            table = Table(title=":plug: Configured Data Sources", show_lines=False)
            table.add_column("name", style="cyan")
            table.add_column("type", style="green")
            table.add_column("configured", style="yellow")

            for name, cls, token in configured_sources:
                # token 为 None 表示该数据源不依赖 token（如 TDX），视为已配置
                is_configured = "yes" if token is None or token else "no"
                table.add_row(name, cls.__name__, is_configured)

            console.print(table)
            console.print(f":information: {len(configured_sources)} data source(s) configured")

        else:
            console.print(f":x: Unknown data type: {data_type}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error getting data: {e}")
        raise typer.Exit(1)


@app.command()
def status():
    """
    :gear: Show data synchronization status.
    """
    console.print(":gear: Data synchronization status:")
    # TODO: Implement data status check
    console.print(":information: Data status check not yet implemented")


def _is_valid_stock_code(code: str) -> bool:
    """#5962: 校验 A 股代码格式。接受项目内**两种既有记法**：

    - 后缀: ``NNNNNN.SH``/``NNNNNN.SZ``（如 ``000001.SZ``，``data get stockinfo -c`` 用此）
    - 前缀: ``SHNNNNNN``/``SZNNNNNN``（如 ``SH600000``，position/adjustfactor/tick mapper 用此）

    仅做**格式**校验，不做 DB 存在性校验（后者属 service 层职责）。
    目的：拒绝 ``INVALIDCODE`` / 裸 ``000001``（无市场标记）等明显无效输入，避免穿透到
    service 层后以 "no data" + exit 0 的形式误报成功（见 [[arch_ashare_code_market_prefix_gap]]）。
    """
    import re
    if not code:
        return False
    suffix = r"\d{6}\.(SH|SZ)"
    prefix = r"(SH|SZ)\d{6}"
    return bool(re.fullmatch(suffix, code) or re.fullmatch(prefix, code))


@app.command()
def sync(
    data_type: str = typer.Argument(..., help="Data type to sync (stockinfo/day/tick/adjustfactor)"),
    code: Optional[str] = typer.Option(None, "--code", "-c", help="Stock code (for day/tick data)"),
    date: Optional[str] = typer.Option(None, "--date", "-d", help="Specific date (YYYYMMDD, for tick data only)"),
    market: Optional[str] = typer.Option(None, "--market", help="Filter by market"),
    exchange: Optional[str] = typer.Option(None, "--exchange", help="Filter by exchange"),
    full: bool = typer.Option(False, "--full", help="Full sync from listing date (skip existing data)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force sync (delete and re-insert)"),
    daemon: bool = typer.Option(False, "--daemon", help="Run sync in background via Kafka queue"),
):
    """
    :repeat: Sync data from external sources.
    """
    # #5962: --code 格式校验门。须在 try 块外，否则 typer.Exit 被外层 except(Exception) 吞
    # 并多印 "Error updating data: 1" 噪音（见 arch_typer_exit_caught_by_except）。
    # day/tick/adjustfactor 接受 --code；无效格式直接非零退出，避免穿透到 service 层
    # 后以 "no data available" warning + exit 0 的形式误报成功。
    if code is not None and data_type in ("day", "tick", "adjustfactor"):
        if not _is_valid_stock_code(code):
            console.print(
                f":x: Invalid stock code '{code}'. "
                "Expected format: NNNNNN.SH or NNNNNN.SZ (e.g. 000001.SZ, 600000.SH)."
            )
            raise typer.Exit(1)

    try:
        # 如果是daemon模式，发送Kafka消息并退出
        if daemon:
            from ginkgo.data.containers import container
            kafka_service = container.kafka_service()

            console.print(f":information: Sending {data_type} sync task to background queue...")

            success = False
            if data_type == "stockinfo":
                success = kafka_service.send_stockinfo_update_signal()
            elif data_type == "day":
                if code:
                    # 单股票日K线同步：直接传递full和force参数
                    success = kafka_service.send_daybar_update_signal(code=code, full=full, force=force)
                else:
                    # 全代码日K线同步
                    success = kafka_service.send_bar_all_signal(full=full, force=force)
            elif data_type == "tick":
                if code:
                    # 单股票tick同步：传递完整的full和force参数
                    success = kafka_service.send_tick_update_signal(code=code, full=full, force=force)
                else:
                    # 全代码tick同步
                    success = kafka_service.send_tick_all_signal(full=full, force=force)
            elif data_type == "adjustfactor":
                if code:
                    # 单股票adjustfactor同步：直接传递full和force参数
                    success = kafka_service.send_adjustfactor_update_signal(code=code, full=full, force=force)
                else:
                    # 全代码adjustfactor同步：直接pass参数
                    success = kafka_service.send_adjustfactor_all_signal(full=full, force=force)

            if success:
                console.print(f":white_check_mark: {data_type} sync task successfully queued for background processing")
                console.print(f":information: Use 'ginkgo kafka status' to monitor queue status")
            else:
                console.print(f":x: Failed to queue {data_type} sync task")
                if not force:
                    raise typer.Exit(1)
            return

        if data_type == "stockinfo":
            from ginkgo.data.containers import container
            stockinfo_service = container.stockinfo_service()
            console.print(":repeat: Syncing stock information...")
            result = stockinfo_service.sync()
            if result and result.is_success():
                console.print(f":white_check_mark: {result.message}")
            else:
                error_msg = result.message if result and hasattr(result, "message") else "unknown error"
                console.print(f":x: Stock info sync failed: {error_msg}")
                raise typer.Exit(1)

        elif data_type == "day":
            from ginkgo import service_hub
            from datetime import datetime

            bar_service = service_hub.data.bar_service()
            stockinfo_service = service_hub.data.stockinfo_service()

            # 确定同步哪些股票
            if code:
                codes = [code]
                console.print(f":repeat: Syncing day data for {code}...")
            else:
                # 获取所有股票代码
                stock_result = stockinfo_service.list(page_size=5000)
                if stock_result.is_success() and stock_result.data:
                    stocks = stock_result.data.get('data', stock_result.data) if isinstance(stock_result.data, dict) else stock_result.data
                    codes = [s.code for s in stocks]
                    console.print(f":repeat: Syncing day data for all {len(codes)} stocks...")
                else:
                    console.print(":x: Failed to get stock list")
                    raise typer.Exit(1)

            try:
                success_count = 0
                error_count = 0

                for current_code in codes:
                    try:
                        console.print(f":information: Processing {current_code}...")

                        if full:
                            # 全量同步：从1990年开始
                            console.print(f":information: Full sync for {current_code} (from 1990-01-01)")
                            result = bar_service.sync_range(
                                code=current_code,
                                start_date=datetime(1990, 1, 1),
                                end_date=datetime.now()
                            )
                        else:
                            # 增量同步：智能同步
                            console.print(f":information: Smart sync for {current_code}")
                            result = bar_service.sync_smart(code=current_code)

                        if result and result.is_success():
                            # 检查实际同步的记录数，避免误导性成功消息
                            records_added = 0
                            try:
                                raw = getattr(result.data, 'records_added', 0)
                                records_added = int(raw) if isinstance(raw, (int, float)) else 0
                            except (AttributeError, TypeError, ValueError):
                                records_added = 0
                            if records_added > 0:
                                success_count += 1
                                console.print(f":white_check_mark: {current_code} sync completed ({records_added} records)")
                            else:
                                console.print(f":warning: {current_code} — no data available from source")
                        else:
                            error_count += 1
                            error_msg = result.message if hasattr(result, 'message') else str(result.error) if hasattr(result, 'error') else 'Unknown error'
                            console.print(f":x: {current_code} sync failed: {error_msg}")

                    except Exception as e:
                        error_count += 1
                        console.print(f":x: Error syncing {current_code}: {str(e)}")
                        continue

                console.print(f":information: Day sync completed. Success: {success_count}, Errors: {error_count}")

            except Exception as e:
                console.print(f":x: Error in day sync process: {e}")
                if not force:
                    raise typer.Exit(1)

        elif data_type == "tick":
            from ginkgo import service_hub
            from datetime import datetime

            tick_service = service_hub.data.tick_service()
            stockinfo_service = service_hub.data.stockinfo_service()

            # 确定同步哪些股票
            if code:
                codes = [code]
                console.print(f":repeat: Syncing tick data for {code}...")
            else:
                # 获取所有股票代码
                stock_result = stockinfo_service.list(page_size=5000)
                if stock_result.is_success() and stock_result.data:
                    stocks = stock_result.data.get('data', stock_result.data) if isinstance(stock_result.data, dict) else stock_result.data
                    codes = [s.code for s in stocks]
                    console.print(f":repeat: Syncing tick data for all {len(codes)} stocks...")
                else:
                    console.print(":x: Failed to get stock list")
                    raise typer.Exit(1)

            try:
                success_count = 0
                error_count = 0

                for current_code in codes:
                    try:
                        console.print(f":information: Processing {current_code}...")

                        if date:
                            # 指定日期同步
                            target_date = datetime.strptime(date, "%Y%m%d")
                            console.print(f":information: Syncing tick data for {current_code} on {date}")
                            result = tick_service.sync_date(current_code, target_date)

                        elif full:
                            # 全量同步：从上市开始
                            console.print(f":information: Full sync for {current_code} (from listing date)")
                            result = tick_service.sync_backfill_by_date(current_code, force_overwrite=force)
                        else:
                            # 增量同步：智能同步
                            console.print(f":information: Smart sync for {current_code}")
                            result = tick_service.sync_smart(current_code)

                        if result and result.is_success():
                            success_count += 1
                            console.print(f":white_check_mark: {current_code} sync completed")
                        else:
                            error_count += 1
                            error_msg = result.message if hasattr(result, 'message') else str(result.error) if hasattr(result, 'error') else 'Unknown error'
                            console.print(f":x: {current_code} sync failed: {error_msg}")

                    except Exception as e:
                        error_count += 1
                        console.print(f":x: Error syncing {current_code}: {str(e)}")
                        continue

                console.print(f":information: Tick sync completed. Success: {success_count}, Errors: {error_count}")

            except Exception as e:
                console.print(f":x: Error in tick sync process: {e}")
                if not force:
                    raise typer.Exit(1)

        elif data_type == "adjustfactor":
            from ginkgo.data.containers import container
            # CLI → Service 直调（分层规则）。旧 import 的两个自由函数从未在 src/ 实现，
            # 每次执行必 ImportError。sync 带 fast_mode 参数，full/force 语义无损透传。
            adjustfactor_service = container.adjustfactor_service()

            # 确定同步哪些股票
            if code:
                codes = [code]
                console.print(f":repeat: Syncing adjustfactor data for {code}...")
            else:
                # 获取所有股票代码
                stockinfo_service = container.stockinfo_service()
                stock_result = stockinfo_service.get()
                if stock_result.success and stock_result.data:
                    codes = [s.code for s in stock_result.data]
                    console.print(f":repeat: Syncing adjustfactor data for all {len(codes)} stocks...")
                else:
                    console.print(":x: Failed to get stock list")
                    raise typer.Exit(1)

            try:
                success_count = 0
                error_count = 0

                for current_code in codes:
                    try:
                        console.print(f":information: Processing {current_code}...")

                        if full:
                            if force:
                                # 强制全量同步：fast_mode=False 重算覆盖
                                console.print(f":information: Force full sync for {current_code} (overwrite existing)")
                                result = adjustfactor_service.sync(current_code, fast_mode=False)
                            else:
                                # 全量同步：fast_mode=True 跳过已有数据
                                console.print(f":information: Full sync for {current_code} (skip existing)")
                                result = adjustfactor_service.sync(current_code, fast_mode=True)
                        else:
                            # 增量同步：从最新日期开始到当下
                            console.print(f":information: Incremental sync for {current_code} (from latest date)")
                            result = adjustfactor_service.sync(current_code, fast_mode=True)

                        # Check sync result - ServiceResult has success property, other results may not
                        sync_success = False
                        if hasattr(result, 'success'):
                            sync_success = result.success
                        elif result is None:  # Some functions return None on success
                            sync_success = True


                        if sync_success:
                            # 仿 day 分支：从 result.data.records_added 提取实际入库条数，
                            # 避免无数据时仍打印 ":white_check_mark: sync completed" 误导用户（#6053）。
                            records_added = 0
                            try:
                                _data = getattr(result, 'data', None)
                                raw = getattr(_data, 'records_added', 0)
                                records_added = int(raw) if isinstance(raw, (int, float)) else 0
                            except (AttributeError, TypeError, ValueError):
                                records_added = 0
                            if records_added > 0:
                                success_count += 1
                                console.print(f":white_check_mark: {current_code} sync completed ({records_added} records)")
                            else:
                                # service.sync 成功但源端无数据：不算成功计数，避免误导（#6053）
                                console.print(f":warning: {current_code} — no adjustfactor data available from source")

                            # 同步完成后立即计算该股票的复权因子
                            console.print(f":information: Calculating adjustment factors for {current_code}...")
                            calc_result = adjustfactor_service.calculate(current_code)
                            if calc_result and hasattr(calc_result, 'success') and calc_result.success:
                                console.print(f":white_check_mark: {current_code} adjustment factor calculation completed")
                            else:
                                console.print(f":warning: {current_code} adjustment factor calculation failed")
                                if hasattr(calc_result, 'error') and calc_result.error:
                                    console.print(f"   Error: {calc_result.error}")
                        else:
                            error_count += 1
                            console.print(f":x: {current_code} sync failed")
                            if hasattr(result, 'error') and result.error:
                                console.print(f"   Error: {result.error}")
                            elif hasattr(result, 'message') and result.message:
                                console.print(f"   Message: {result.message}")

                    except Exception as e:
                        error_count += 1
                        console.print(f":x: Error syncing {current_code}: {str(e)}")
                        continue

                console.print(f":information: Adjustfactor sync completed. Success: {success_count}, Errors: {error_count}")

            except Exception as e:
                console.print(f":x: Error in adjustfactor sync process: {e}")
                if not force:
                    raise typer.Exit(1)

        else:
            console.print(f":x: Unknown data type: {data_type}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error updating data: {e}")
        raise typer.Exit(1)


@app.command()
def migrate(
    database: str = typer.Option("mysql", "--database", "-d", help="Database type (mysql/clickhouse/mongodb)"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Migration message/description"),
    autogenerate: bool = typer.Option(False, "--autogenerate", "-a", help="Auto-generate migration from model changes"),
    revision: Optional[str] = typer.Option(None, "--revision", "-r", help="Specific revision to upgrade/downgrade"),
    action: str = typer.Option("upgrade", "--action", help="Action: upgrade/downgrade/heads/history/current"),
):
    """
    :page_facing_up: Database migration management.

    Examples:
        ginkgo data migrate                              # Show migration status
        ginkgo data migrate --autogenerate -m "Add users table"
        ginkgo data migrate --action upgrade
        ginkgo data migrate --action heads
        ginkgo data migrate --action revision -r <revision_id>
    """
    try:
        if database == "mysql":
            import subprocess
            import os

            migrations_dir = "/home/kaoru/Ginkgo/migrations/mysql"
            alembic_ini = os.path.join(migrations_dir, "alembic.ini")

            if autogenerate:
                # Auto-generate migration
                console.print(f":memo: Generating migration for MySQL database...")
                if message:
                    cmd = ["alembic", "revision", "--autogenerate", "-m", message]
                else:
                    cmd = ["alembic", "revision", "--autogenerate"]
                subprocess.run(cmd, cwd=migrations_dir, check=True)
                console.print(f":white_check_mark: Migration generated successfully")

            elif action == "upgrade":
                console.print(f":arrow_up: Upgrading MySQL database to latest version...")
                if revision:
                    subprocess.run(["alembic", "upgrade", revision], cwd=migrations_dir, check=True)
                else:
                    subprocess.run(["alembic", "upgrade", "head"], cwd=migrations_dir, check=True)
                console.print(f":white_check_mark: Database upgraded successfully")

            elif action == "downgrade":
                if not revision:
                    console.print(":x: --revision is required for downgrade")
                    raise typer.Exit(1)
                console.print(f":arrow_down: Downgrading MySQL database to {revision}...")
                subprocess.run(["alembic", "downgrade", revision], cwd=migrations_dir, check=True)
                console.print(f":white_check_mark: Database downgraded successfully")

            elif action == "heads":
                subprocess.run(["alembic", "heads"], cwd=migrations_dir)
            elif action == "history":
                subprocess.run(["alembic", "history"], cwd=migrations_dir)
            elif action == "current":
                subprocess.run(["alembic", "current"], cwd=migrations_dir)
            else:
                # Show current status
                console.print(f":information: MySQL Database Migration Status")
                console.print(f"Migrations directory: {migrations_dir}")
                console.print(f"\nAvailable actions:")
                console.print(f"  --autogenerate    Generate migration from model changes")
                console.print(f"  --action upgrade  Upgrade to latest revision")
                console.print(f"  --action heads    Show available heads")
                console.print(f"  --action history  Show migration history")
                console.print(f"  --action current  Show current revision")

        elif database == "clickhouse":
            console.print(":information: ClickHouse migrations use SQL scripts in migrations/clickhouse/")
            console.print("Manual execution required:")
            console.print("  1. Create SQL migration file in migrations/clickhouse/")
            console.print("  2. Execute: clickhouse-client --query=$(cat migration.sql)")

        elif database == "mongodb":
            console.print(":information: MongoDB migrations use JavaScript scripts in migrations/mongodb/")
            console.print("Manual execution required:")
            console.print("  1. Create JS migration file in migrations/mongodb/")
            console.print("  2. Execute: mongo <migration.js>")

        else:
            console.print(f":x: Unknown database type: {database}")
            console.print("Available types: mysql, clickhouse, mongodb")
            raise typer.Exit(1)

    except subprocess.CalledProcessError as e:
        console.print(f":x: Migration command failed: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)