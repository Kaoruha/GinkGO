"""
负责引擎相关的线程调度
"""
import threading
from ginkgo.libs.thread_manager import ThreadManager

engine_manager = ThreadManager()
engine_list = []


def enging_register(portfolio_id: int):
    if portfolio_id not in engine_list:
        # 注册、启动
        pass


def kill_all_engine_thread():
    """
    停止所有引擎相关线程
    :return:
    """
    try:
        engine_manager.kill_all()
    except Exception as e:
        raise e
    return
