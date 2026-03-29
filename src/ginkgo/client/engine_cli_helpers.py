# Upstream: engine_cli.py (引擎管理CLI)
# Downstream: EngineService/PortfolioService/MappingService(引擎/组合/映射服务)、FileCRUD/EnginePortfolioMappingCRUD/PortfolioFileMappingCRUD/ParamCRUD(CRUD操作)、Rich库(表格显示)
# Role: 引擎管理CLI的辅助函数集合，包含ID解析、分析报告生成、组件信息收集与显示等非命令函数


"""
Ginkgo Engine CLI Helpers - 引擎管理CLI辅助函数

从 engine_cli.py 中提取的非命令辅助函数，用于减少主文件体积。
所有CLI命令入口仍保留在 engine_cli.py 中。
"""

from typing import Optional
from rich.console import Console
from rich.table import Table as RichTable


# ============================================================
# 引擎ID解析
# ============================================================

def resolve_engine_id(engine_identifier: str) -> Optional[str]:
    """
    根据engine名称或UUID查找engine的UUID

    优先级：
    1. 按UUID精确查找
    2. 按name精确查找（如果有多个，选择第一个）
    3. 如果都没有找到，返回None

    Args:
        engine_identifier: engine名称或UUID

    Returns:
        engine的UUID，如果找到则返回，否则返回None
    """
    from rich.console import Console

    console = Console(emoji=True, legacy_windows=False)

    try:
        from ginkgo.data.containers import container

        engine_service = container.engine_service()

        # 1. 首先尝试按UUID精确查找
        result = engine_service.get(engine_id=engine_identifier)
        if result.success and result.data:
            # Handle both ModelList and single object
            if hasattr(result.data, '__len__') and len(result.data) > 0:
                # ModelList - get the first engine
                return result.data[0].uuid
            elif hasattr(result.data, 'uuid'):
                # Single engine object
                return result.data.uuid

        # 2. 如果UUID查找失败，尝试按name精确查找
        engines_result = engine_service.get(name=engine_identifier)
        if engines_result.success and engines_result.data and len(engines_result.data) > 0:
            if len(engines_result.data) > 1:
                console.print(f":warning: Found {len(engines_result.data)} engines with name '{engine_identifier}', using the first one")
            return engines_result.data[0].uuid

        # 3. 如果精确查找都失败，尝试模糊搜索（UUID和name字段）
        fuzzy_result = engine_service.fuzzy_search(engine_identifier, fields=["uuid", "name"])
        if fuzzy_result.success and fuzzy_result.data and len(fuzzy_result.data) > 0:
            console.print(f":information: Fuzzy search found {len(fuzzy_result.data)} engines matching '{engine_identifier}':")

            # 显示模糊搜索结果
            table = Table(title="Fuzzy Search Results")
            table.add_column("Name", style="cyan")
            table.add_column("UUID", style="magenta")
            table.add_column("Status", style="green")
            table.add_column("Match Type", style="yellow")

            for engine in fuzzy_result.data:
                # 判断匹配类型
                match_type = "UUID" if engine.uuid[:8] == engine_identifier[:8] else "Name"
                if hasattr(engine, 'status'):
                    status_str = engine.status.name if hasattr(engine.status, 'name') else str(engine.status)
                else:
                    status_str = "Unknown"

                table.add_row(engine.name, engine.uuid[:8] + "...", status_str, match_type)

            console.print(table)
            console.print(f":information: Using first match: {fuzzy_result.data[0].name} ({fuzzy_result.data[0].uuid[:8]}...)")
            return fuzzy_result.data[0].uuid

        # 4. 如果所有查找都失败，返回None让调用者处理
        return None

    except Exception as e:
        console.print(f":x: Error resolving engine ID: {e}")
        return None


# ============================================================
# 回测分析报告
# ============================================================

