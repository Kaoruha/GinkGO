"""
显示和格式化工具模块
合并了原来的 ginkgo_pretty.py 和 ginkgo_color.py
提供颜色控制和格式化输出功能
包含交互式表格显示组件
"""

from types import FunctionType, MethodType
import pandas as pd
from enum import Enum
import sys
import os
from typing import Optional, Dict, Any, Tuple
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.prompt import Prompt




class GinkgoColor:
    """颜色控制类"""
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    def red(self, msg: str) -> str:
        return f"{self.FAIL}{msg}{self.ENDC}"
    
    def green(self, msg: str) -> str:
        return f"{self.OKGREEN}{msg}{self.ENDC}"
    
    def blue(self, msg: str) -> str:
        return f"{self.OKBLUE}{msg}{self.ENDC}"
    
    def cyan(self, msg: str) -> str:
        return f"{self.OKCYAN}{msg}{self.ENDC}"
    
    def yellow(self, msg: str) -> str:
        return f"{self.WARNING}{msg}{self.ENDC}"
    
    def bold(self, msg: str) -> str:
        return f"{self.BOLD}{msg}{self.ENDC}"
    
    def header(self, msg: str) -> str:
        return f"{self.HEADER}{msg}{self.ENDC}"
    
    def underline(self, msg: str) -> str:
        return f"{self.UNDERLINE}{msg}{self.ENDC}"


def chinese_count(msg: str) -> int:
    """计算字符串中中文字符的数量"""
    count = 0
    for _char in msg:
        if "\u4e00" <= _char <= "\u9fa5":
            count = count + 1
    return count


