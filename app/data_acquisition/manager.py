"""
负责数据相关的线程调度
"""


class DataManager(object):
    __process_dict = dict()

    @classmethod
    def process_register(cls, process):
        """
        子进程注册
        1、判断子进程是否存在
        2、如果不存在，则注册到__process_dict
        3、同时开启进程
        :param process:
        :return: 是否注册成功的文本信息
        """
        cls.kill_dead_process()
        if cls.is_process_exist(process):
            res = process.name + ' already exist!'
        else:
            cls.__process_dict[process.name] = process
            process.start()
            res = process.name + ' added!!'
        print(res)
        return

    @classmethod
    def is_process_exist(cls, process):
        """
        判断子进程是否已经存在
        :param process: 传入进程
        :return: 如果存在返回True，否则返回False
        """
        cls.kill_dead_process()
        if process.name in cls.__process_dict:
            return True
        else:
            return False

    @classmethod
    def kill_all(cls):
        """
        杀掉列表中所有进程
        :return:
        """
        for p in cls.__process_dict:
            if cls.__process_dict[p].is_alive():
                cls.__process_dict[p].terminate()
                msg = p + ' closed!'
                print(msg)
        cls.__process_dict.clear()
        return

    @classmethod
    def kill_dead_process(cls):
        for p in cls.__process_dict:
            if not cls.__process_dict[p].is_alive():
                cls.__process_dict.pop(p, None)
                msg = p + ' popped!'
                print(msg)
        cls.__process_dict.clear()


def kill_all_process():
    """
    停止所有数据获取相关进程
    :return:
    """
    try:
        DataManager.kill_all()
    except Exception as e:
        raise e
    return
