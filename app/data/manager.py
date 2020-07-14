"""
负责数据相关的线程调度
"""


class DataManager(object):
    __thread_dict = dict()

    @classmethod
    def thread_register(cls, thread):
        """
        子线程注册
        1、判断子线程是否存在
        2、如果不存在，则注册到__thread_dict
        3、同时开启线程
        :param thread:
        :return: 是否注册成功的文本信息
        """
        cls.kill_dead_thread()
        if cls.is_thread_exist(thread):
            res = thread.name + ' already exist!'
        else:
            cls.__thread_dict[thread.name] = thread
            thread.start()
            res = thread.name + ' added!!'
        print(res)

    @classmethod
    def is_thread_exist(cls, thread):
        """
        判断子线程是否已经存在
        :param thread: 传入线程
        :return: 如果存在返回True，否则返回False
        """
        cls.kill_dead_thread()
        if thread.name in cls.__thread_dict:
            return True
        else:
            return False

    @classmethod
    def kill_all(cls):
        """
        杀掉列表中所有线程
        :return:
        """
        for p in cls.__thread_dict:
            if cls.__thread_dict[p].is_alive():
                cls.__thread_dict[p].terminate()
                msg = p + ' closed!'
                print(msg)
        cls.__thread_dict.clear()

    @classmethod
    def kill_dead_thread(cls):
        for p in cls.__thread_dict:
            if not cls.__thread_dict[p].is_alive():
                cls.__thread_dict.pop(p, None)
                msg = p + ' popped!'
                print(msg)
        cls.__thread_dict.clear()


def kill_all_thread():
    """
    停止所有数据获取相关线程
    :return:
    """
    try:
        DataManager.kill_all()
    except Exception as e:
        raise e
    return
