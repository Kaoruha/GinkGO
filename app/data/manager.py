"""
负责数据相关的线程调度
"""
import threading

class DataManager(object):
    __thread_dict = dict()
    _instance_lock = threading.Lock()

    def __new__(self, *args, **kwargs):
        if not hasattr(self, '_instance'):
            with DataManager._instance_lock:
                if not hasattr(self, '_instance'):
                    DataManager._instance = super().__new__(self)

            return DataManager._instance

    def thread_register(self, thread):
        """
        子线程注册
        1、判断子线程是否存在
        2、如果不存在，则注册到__thread_dict
        3、同时开启线程
        :param thread:
        :return: 是否注册成功的文本信息
        """
        self.kill_dead_thread()
        if self.is_thread_exist(thread):
            res = thread.name + ' already exist!'
            print(res+'\n')
            return
        else:
            self.__thread_dict[thread.name] = thread
            thread.start()
            res = thread.name + ' added!!'
        print(res+'\n')

    def is_thread_exist(self, thread):
        """
        判断子线程是否已经存在
        :param thread: 传入线程
        :return: 如果存在返回True，否则返回False
        """
        if thread.name in self.__thread_dict:
            return True
        else:
            return False

    def kill_all(self):
        """
        杀掉列表中所有线程
        :return:
        """
        for p in self.__thread_dict:
            if self.__thread_dict[p].is_alive():
                self.__thread_dict[p].terminate()
                msg = p + ' closed!'
                print(msg)
        self.__thread_dict.clear()
        return

    def kill_dead_thread(self):
        dead_list = []
        for p in self.__thread_dict:
            if not self.__thread_dict[p].is_alive():
                dead_list.append(p)
        for d in dead_list:
            self.__thread_dict.pop(d)
            print(f'{d} has popped')

dm = DataManager()
def kill_all_thread():
    """
    停止所有数据获取相关线程
    :return:
    """
    try:
        dm.kill_all()
    except Exception as e:
        raise e
    return
