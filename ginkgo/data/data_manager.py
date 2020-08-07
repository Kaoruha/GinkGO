"""
负责数据相关的线程调度
"""
from ginkgo.libs.thread_manager import ThreadManager
data_manager = ThreadManager()


def kill_all_thread():
    """
    停止所有数据获取相关线程
    :return:
    """
    try:
        data_manager.kill_all()
    except Exception as e:
        raise e
    return
