import pandas as pd
import shutil
import plotext as plt


class TerminalLine:
    """
    一个用于处理终端蜡烛图相关操作的类。
    """

    def __init__(self, data=None, title=None, *args, **kwargs):
        self._raw = pd.DataFrame()
        self._height = 30
        self._width = shutil.get_terminal_size()[0]
        self._title = "TerminalLine"
        if data is not None:
            self.set_data(data)
        if title is not None:
            self.set_title(title)

    def set_title(self, title: str, *args, **kwargs):
        self._title = title

    def show(self):
        if self._raw.shape[0] == 0:
            return
        plt.title(self._title)
        show_data = self._raw.copy()
        plt.plotsize(self._width, self._height)
        plt.plot(show_data["timestamp"].dt.strftime("%d/%m/%Y"), self._raw["value"].to_list())
        plt.grid(True)  # 关闭网格
        plt.theme("pro")
        # plt.xlabel("Date")
        # plt.ylabel("Price")
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
            return Fals
        exsisting = set(data_raw.columns)
        required = set(["timestamp", "value"])
        if required.issubset(exsisting):
            return True
        else:
            missing = required - exsisting
            print("Missing columns: ", missing)
            return False
