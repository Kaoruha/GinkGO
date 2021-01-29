"""
负责数据相关的线程调度
"""
import threading
import queue
import time


class ThreadManager(object):
    __thread_dict = dict()
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with ThreadManager._instance_lock:
                if not hasattr(cls, '_instance'):
                    ThreadManager._instance = super().__new__(cls)

            return ThreadManager._instance

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
            print('\n' + res + '\n')
            return
        else:
            self.__thread_dict[thread.name] = thread
            thread.start()
        #     res = f'Thread:+{thread.name} added!!'
        # print(res + '\n')

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

    def kill_dead_thread(self):
        dead_list = []
        for p in self.__thread_dict:
            if not self.__thread_dict[p].is_alive():
                dead_list.append(p)
        for d in dead_list:
            self.__thread_dict.pop(d)
            # print(f'Thread:{d} has popped')

    def limit_thread_register(self, threads, thread_num):
        # 构建待插入与正在运行的线程池
        to_insert_thread = queue.Queue()
        runing_threads = {}
        for i in threads:
            to_insert_thread.put(i)
        
        # 当待insert_list与runing_threads有线程时，执行
        while True:
            if len(runing_threads) + to_insert_thread.qsize() == 0:
                break
            # 如果正在运行的线程数量小于传入的预设线程数量，则从insert_list中提取一个
            if to_insert_thread.qsize() > 0 and len(runing_threads) < thread_num:
                new_thread = to_insert_thread.get()
                runing_threads[new_thread.name] = new_thread
                self.thread_register(new_thread)
            dead_list = []
            for p in runing_threads:
                if not runing_threads[p].is_alive():
                    dead_list.append(p)
            for d in dead_list:
                runing_threads.pop(d)
            self.kill_dead_thread()
            time.sleep(2)

            


thread_manager = ThreadManager()
