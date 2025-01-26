import signal
import pandas as pd
import shutil


class TerminalCandle:
    """
    一个用于处理终端蜡烛图相关操作的类。
    """

    def __init__(self, *args, **kwargs):
        self._raw = pd.DataFrame()
        self._min_width = 60
        self._min_height = 40
        self._width = self.get_terminal_size()[0]
        self._height = self.get_terminal_size()[1]
        self._index = 0
        self._title = "default"

    def get_terminal_size(self):
        """
        获取当前终端的宽度和高度（列数和行数）。

        使用 `shutil.get_terminal_size()` 方法获取终端的尺寸信息，
        并返回一个包含宽度和高度的元组。

        Returns:
            tuple[int, int]: 一个包含两个元素的元组，第一个元素是终端的宽度（列数）， 第二个元素是终端的高度（行数）。
        """
        size = shutil.get_terminal_size()
        return (size.columns, size.lines)

    def on_terminal_resize(self, signum, frame):
        new_size = get_terminal_size()
        print("New size: ", new_size)

    def set_title(self, title: str):
        self._title = title

    def set_size(self, width: int, height: int):
        """
        设置终端的宽度和高度。
        """
        width = int(width)
        height = int(height)
        current_size = self.get_terminal_size()
        if width > current_size[0]:
            raise ValueError("Can not set width larger than current width.")
        if height > current_size[1]:
            raise ValueError("Can not set height larget than current height.")

    def show(self):
        pass

    def set_data(self, data_raw: pd.DataFrame):
        # Validation
        if not self.validate_dataframe(data_raw):
            return
        self._raw = data_raw

    def validate_dataframe(self, data_raw):
        """
        验证数据是否符合要求
        """
        exsisting = set(data_raw.columns)
        required = set(["timestamp", "open", "high", "low", "close"])
        if required.issubset(exsisting):
            return True
        else:
            missing = required - exsisting
            print("Missing columns: ", missing)
            return False
