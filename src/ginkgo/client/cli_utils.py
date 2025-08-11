from rich.console import Console
from rich.tree import Tree
from typing import Optional
from ginkgo.enums import FILE_TYPES

console = Console()

def _get_component_parameters(mapping_id: str, file_id: str, file_type: FILE_TYPES) -> dict:
    """获取组件的参数信息"""
    try:
        from ginkgo.data.containers import container
        
        # 从params表获取所有构造参数
        param_crud = container.cruds.param()
        params_df = param_crud.find(filters={"mapping_id": mapping_id}, as_dataframe=True, order_by="index")
        params_dict = {}
        
        if params_df.shape[0] > 0:
            # 显示所有参数，使用索引作为键名
            for i, param_value in enumerate(params_df["value"].values):
                params_dict[f"param_{i}"] = param_value
        
        return params_dict
        
    except Exception as e:
        console.print(f"[red]Error getting parameters for {file_id}: {e}[/red]")
        return {}

def _add_portfolio_components(parent_node, portfolio_id: str, detail: bool, filter_type: Optional[FILE_TYPES]):
    """添加Portfolio的组件到树节点"""
    from ginkgo.data.containers import container
    
    # 获取portfolio的文件映射
    portfolio_service = container.portfolio_service()
    mappings_df = portfolio_service.get_portfolio_file_mappings(as_dataframe=True)
    portfolio_files = mappings_df[mappings_df["portfolio_id"] == portfolio_id]
    
    if portfolio_files.shape[0] == 0:
        parent_node.add("[dim]No components bound to this portfolio[/dim]")
        return
    
    # 按文件类型分组
    components = {
        "selectors": [],
        "sizers": [],
        "strategies": [],
        "risks": [],
        "analyzers": []
    }
    
    for _, mapping in portfolio_files.iterrows():
        file_type_value = mapping["type"]
        # 将数字转换为枚举
        file_type = FILE_TYPES(file_type_value)
        component_info = {
            "name": mapping["name"],
            "id": mapping["file_id"],
            "mapping_id": mapping["uuid"],
            "type": file_type
        }
        
        if file_type == FILE_TYPES.SELECTOR:
            components["selectors"].append(component_info)
        elif file_type == FILE_TYPES.SIZER:
            components["sizers"].append(component_info)
        elif file_type == FILE_TYPES.STRATEGY:
            components["strategies"].append(component_info)
        elif file_type == FILE_TYPES.RISKMANAGER:
            components["risks"].append(component_info)
        elif file_type == FILE_TYPES.ANALYZER:
            components["analyzers"].append(component_info)
    
    # 根据filter_type筛选要显示的组件类型
    component_sections = []
    if filter_type is None:
        component_sections = [
            ("selectors", ":dart: Selectors", "selector"),
            ("sizers", ":balance_scale: Sizers", "sizer"),
            ("strategies", ":chart_with_upwards_trend: Strategies", "strategy"),
            ("risks", ":shield: Risk Managements", "risk"),
            ("analyzers", ":bar_chart: Analyzers", "analyzer")
        ]
    else:
        type_mapping = {
            FILE_TYPES.SELECTOR: ("selectors", ":dart: Selectors", "selector"),
            FILE_TYPES.SIZER: ("sizers", ":balance_scale: Sizers", "sizer"),
            FILE_TYPES.STRATEGY: ("strategies", ":chart_with_upwards_trend: Strategies", "strategy"),
            FILE_TYPES.RISKMANAGER: ("risks", ":shield: Risk Managements", "risk"),
            FILE_TYPES.ANALYZER: ("analyzers", ":bar_chart: Analyzers", "analyzer")
        }
        if filter_type in type_mapping:
            component_sections = [type_mapping[filter_type]]
    
    # 显示各类组件
    for component_key, section_title, _ in component_sections:
        component_list = components[component_key]
        if component_list:
            section_node = parent_node.add(f"[bold]{section_title}[/bold]")
            for component in component_list:
                component_node = section_node.add(f"{component['name']} [dim]ID:{component['id']}[/dim]")
                
                if detail:
                    # 获取并显示组件参数详情
                    params = _get_component_parameters(component['mapping_id'], component['id'], component['type'])
                    if params:
                        for param_name, param_value in params.items():
                            component_node.add(f"[cyan]{param_name}[/cyan]: [green]{param_value}[/green]")
                    else:
                        component_node.add("[dim]No parameters found[/dim]")

def _show_portfolio_tree(portfolio_row, detail: bool, filter_type: Optional[FILE_TYPES]):
    """显示Portfolio树结构"""
    tree = Tree(f"[bold green]Portfolio:[/bold green] {portfolio_row['name']} ([yellow]{portfolio_row['uuid']}[/yellow])")
    _add_portfolio_components(tree, portfolio_row['uuid'], detail, filter_type)
    console.print(tree)

def _show_engine_tree(engine_row, detail: bool, filter_type: Optional[FILE_TYPES]):
    """显示Engine树结构"""
    from ginkgo.data.containers import container
    
    tree = Tree(f"[bold blue]Engine:[/bold blue] {engine_row['name']} ([cyan]{engine_row['uuid']}[/cyan])")
    
    # 获取engine关联的portfolios
    engine_service = container.engine_service()
    mappings_df = engine_service.get_engine_portfolio_mappings(as_dataframe=True)
    engine_portfolios = mappings_df[mappings_df["engine_id"] == engine_row["uuid"]]
    
    if engine_portfolios.shape[0] == 0:
        tree.add("[dim]No portfolios bound to this engine[/dim]")
    else:
        for _, mapping in engine_portfolios.iterrows():
            portfolio_id = mapping["portfolio_id"]
            # 获取portfolio详情
            portfolio_service = container.portfolio_service()
            portfolio_df = portfolio_service.get_portfolio(portfolio_id, as_dataframe=True)
            if portfolio_df.shape[0] > 0:
                portfolio_row = portfolio_df.iloc[0]
                portfolio_branch = tree.add(f"[bold green]Portfolio:[/bold green] {portfolio_row['name']} ([yellow]{portfolio_id}[/yellow])")
                _add_portfolio_components(portfolio_branch, portfolio_id, detail, filter_type)
    
    console.print(tree)