def pretty_repr(class_name: str, msg: list, width: int = None) -> str:
    """
    格式化对象的打印输出
    Args:
        class_name: 类名
        msg: 消息列表
        width: 宽度
    Returns:
        格式化后的字符串
    """
    if width:
        row_max = width
    else:
        row_max = 0
        for i in msg:
            if len(str(i)) > row_max:
                row_max = len(str(i))
        row_max += 4

    r = ""
    r += "\n"
    r += "-" * (row_max // 2 - len(class_name) // 2) + f" {class_name} "
    r += "-" * (row_max - len(r)) + "+"
    
    for row in msg:
        r += "\n"
        r += str(row)
        l = row_max - 1 - len(str(row)) - chinese_count(str(row))
        r += " " * l + "|"
    
    r += "\n"
    r += "-" * (row_max - 1) + "+"
    r += "\n"

    return r


def base_repr(obj, name, label_len=12, total_len=80, *args, **kwargs) -> str:
    """
    生成对象的基础表示
    Args:
        obj: 对象
        name: 对象名称
        label_len: 标签长度
        total_len: 总长度
    Returns:
        对象的字符串表示
    """
    methods = ["delete", "query", "registry", "metadata", "to_dataframe", "value"]
    r = []
    count = label_len if label_len else 12

    # 内存位置
    mem = " " * (count - len("MEM"))
    mem += "MEM : "
    mem += f"{hex(id(obj))}"
    r.append(mem)

    for param in obj.__dir__():
        if param in methods:
            continue

        if param.startswith("_"):
            continue

        # 单次访问属性，避免多次调用导致的问题
        try:
            s = obj.__getattribute__(param)
        except Exception:
            # 跳过无法访问的属性
            continue

        # 排除方法和函数
        if isinstance(s, (MethodType, FunctionType)):
            continue

        tmp = " " * (count - len(str(param)))
        tmp += f"{str(param).upper()}"

        # 安全地转换为字符串，避免递归
        try:
            # 检查是否是基础类型，可以直接转换
            if isinstance(s, (int, float, str, bool, type(None))):
                filter_s = str(s)
            elif isinstance(s, (list, tuple)):
                # 对于序列，显示长度和类型
                filter_s = f"[{len(s)} items] {type(s).__name__}"
            elif isinstance(s, dict):
                # 对于字典，显示键数量
                filter_s = f"{{{len(s)} keys}} {type(s).__name__}"
            else:
                # 对于复杂对象，使用安全的表示
                class_name = s.__class__.__name__
                obj_id = hex(id(s))
                filter_s = f"<{class_name} at {obj_id}>"
        except RecursionError:
            # 遇到递归时使用安全的表示
            filter_s = f"<object at {hex(id(s))}>"
        except Exception:
            # 其他异常时使用类型表示
            filter_s = f"<{type(s).__name__} object>"
        
        special_ins_param = [
            "engine", "matchmaking", "datafeeder", "portfolio",
            "selector", "sizer", "data_feeder",
        ]
        special_list_param = ["portfolios", "strategies", "interested", "signals", "loggers", "risk_managers", "selectors"]
        special_dict_param = ["positions", "analyzers"]

        if isinstance(s, pd.DataFrame):
            filter_s = f"{str(s.shape)}"
        elif param == "bound_engine":
            # 特殊处理bound_engine属性
            if s is not None:
                engine_name = getattr(s, 'name', s.__class__.__name__)
                filter_s = f"[{hex(id(s))}] {engine_name}"
            else:
                filter_s = "None"
        elif param in special_ins_param:
            filter_s = f"[{hex(id(s))}] {str(s.name)}" if s is not None else "None"
        elif param in special_dict_param:
            filter_s = f"{len(s.keys())}"
        elif param in special_list_param:
            filter_s = f"{len(s)}"
        elif isinstance(s, Enum):
            filter_s += f" : {s.value}"
        elif param == "subscribers":
            filter_s = ""
            for i in range(len(s)):
                if i != 0:
                    filter_s += ","
                filter_s += s[i].name
        
        max_len = total_len - count - 6
        l = len(filter_s) + chinese_count(filter_s)
        if l > max_len:
            cc = chinese_count(filter_s)
            end = int(max_len - 3 - cc / 2)
            filter_s = filter_s[:end] + "..."
        tmp += f" : {filter_s}"
        r.append(tmp)

    return pretty_repr(name, r, total_len)


def fix_string_length(s: str, length: int = 10) -> str:
    """
    固定字符串长度
    Args:
        s: 原字符串
        length: 目标长度
    Returns:
        固定长度的字符串
    """
    if len(s) > length:
        return s[: length - 3] + "..."
    else:
        return s.ljust(length)


def display_dataframe(data: pd.DataFrame,
                     columns_config: Optional[Dict[str, Dict[str, Any]]] = None,
                     title: Optional[str] = None,
                     console: Optional[Console] = None) -> None:
    """
    显示DataFrame为表格
    
    Args:
        data: 要显示的DataFrame
        columns_config: 列配置字典，格式：{"column_name": {"display_name": "Display Name", "style": "dim"}}
        title: 表格标题
        console: Rich Console实例，可选
    """
    console = console or Console()
    
    if data.shape[0] == 0:
        console.print(f":exclamation: [yellow]没有数据可显示[/yellow]")
        return
    
    # 创建表格
    table = Table(show_header=True, header_style="bold magenta", title=title)
    
    # 配置列
    if columns_config:
        for col_name, config in columns_config.items():
            if col_name in data.columns:
                display_name = config.get("display_name", col_name)
                style = config.get("style", "")
                table.add_column(display_name, style=style)
    else:
        # 默认：添加所有列
        for col in data.columns:
            table.add_column(col, style="dim")
    
    # 添加行
    for _, row in data.iterrows():
        if columns_config:
            row_data = []
            for col_name in columns_config.keys():
                if col_name in data.columns:
                    value = row[col_name]
                    row_data.append(str(value) if value is not None else "")
            table.add_row(*row_data)
        else:
            table.add_row(*[str(row[col]) if row[col] is not None else "" for col in data.columns])
    
    # 显示表格
    console.print(table)
    
    # 显示数据统计
    console.print(f"[dim]总计: {data.shape[0]} 条记录[/dim]")






def display_dataframe_interactive(data: pd.DataFrame,
                                 columns_config: Optional[Dict[str, Dict[str, Any]]] = None,
                                 title: Optional[str] = None,
                                 page_size: int = 20,
                                 enable_interactive: bool = True,
                                 console: Optional[Console] = None) -> None:
    """
    显示DataFrame，支持交互式分页
    
    Args:
        data: 要显示的DataFrame
        columns_config: 列配置字典，格式：{"column_name": {"display_name": "Display Name", "style": "dim"}}
        title: 表格标题
        page_size: 每页显示的行数
        enable_interactive: 是否启用交互模式
        console: Rich Console实例，可选
    """
    console = console or Console()
    
    if not enable_interactive or data.shape[0] <= page_size:
        # 非交互模式或数据量少，直接显示
        display_dataframe(data, columns_config, title, console)
        return
    
    # 交互模式 - 内部实现所有分页和交互逻辑
    if data.shape[0] == 0:
        console.print(f":exclamation: [yellow]没有数据可显示[/yellow]")
        return
    
    # 分页变量
    page_size = max(1, page_size)
    current_page = 0
    total_pages = (data.shape[0] + page_size - 1) // page_size
    
    
    def _render_current_page():
        """渲染当前页面"""
        # 计算当前页数据
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, data.shape[0])
        current_data = data.iloc[start_idx:end_idx]
        
        # 简化标题，只显示名称
        page_title = title or "数据表格"
        
        # 创建表格
        table = Table(show_header=True, header_style="bold magenta", title=page_title)
        
        # 配置列
        if columns_config:
            for col_name, config in columns_config.items():
                if col_name in data.columns:
                    display_name = config.get("display_name", col_name)
                    style = config.get("style", "")
                    table.add_column(display_name, style=style)
        else:
            # 默认：添加所有列
            for col in data.columns:
                table.add_column(col, style="dim")
        
        # 添加行
        for _, row in current_data.iterrows():
            if columns_config:
                row_data = []
                for col_name in columns_config.keys():
                    if col_name in data.columns:
                        value = row[col_name]
                        row_data.append(str(value) if value is not None else "")
                table.add_row(*row_data)
            else:
                table.add_row(*[str(row[col]) if row[col] is not None else "" for col in data.columns])
        
        return table
    
    # 主交互循环
    while True:
        # 重新计算总页数（页面大小可能改变）
        total_pages = (data.shape[0] + page_size - 1) // page_size
        
        # 清屏并显示内容（优化后的显示顺序）
        console.clear()
        
        # 1. 表头和表格
        table = _render_current_page()
        console.print(table)
        
        # 2. 状态信息（合并到一行）
        status_parts = [f"总计: {data.shape[0]} 条记录", f"页面大小: {page_size}"]
        if total_pages > 1:
            start_idx = current_page * page_size + 1
            end_idx = min((current_page + 1) * page_size, data.shape[0])
            status_parts.append(f"当前页面: 第{current_page + 1}/{total_pages}页 ({start_idx}-{end_idx})")
        console.print(" | ".join(status_parts))
        
        # 3. 单键翻页逻辑
        try:
            import sys
            import select
            import time
            import termios
            import tty

            if total_pages > 1:
                console.print("\n[bold green]单键翻页模式[/bold green]")
                console.print("按 [bold yellow]n[/bold yellow] 下一页, [bold yellow]p[/bold yellow] 上一页, [bold yellow]q[/bold yellow] 退出")

                # 尝试设置终端为原始模式
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    # 设置终端为原始模式（无缓冲）
                    tty.setraw(sys.stdin.fileno())

                    # 设置标准输入为非阻塞
                    import fcntl
                    fd = sys.stdin.fileno()
                    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

                    while True:
                        # 清空缓冲区
                        try:
                            while True:
                                sys.stdin.read(1)
                        except:
                            pass

                        # 非阻塞检查用户输入，等待0.5秒
                        if select.select([sys.stdin], [], [], 0.5)[0]:
                            try:
                                key = sys.stdin.read(1).strip().lower()
                                if key == 'n':
                                    # 下一页
                                    if current_page < total_pages - 1:
                                        current_page += 1
                                    else:
                                        console.print(f"\n[bold blue]已到达最后一页 (第{total_pages}页)[/bold blue]")
                                        break
                                    continue
                                elif key == 'p':
                                    # 上一页
                                    if current_page > 0:
                                        current_page -= 1
                                    continue
                                elif key == 'q':
                                    # 退出
                                    console.print("\n[yellow]用户退出[/yellow]")
                                    break
                                # 忽略其他按键
                            except:
                                pass
                        else:
                            # 没有输入时，等待一段时间再检查
                            time.sleep(0.1)
                            continue

                finally:
                    # 恢复终端设置
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            else:
                # 只有一页时
                time.sleep(2)
                break

        except (KeyboardInterrupt, EOFError):
            break
        except (ImportError, AttributeError):
            # 如果Unix终端设置失败，尝试Windows方案
            try:
                import msvcrt
                import time

                if total_pages > 1:
                    console.print("\n[bold green]单键翻页模式[/bold green]")
                    console.print("按 [bold yellow]n[/bold yellow] 下一页, [bold yellow]p[/bold yellow] 上一页, [bold yellow]q[/bold yellow] 退出")

                    while True:
                        if msvcrt.kbhit():
                            key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                            if key == 'n':
                                if current_page < total_pages - 1:
                                    current_page += 1
                                else:
                                    console.print(f"\n[bold blue]已到达最后一页 (第{total_pages}页)[/bold blue]")
                                    break
                            elif key == 'p':
                                if current_page > 0:
                                    current_page -= 1
                            elif key == 'q':
                                console.print("\n[yellow]用户退出[/yellow]")
                                break
                        else:
                            time.sleep(0.1)
                else:
                    time.sleep(2)
                    break

            except ImportError:
                # 如果所有单键方案都失败，回退到原有模式
                raise
            except Exception as e:
                # 其他异常也回退到原有模式
                raise

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as e:
            # 如果非阻塞输入失败，回退到原有模式
            if total_pages > 1:
                prompt_text = "按Enter下一页 | n(下一页) | p(上一页) | q(退出) > "
            else:
                prompt_text = "按Enter或q(退出) > "
            user_input = Prompt.ask(prompt_text, default="").strip().lower()

            if user_input == "" or user_input.startswith('n'):
                if current_page < total_pages - 1:
                    current_page += 1
                else:
                    break
            elif user_input.startswith('p'):
                if current_page > 0:
                    current_page -= 1
            elif user_input.startswith('q'):
                break


