import pandas as pd
import shutil
import plotext as plt


class TerminalCandle:
    """
    一个用于处理终端蜡烛图相关操作的类。
    """

    def __init__(self, data=None, title=None, *args, **kwargs):
        self._raw = pd.DataFrame()
        self._height = 30
        self._width = shutil.get_terminal_size()[0]
        self._title = "TerminalCandle"
        if data is not None:
            self.set_data(data)
        if title is not None:
            self.set_title(title)

    def set_title(self, title: str, *args, **kwargs):
        self._title = title

    def show(self):
        if self._raw.shape[0] == 0:
            return
        max_count = self._width - 10
        ratio = 3.2
        max_count = int(max_count / ratio)
        if self._raw.shape[0] > max_count:
            data_count = max_count
        else:
            data_count = self._raw.shape[0]

        show_data = self._raw[:data_count]
        plt.title(self._title)
        plt.plotsize(self._width, self._height)
        plt.candlestick(data=show_data, dates=show_data["timestamp"].dt.strftime("%d/%m/%Y"), colors=["green", "red"])
        plt.grid(True)  # 关闭网格
        plt.theme("pro")
        # plt.xlabel("Date")
        # plt.ylabel("Price")
        plt.show()

    def set_data(self, data_raw: pd.DataFrame):
        # Validation
        if not self.validate_dataframe(data_raw):
            return
        data_raw = data_raw.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close"})
        self._raw = data_raw.sort_values(by="timestamp")

    def validate_dataframe(self, data_raw):
        """
        验证数据是否符合要求
        """
        if data_raw.shape[0] == 0:
            return Fals
        existing = set(data_raw.columns)
        required = set(["timestamp", "open", "high", "low", "close"])
        if required.issubset(existing):
            return True
        else:
            missing = required - existing
            print("Missing columns: ", missing)
            return False
