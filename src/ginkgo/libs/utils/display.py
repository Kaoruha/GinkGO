"""
显示和格式化工具模块
合并了原来的 ginkgo_pretty.py 和 ginkgo_color.py
提供颜色控制和格式化输出功能
"""

from types import FunctionType, MethodType
import pandas as pd
from enum import Enum


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

        if isinstance(obj.__getattribute__(param), MethodType):
            continue

        if isinstance(obj.__getattribute__(param), FunctionType):
            continue

        tmp = " " * (count - len(str(param)))
        tmp += f"{str(param).upper()}"
        s = obj.__getattribute__(param)
        filter_s = str(s).strip(b"\x00".decode())
        
        special_ins_param = [
            "engine", "matchmaking", "datafeeder", "portfolio", 
            "selector", "risk_manager", "sizer", "data_feeder",
        ]
        special_list_param = ["portfolios", "strategies", "interested", "signals", "loggers"]
        special_dict_param = ["positions", "analyzers"]
        
        if isinstance(s, pd.DataFrame):
            filter_s = f"{str(s.shape)}"
        if param in special_ins_param:
            filter_s = f"[{hex(id(s))}] {str(s.name)}" if s is not None else "None"
        if param in special_dict_param:
            filter_s = f"{len(s.keys())}"
        if param in special_list_param:
            filter_s = f"{len(s)}"
        if isinstance(s, Enum):
            filter_s += f" : {s.value}"
        if param == "subscribers":
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