def display_terminal_chart(data: pd.DataFrame,
                          title: Optional[str] = None,
                          max_points: int = 100,
                          console: Optional[Console] = None) -> None:
    """
    显示静态终端图表
    
    Args:
        data: 要显示的DataFrame，必须包含timestamp和value列
        title: 图表标题
        max_points: 最大显示点数，超过则自动重采样
        console: Rich Console实例，可选
    """
    console = console or Console()
    
    # 数据验证
    if data.shape[0] == 0:
        console.print(f":exclamation: [yellow]没有数据可显示[/yellow]")
        return
    
    required_columns = {"timestamp", "value"}
    if not required_columns.issubset(set(data.columns)):
        missing = required_columns - set(data.columns)
        console.print(f":x: [red]缺少必要的列: {missing}[/red]")
        console.print("数据必须包含 'timestamp' 和 'value' 列")
        return
    
    # 导入plotext
    try:
        import plotext as plt
        import shutil
    except ImportError:
        console.print(f":x: [red]Terminal chart failed: Missing required dependency[/red]")
        console.print(f"[yellow]plotext package not found.[/yellow]")
        console.print(f"[cyan]解决方案: pip install plotext[/cyan]")
        return
    
    # 排序数据
    data_sorted = data.sort_values(by="timestamp").copy()
    
    # 自动重采样（如果数据点过多）
    if data_sorted.shape[0] > max_points:
        console.print(f"[dim]数据点过多 ({data_sorted.shape[0]} > {max_points})，自动重采样...[/dim]")
        # 使用智能重采样（从交互版本中提取逻辑）
        display_data = _smart_resample_for_chart(data_sorted, max_points)
        console.print(f"[dim]重采样后显示 {display_data.shape[0]} 个关键数据点[/dim]")
    else:
        display_data = data_sorted
    
    # 渲染图表
    _render_terminal_chart(display_data, title, console)