def analyze_net_value(portfolio):
    """分析净值数据"""
    net_value_info = {}

    try:
        # 尝试从Portfolio获取净值分析器
        if hasattr(portfolio, 'analyzers'):
            for analyzer in portfolio.analyzers:
                if hasattr(analyzer, 'current_net_value'):
                    current_net_value = float(analyzer.current_net_value)
                    net_value_info['current_net_value'] = current_net_value

                    if hasattr(analyzer, '_size') and analyzer._size > 0:
                        net_value_info['record_count'] = analyzer._size

                        if analyzer._size > 1 and hasattr(analyzer, '_values'):
                            values = analyzer._values[:analyzer._size]
                            max_net_value = max(values)
                            min_net_value = min(values)
                            net_value_info['max_net_value'] = max_net_value
                            net_value_info['min_net_value'] = min_net_value

                            if max_net_value > 0:
                                max_drawdown = (max_net_value - min_net_value) / max_net_value * 100
                                net_value_info['max_drawdown'] = max_drawdown
                    break

    except Exception as e:
        pass  # 净值分析失败时返回空字典

    return net_value_info


def generate_backtest_analysis(console: Console, portfolio, engine):
    """
    生成回测统计分析报告，参考complete_backtest_example.py的逻辑
    """
    try:
        # 获取初始资金 - 从portfolio属性获取
        initial_cash = float(getattr(portfolio, 'initial_cash', 100000.0))

        # 基本统计分析 - 直接从portfolio属性获取
        final_value = 0.0

        # 尝试多种方式获取portfolio价值
        if hasattr(portfolio, 'worth'):
            final_value = float(portfolio.worth)
        elif hasattr(portfolio, 'total_value'):
            final_value = float(portfolio.total_value)
        else:
            # 手动计算：现金 + 持仓价值
            cash = float(getattr(portfolio, 'cash', 0.0))
            frozen = float(getattr(portfolio, 'frozen', 0.0))
            final_value = cash + frozen

        total_return = (final_value - initial_cash) / initial_cash if initial_cash > 0 else 0.0

        # 交易统计 - 直接从portfolio获取
        orders = getattr(portfolio, 'orders', [])
        order_count = len(orders) if orders else 0

        positions = getattr(portfolio, 'positions', {})
        if isinstance(positions, dict):
            position_count = len(positions)
        elif hasattr(positions, '__len__'):
            position_count = len(positions)
        else:
            position_count = 0

        # 净值分析
        net_value_info = analyze_net_value(portfolio)

        # 创建统计表格
        stats_table = RichTable(title="💰 收益统计", show_header=True, header_style="bold blue")
        stats_table.add_column("指标", style="cyan", width=20)
        stats_table.add_column("数值", justify="right", style="green")

        stats_table.add_row("初始资金", f"¥{initial_cash:,}")
        stats_table.add_row("期末价值", f"¥{final_value:,.2f}")
        stats_table.add_row("总收益率", f"{total_return*100:.2f}%")
        stats_table.add_row("总盈亏", f"¥{final_value - initial_cash:,.2f}")

        console.print(stats_table)

        # 创建交易统计表格
        trading_table = RichTable(title="📈 交易统计", show_header=True, header_style="bold blue")
        trading_table.add_column("指标", style="cyan", width=20)
        trading_table.add_column("数值", justify="right", style="green")

        trading_table.add_row("订单数量", f"{order_count}")
        trading_table.add_row("持仓数量", f"{position_count}")

        console.print(trading_table)

        # 持仓详情
        if position_count > 0:
            console.print("\n💼 当前持仓:")
            position_table = RichTable(show_header=True, header_style="bold blue")
            position_table.add_column("股票代码", style="cyan")
            position_table.add_column("持仓数量", justify="right")
            position_table.add_column("持仓价值", justify="right", style="green")

            total_position_worth = 0
            for code, position in portfolio.positions.items():
                volume = getattr(position, 'volume', 0)
                worth = float(getattr(position, 'worth', 0))
                total_position_worth += worth
                position_table.add_row(code, f"{volume:,}", f"¥{worth:,.2f}")

            console.print(position_table)
            console.print(f"\n总持仓价值: ¥{total_position_worth:,.2f}")

        # 净值分析结果
        if net_value_info:
            console.print("\n📊 净值分析:")
            net_table = RichTable(show_header=True, header_style="bold blue")
            net_table.add_column("指标", style="cyan", width=20)
            net_table.add_column("数值", justify="right", style="green")

            if 'current_net_value' in net_value_info:
                net_table.add_row("当前净值", f"¥{net_value_info['current_net_value']:,.2f}")

            if 'record_count' in net_value_info:
                net_table.add_row("净值记录数", f"{net_value_info['record_count']}")

            if 'max_net_value' in net_value_info:
                net_table.add_row("最高净值", f"¥{net_value_info['max_net_value']:,.2f}")

            if 'min_net_value' in net_value_info:
                net_table.add_row("最低净值", f"¥{net_value_info['min_net_value']:,.2f}")

            if 'max_drawdown' in net_value_info:
                net_table.add_row("最大回撤", f"{net_value_info['max_drawdown']:.2f}%")

            console.print(net_table)

        # 时间范围信息
        start_time = getattr(engine, 'start_time', None)
        end_time = getattr(engine, 'end_time', None)
        if start_time and end_time:
            console.print(f"\n⏰ 回测时间范围:")
            time_table = RichTable(show_header=True, header_style="bold blue")
            time_table.add_column("指标", style="cyan", width=15)
            time_table.add_column("时间", style="white")

            time_table.add_row("开始时间", str(start_time))
            time_table.add_row("结束时间", str(end_time))

            console.print(time_table)

    except Exception as e:
        console.print(f"⚠️ 统计分析过程中出现错误: {e}")


