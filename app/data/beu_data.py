"""
@Author:sunny
@Create:2020-07-06  15-55-12
@Description:BlaBla
"""
import threading


class BeuData(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with BeuData._instance_lock:
                if not hasattr(cls, '_instance'):
                    BeuData._instance = super().__new__(cls)

            return BeuData._instance

    @staticmethod
    def query_stock(code, start_date, end_date, frequency):
        # 根据code与frequency 找到数据文件位置
        # 根据start_date与end_date返回数据
        pass


beu_data = BeuData()
