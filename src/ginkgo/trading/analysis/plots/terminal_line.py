import pandas as pd
import shutil
import plotext as plt
import numpy as np
import sys
import termios
import tty
from typing import Optional, Tuple


class TerminalLine:
    """
    一个用于处理终端线图显示的类，支持智能数据采样和分页功能。
    
    功能特性:
    - 根据终端宽度自动计算最大显示点数
    - 智能采样保留峰值和转折点
    - 分页模式支持方向键翻页
    - 时间轴标签自动优化避免重叠
    
    使用示例:
    ```python
    import pandas as pd
    from terminal_line import TerminalLine
    
    # 创建示例数据
    data = pd.DataFrame({'timestamp': pd.date_range('2023-01-01', periods=1000, freq='D'),
                        'value': np.random.randn(1000).cumsum()})
    
    # 基本使用
    plot = TerminalLine(title="股价走势")
    plot.set_data(data)
    plot.show()  # 自动智能采样
    
    # 分页模式
    plot.set_pagination(True)
    plot.show()  # 使用方向键翻页
    
    # 自定义最大点数
    plot.set_max_points(200)
    plot.show()
    ```
    """

    def __init__(self, data=None, title=None, *args, **kwargs):
        self._raw = pd.DataFrame()
        self._height = 30
        self._width = shutil.get_terminal_size()[0]
        self._title = "TerminalLine"
        self._pagination_enabled = False
        self._current_page = 0
        self._max_points_override = None
        if data is not None:
            self.set_data(data)
        if title is not None:
            self.set_title(title)

    def set_title(self, title: str, *args, **kwargs):
        self._title = title
    
    def set_pagination(self, enabled: bool = True):
        """启用或禁用分页模式"""
        self._pagination_enabled = enabled
        self._current_page = 0
    
    def set_max_points(self, count: Optional[int] = None):
        """手动设置最大显示点数"""
        self._max_points_override = count
    
    def _calculate_max_points(self) -> int:
        """根据终端宽度计算最大可显示的数据点数"""
        if self._max_points_override is not None:
            return self._max_points_override
        
        # 参考terminal_candle的逻辑，但线图比蜡烛图更紧凑
        available_width = self._width - 15  # 留出边距和轴标签空间
        ratio = 2.0  # 线图比蜡烛图(3.2)更紧凑
        max_points = int(available_width / ratio)
        return max(max_points, 50)  # 最少显示50个点
    
    def _detect_peaks_and_turns(self, data: pd.DataFrame, window: int = 5) -> list[int]:
        """检测峰值和转折点的索引"""
        if data.shape[0] < window * 2:
            return list(range(data.shape[0]))
        
        values = data['value'].values
        important_indices = set()
        
        # 1. 检测局部极值点（峰值和谷值）
        for i in range(window, len(values) - window):
            local_window = values[i-window:i+window+1]
            center_value = values[i]
            
            # 局部最大值（峰值）
            if center_value == max(local_window):
                important_indices.add(i)
            # 局部最小值（谷值）
            elif center_value == min(local_window):
                important_indices.add(i)
        
        # 2. 检测转折点（方向变化）
        if len(values) > 3:
            # 计算变化率
            diff = np.diff(values)
            # 检测符号变化（转折点）
            for i in range(1, len(diff) - 1):
                if (diff[i-1] > 0 > diff[i]) or (diff[i-1] < 0 < diff[i]):
                    important_indices.add(i)
        
        # 3. 确保包含首尾点
        important_indices.add(0)
        important_indices.add(len(values) - 1)
        
        return sorted(list(important_indices))
    
    def _smart_resample(self, data: pd.DataFrame, target_points: int) -> pd.DataFrame:
        """智能重采样，保留峰值和转折点"""
        if data.shape[0] <= target_points:
            return data.copy()
        
        # 检测重要点
        important_indices = self._detect_peaks_and_turns(data)
        
        # 如果重要点数量已经超过目标点数，进行优先级筛选
        if len(important_indices) > target_points:
            # 计算每个重要点的"重要程度"
            values = data['value'].values
            importance_scores = []
            
            for idx in important_indices:
                if idx == 0 or idx == len(values) - 1:
                    # 首尾点最重要
                    importance_scores.append(float('inf'))
                else:
                    # 计算局部变化幅度作为重要程度
                    window = min(5, idx, len(values) - idx - 1)
                    local_values = values[max(0, idx-window):min(len(values), idx+window+1)]
                    local_range = max(local_values) - min(local_values)
                    importance_scores.append(local_range)
            
            # 按重要程度排序，保留前target_points个
            sorted_pairs = sorted(zip(important_indices, importance_scores), 
                                key=lambda x: x[1], reverse=True)
            important_indices = sorted([pair[0] for pair in sorted_pairs[:target_points]])
        
        # 如果重要点不够，均匀补充其他点
        elif len(important_indices) < target_points:
            remaining_points = target_points - len(important_indices)
            all_indices = set(range(data.shape[0]))
            available_indices = all_indices - set(important_indices)
            
            if available_indices:
                # 均匀选择剩余点
                step = max(1, len(available_indices) // remaining_points)
                additional_indices = sorted(list(available_indices))[::step][:remaining_points]
                important_indices.extend(additional_indices)
                important_indices = sorted(important_indices)
        
        return data.iloc[important_indices].copy()
    
    def _get_pagination_info(self, data_size: int, max_points: int) -> Tuple[int, int]:
        """计算分页信息：总页数和当前页数据范围"""
        total_pages = (data_size + max_points - 1) // max_points  # 向上取整
        self._current_page = max(0, min(self._current_page, total_pages - 1))
        return total_pages, self._current_page
    
    def _get_page_data(self, data: pd.DataFrame, page: int, max_points: int) -> pd.DataFrame:
        """获取指定页的数据"""
        start_idx = page * max_points
        end_idx = min(start_idx + max_points, data.shape[0])
        return data.iloc[start_idx:end_idx].copy()
    
    def _wait_for_keypress(self) -> str:
        """等待用户按键"""
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.cbreak(fd)
            
            key = sys.stdin.read(1)
            
            # 检测方向键（ESC序列）
            if key == '\x1b':  # ESC
                key += sys.stdin.read(2)
                if key == '\x1b[D':  # 左方向键
                    return 'left'
                elif key == '\x1b[C':  # 右方向键
                    return 'right'
                else:
                    return 'esc'
            elif key == 'q' or key == 'Q':
                return 'quit'
            elif key == ' ':
                return 'space'
            else:
                return key
                
        except Exception:
            return 'quit'
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except:
                pass
    
    def _paginate_display(self, data: pd.DataFrame):
        """分页显示数据"""
        max_points = self._calculate_max_points()
        total_pages, _ = self._get_pagination_info(data.shape[0], max_points)
        
        while True:
            # 清屏
            plt.clear_figure()
            
            # 获取当前页数据
            page_data = self._get_page_data(data, self._current_page, max_points)
            
            # 生成标题（包含分页信息）
            start_idx = self._current_page * max_points
            end_idx = min(start_idx + max_points, data.shape[0])
            page_title = f"{self._title} [第{self._current_page + 1}/{total_pages}页] ({start_idx + 1}-{end_idx}/{data.shape[0]})"
            
            # 绘制图表
            plt.title(page_title)
            plt.plotsize(self._width, self._height)
            
            # 直接使用分页数据的所有时间点作为标签
            try:
                time_labels = page_data["timestamp"].dt.strftime("%d/%m/%Y")
                print(f"DEBUG[分页]: 时间标签转换成功，前3个: {time_labels.head(3).tolist()}")
                display_labels = time_labels.tolist()  # 直接使用所有分页数据的时间
                print(f"DEBUG[分页]: 标签数量: {len(display_labels)}")
            except Exception as e:
                print(f"DEBUG[分页]: 日期转换错误: {e}")
                display_labels = [str(i) for i in range(len(page_data))]
            
            plt.plot(display_labels, page_data["value"].to_list())
            plt.grid(True)
            plt.theme("pro")
            plt.show()
            
            # 显示操作提示
            print(f"\\n操作: ← 上一页 | → 下一页 | q 退出 | 当前: {self._current_page + 1}/{total_pages}")
            
            # 等待用户输入
            key = self._wait_for_keypress()
            
            if key == 'quit':
                break
            elif key == 'left' and self._current_page > 0:
                self._current_page -= 1
            elif key == 'right' and self._current_page < total_pages - 1:
                self._current_page += 1

    def show(self):
        """显示线图，支持智能采样和分页"""
        if self._raw.shape[0] == 0:
            print("没有数据可显示")
            return
        
        max_points = self._calculate_max_points()
        data_size = self._raw.shape[0]
        
        # 显示数据统计信息
        print(f"数据统计: 总计 {data_size} 个数据点，最大显示 {max_points} 个点")
        
        # 分页模式
        if self._pagination_enabled:
            print("分页模式已启用，使用方向键翻页")
            self._paginate_display(self._raw)
            return
        
        # 智能采样模式
        if data_size > max_points:
            print(f"数据点过多，使用智能采样 (保留峰值和转折点)")
            show_data = self._smart_resample(self._raw, max_points)
            print(f"采样后显示 {show_data.shape[0]} 个关键数据点")
        else:
            show_data = self._raw.copy()
        
        # 绘制图表
        plt.clear_figure()
        plt.title(self._title)
        plt.plotsize(self._width, self._height)
        
        # 调试：打印时间戳信息
        print(f"DEBUG: timestamp 列类型: {type(show_data['timestamp'].iloc[0])}")
        print(f"DEBUG: timestamp 前3个值: {show_data['timestamp'].head(3).tolist()}")
        
        # 直接使用重新采样后所有数据点的时间作为标签
        try:
            time_labels = show_data["timestamp"].dt.strftime("%d/%m/%Y")
            print(f"DEBUG: 转换后的时间标签前3个: {time_labels.head(3).tolist()}")
            display_labels = time_labels.tolist()  # 直接使用所有采样点的时间
            print(f"DEBUG: 最终显示标签数量: {len(display_labels)}, 前5个: {display_labels[:5]}")
        except Exception as e:
            print(f"DEBUG: 日期转换错误: {e}")
            # 回退到索引
            display_labels = [str(i) for i in range(len(show_data))]
        
        print(f"DEBUG: 准备绘制，x轴标签数量: {len(display_labels)}, y轴数据数量: {len(show_data['value'])}")
        plt.plot(display_labels, show_data["value"].to_list())
        plt.grid(True)
        plt.theme("pro")
        plt.show()

    def set_data(self, data_raw: pd.DataFrame):
        # Validation
        if not self.validate_dataframe(data_raw):
            return
        self._raw = data_raw.sort_values(by="timestamp")

    def validate_dataframe(self, data_raw):
        """
        验证数据是否符合要求
        """
        if data_raw.shape[0] == 0:
            return False
        existing = set(data_raw.columns)
        required = set(["timestamp", "value"])
        if required.issubset(existing):
            return True
        else:
            missing = required - existing
            print("Missing columns: ", missing)
            return False