# ============================================================
# 组件信息收集与显示
# ============================================================

def collect_component_info(engine_id: str, container) -> dict:
    """收集所有组件信息，减少数据库查询次数"""
    component_data = {
        'has_portfolio': False,
        'portfolio_id': None,
        'portfolio_info': None,
        'strategies': [],
        'risk_managers': [],
        'analyzers': [],
        'selectors': [],
        'sizers': []
    }

    try:
        # 1. 获取Engine-Portfolio绑定关系
        portfolio_mappings = container.cruds.engine_portfolio_mapping().find(filters={"engine_id": engine_id})

        if len(portfolio_mappings) > 0:
            portfolio_id = portfolio_mappings[0].portfolio_id
            component_data['has_portfolio'] = True
            component_data['portfolio_id'] = portfolio_id

            # 2. 获取Portfolio详细信息
            portfolio_service = container.portfolio_service()
            portfolio_result = portfolio_service.get(portfolio_id=portfolio_id)

            if portfolio_result.success and len(portfolio_result.data) > 0:
                component_data['portfolio_info'] = portfolio_result.data[0]

            # 3. 一次性获取Portfolio的所有文件绑定关系
            file_mapping_crud = container.cruds.portfolio_file_mapping()
            all_file_mappings = file_mapping_crud.find(filters={"portfolio_id": portfolio_id})

            # 4. 按类型分类文件映射，并添加参数字段
            for mapping in all_file_mappings:
                file_info = {
                    'name': mapping.name,
                    'file_id': mapping.file_id,
                    'type': mapping.type,
                    'parameters': []  # 每个组件都有自己的参数列表
                }

                if mapping.type == 6:  # FILE_TYPES.STRATEGY
                    component_data['strategies'].append(file_info)
                elif mapping.type == 3:  # FILE_TYPES.RISKMANAGER
                    component_data['risk_managers'].append(file_info)
                elif mapping.type == 1:  # FILE_TYPES.ANALYZER
                    component_data['analyzers'].append(file_info)
                elif mapping.type == 4:  # FILE_TYPES.SELECTOR
                    component_data['selectors'].append(file_info)
                elif mapping.type == 5:  # FILE_TYPES.SIZER
                    component_data['sizers'].append(file_info)

            # 5. 获取所有参数 - 修复：现在参数使用mapping.uuid作为mapping_id
            param_crud = container.cruds.param()

            # 收集所有mapping的UUID
            mapping_uuids = [mapping.uuid for mapping in all_file_mappings]

            # 按mapping_uuid分别获取参数
            all_params = {}
            for mapping_uuid in mapping_uuids:
                params = param_crud.find(filters={"mapping_id": mapping_uuid})
                if params:
                    # 按index排序
                    sorted_params = sorted(params, key=lambda p: p.index)
                    all_params[mapping_uuid] = sorted_params

            # 🔑 关键修复：将参数分配给对应的组件
            for mapping in all_file_mappings:
                mapping_uuid = mapping.uuid

                # 获取该mapping的所有参数
                if mapping_uuid in all_params:
                    params = all_params[mapping_uuid]

                    # 找到对应的组件
                    component_list = None
                    if mapping.type == 6:  # STRATEGY
                        component_list = component_data['strategies']
                    elif mapping.type == 3:  # RISKMANAGER
                        component_list = component_data['risk_managers']
                    elif mapping.type == 1:  # ANALYZER
                        component_list = component_data['analyzers']
                    elif mapping.type == 4:  # SELECTOR
                        component_list = component_data['selectors']
                    elif mapping.type == 5:  # SIZER
                        component_list = component_data['sizers']

                    # 将参数分配给对应的组件
                    if component_list:
                        for component in component_list:
                            if component['file_id'] == mapping.file_id:
                                for param in params:
                                    import json
                                    try:
                                        # 尝试解析JSON值
                                        display_value = json.loads(param.value) if param.value and param.value.startswith('[') else param.value
                                    except Exception as e:
                                        from ginkgo.libs import GLOG
                                        GLOG.ERROR(f"Failed to parse param value as JSON for param index {param.index}: {e}")
                                        display_value = param.value

                                    component['parameters'].append({
                                        'index': param.index,
                                        'value': display_value,
                                        'raw_value': param.value
                                    })
                                break

    except Exception as e:
        # 如果查询失败，保持空的数据结构
        pass

    return component_data


