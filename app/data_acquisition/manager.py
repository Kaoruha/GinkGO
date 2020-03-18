"""
负责代理相关的线程调度
"""


class SpiderManager(object):
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
        if cls.is_process_exist(process):
            res = process.name + ' already exist!'
        else:
            cls.__process_dict[process.name] = process
            process.start()
            res = process.name + ' added!!'
        print(res)
        return process

    @classmethod
    def is_process_exist(cls, process):
        """
        判断子进程是否已经存在
        :param process:
        :return: 如果存在返回True，否则返回False
        """
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
        return 'Doen'


def kill_all_process():
    try:
        SpiderManager.kill_all()
    except Exception as e:
        raise e
    return 'OK'