def _smart_resample_for_chart(data: pd.DataFrame, target_points: int) -> pd.DataFrame:
    """
    为图表进行智能重采样，保留关键数据点
    
    Args:
        data: 已排序的DataFrame数据
        target_points: 目标点数
    
    Returns:
        重采样后的DataFrame
    """
    if data.shape[0] <= target_points:
        return data.copy()
    
    # 简单均匀采样（保留首尾）
    indices = [0]  # 保留第一个点
    
    # 计算均匀间隔
    step = (data.shape[0] - 1) / (target_points - 1)
    for i in range(1, target_points - 1):
        idx = int(round(i * step))
        indices.append(idx)
    
    indices.append(data.shape[0] - 1)  # 保留最后一个点
    
    # 去重并排序
    indices = sorted(list(set(indices)))
    
    return data.iloc[indices].copy()


def display_terminal_chart_interactive(data: pd.DataFrame,
                                     title: Optional[str] = None,
                                     max_points_per_page: int = 50,
                                     enable_interactive: bool = True,
                                     console: Optional[Console] = None) -> None:
    """
    显示终端图表，支持交互式分页
    
    Args:
        data: 要显示的DataFrame，必须包含timestamp和value列
        title: 图表标题
        max_points_per_page: 每页显示的最大数据点数
        enable_interactive: 是否启用交互模式
        console: Rich Console实例，可选
    """
    console = console or Console()
    
    # 数据验证
    if data.shape[0] == 0:
        console.print(f":exclamation: [yellow]没有数据可显示[/yellow]")
        return
    
    required_columns = {"timestamp", "value"}
    if not required_columns.issubset(set(data.columns)):
        missing = required_columns - set(data.columns)
        console.print(f":x: [red]缺少必要的列: {missing}[/red]")
        console.print("数据必须包含 'timestamp' 和 'value' 列")
        return
    
    # 导入plotext
    try:
        import plotext as plt
        import shutil
    except ImportError:
        console.print(f":x: [red]Terminal mode failed: Missing required dependency[/red]")
        console.print(f"[yellow]plotext package not found.[/yellow]")
        console.print(f"[cyan]解决方案: pip install plotext[/cyan]")
        return
    
    # 排序数据
    data_sorted = data.sort_values(by="timestamp").copy()
    
    # 非交互模式或数据量少，直接显示
    if not enable_interactive or data_sorted.shape[0] <= max_points_per_page:
        _render_terminal_chart(data_sorted, title, console)
        return
    
    # 交互模式 - 分页显示
    current_page = 0
    total_pages = (data_sorted.shape[0] + max_points_per_page - 1) // max_points_per_page
    
    console.print(f"数据概览: {data_sorted.shape[0]} 条记录")
    console.print(f"分页模式: 每页 {max_points_per_page} 个数据点，共 {total_pages} 页")
    
    # 主交互循环
    while True:
        # 计算当前页数据
        start_idx = current_page * max_points_per_page
        end_idx = min(start_idx + max_points_per_page, data_sorted.shape[0])
        current_data = data_sorted.iloc[start_idx:end_idx]
        
        # 清屏并显示图表
        console.clear()
        
        # 生成页面标题
        page_title = f"{title or 'Terminal Chart'} [第{current_page + 1}/{total_pages}页] ({start_idx + 1}-{end_idx}/{data_sorted.shape[0]})"
        
        # 渲染图表
        _render_terminal_chart(current_data, page_title, console)
        
        # 状态信息
        console.print(f"页面: 第{current_page + 1}/{total_pages}页 | 数据点: {start_idx + 1}-{end_idx}/{data_sorted.shape[0]}")
        
        # 操作提示与输入
        try:
            if total_pages > 1:
                prompt_text = "按Enter下一页 | n(下一页) | p(上一页) | q(退出) > "
            else:
                prompt_text = "按Enter或q(退出) > "
            user_input = Prompt.ask(prompt_text, default="").strip().lower()
        except (KeyboardInterrupt, EOFError):
            break
        
        # 处理用户输入
        if user_input == "" or user_input.startswith('n'):
            # 空输入或n命令 = 下一页
            if current_page < total_pages - 1:
                current_page += 1
            else:
                # 已经是最后一页，自动退出
                break
        elif user_input.startswith('p'):
            # 上一页
            if current_page > 0:
                current_page -= 1
        elif user_input.startswith('q'):
            # 退出
            break