def display_component_tree(console, component_data: dict):
    """以文件树结构显示组件信息"""
    if not component_data['has_portfolio']:
        console.print("└── (No portfolio bound to this engine)")
        return

    portfolio_id = component_data['portfolio_id']

    if component_data['portfolio_info']:
        portfolio = component_data['portfolio_info']
        console.print(f"├── 📦 Portfolio: {portfolio.name}")
        console.print(f"│   ├── ID: {portfolio_id}")
        console.print(f"│   ├── Created: {portfolio.create_at}")
    else:
        console.print(f"├── 📦 Portfolio: {portfolio_id}")
        console.print(f"│   ├── ID: {portfolio_id}")
        console.print(f"│   ├── (Portfolio details not found)")

    # 计算总的组件类型数量
    component_types = []
    if component_data['strategies']:
        component_types.append(("strategies", "📄", "Strategies"))
    if component_data['risk_managers']:
        component_types.append(("risk_managers", "🛡️", "Risk Managers"))
    if component_data['analyzers']:
        component_types.append(("analyzers", "📊", "Analyzers"))
    if component_data['selectors']:
        component_types.append(("selectors", "🎯", "Selectors"))
    if component_data['sizers']:
        component_types.append(("sizers", "📏", "Sizers"))

    # 显示各种组件
    for i, (key, icon, label) in enumerate(component_types):
        items = component_data[key]
        is_last_component = (i == len(component_types) - 1)

        # 组件类型前缀
        component_prefix = "│   └──" if is_last_component else "│   ├──"
        console.print(f"{component_prefix} {icon} {label} ({len(items)})")

        # 检查是否有组件有参数
        has_params_in_this_component = any(item.get('parameters') for item in items)

        for j, item in enumerate(items):
            is_last_file = (j == len(items) - 1)
            has_file_params = item.get('parameters')

            # 文件前缀：如果这个组件类型下有参数，或者这个文件有参数，需要保留垂直线
            if has_params_in_this_component or has_file_params:
                file_prefix = "│   │   └──" if is_last_file else "│   │   ├──"
            else:
                file_prefix = "│       └──" if is_last_file else "│       ├──"

            console.print(f"{file_prefix} {item['name']} (file_id: {item['file_id']})")

            # 显示该组件的参数
            if has_file_params:
                for k, param in enumerate(item['parameters']):
                    is_last_param = (k == len(item['parameters']) - 1)

                    # 参数前缀：只需要文件层的垂直线
                    if is_last_file and is_last_param:
                        param_prefix = "│   │          └──"
                    elif is_last_file:
                        param_prefix = "│   │          ├──"
                    elif is_last_param:
                        param_prefix = "│   │          └──"
                    else:
                        param_prefix = "│   │          ├──"

                    # 使用有意义的参数名称
                    param_display_name = param.get('display_name', f"[{param['index']}]")
                    console.print(f"{param_prefix} {param_display_name}: {param['value']}")

    # 如果没有任何组件
    if not component_types:
        console.print(f"│   └── (No components bound to portfolio)")

    console.print(f"└── (End of component tree)")