def _render_terminal_chart(data: pd.DataFrame, title: Optional[str], console: Optional[Console]) -> None:
    """
    渲染单个终端图表
    
    Args:
        data: 已排序的DataFrame数据
        title: 图表标题
        console: Rich Console实例
    """
    try:
        import plotext as plt
        import shutil
    except ImportError:
        console.print(f":x: [red]plotext not available[/red]")
        return
    
    console = console or Console()
    
    # 获取终端尺寸
    terminal_width = shutil.get_terminal_size()[0]
    terminal_height = 30
    
    try:
        # 清理plotext图形
        plt.clear_figure()
        plt.title(title or "Terminal Chart")
        plt.plotsize(terminal_width, terminal_height)
        
        # 处理时间轴标签 - 使用plotext要求的格式
        time_labels = data["timestamp"].dt.strftime("%d/%m/%Y").tolist()
        values = data["value"].tolist()
        
        console.print(f"[dim]绘制 {len(time_labels)} 个数据点[/dim]")
        
        # 绘制图表
        plt.plot(time_labels, values)
        plt.grid(True)
        plt.theme("pro")
        plt.show()
        
    except Exception as e:
        console.print(f":x: [red]图表渲染失败: {type(e).__name__}[/red]")
        console.print(f"[yellow]错误详情: {str(e)}[/yellow]")
        console.print(f"[dim]数据列: {data.columns.tolist()}[/dim]")
        console.print(f"[dim]数据形状: {data.shape}[/dim]")