# ============================================================
# 组件文件内容获取
# ============================================================

def _get_component_file_content(file_id: str) -> str:
    """
    根据file_id从数据库获取组件文件内容

    Args:
        file_id: 文件UUID

    Returns:
        str: 文件内容，如果找不到返回None
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.libs import GLOG

        file_service = container.file_service()
        result = file_service.get_by_uuid(file_id)

        if result.success and result.data:
            file_info = result.data
            # 处理字典格式 {"file": MFile, "exists": True}
            if isinstance(file_info, dict) and 'file' in file_info:
                mfile = file_info['file']
                if hasattr(mfile, 'data') and mfile.data:
                    # 处理字节类型内容
                    if isinstance(mfile.data, bytes):
                        return mfile.data.decode('utf-8', errors='ignore')
                    else:
                        return str(mfile.data)
            # 直接处理对象格式
            elif hasattr(file_info, 'data') and file_info.data:
                if isinstance(file_info.data, bytes):
                    return file_info.data.decode('utf-8', errors='ignore')
                else:
                    return str(file_info.data)
        return None
    except Exception as e:
        from ginkgo.libs import GLOG
        GLOG.DEBUG(f"获取组件文件内容失败 {file_id}: {e}")
        return None


# ============================================================
# 参数匹配判断
# ============================================================

def _is_param_for_component(param_value: str, component_name: str, component_type: str) -> bool:
    """
    判断参数是否属于特定组件

    Args:
        param_value: 参数值
        component_name: 组件名称
        component_type: 组件类型 (strategy/selector/sizer)

    Returns:
        bool: 是否匹配
    """
    param_value = param_value.strip()
    component_name = component_name.lower()

    # 股票代码模式 - 通常属于selector
    if (len(param_value) == 6 and param_value.isdigit()) or \
       (len(param_value) == 9 and '.' in param_value and param_value.count('.') == 1):
        return component_type == 'selector' and ('fixed' in component_name or 'selector' in component_name)

    # 整数模式
    if param_value.isdigit():
        num = int(param_value)
        # 大数字（>=1000）可能是sizer的volume
        if num >= 1000:
            return component_type == 'sizer' and ('fixed' in component_name or 'sizer' in component_name)
        # 小数字可能是strategy的概率
        elif num < 100:
            return component_type == 'strategy' and ('random' in component_name or 'choice' in component_name)

    # 浮点数模式 - 通常是概率或比例
    try:
        float_val = float(param_value)
        if 0 < float_val <= 1:
            return component_type == 'strategy' and ('random' in component_name or 'choice' in component_name)
    except ValueError:
        pass

    return False
