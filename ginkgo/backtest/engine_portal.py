"""
负责引擎相关的线程调度
"""
import threading
from ginkgo.libs.thread_manager import thread_manager


class EnginePortal(object):
    _instance_lock = threading.Lock()
    __thread_dict = dict()
    engine_list = {}

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            with EnginePortal._instance_lock:
                if not hasattr(cls, '_instance'):
                    EnginePortal._instance = super().__new__(cls)
            return EnginePortal._instance
  
    def engine_register(self, engine, portfolio):
        if portfolio.name not in self.engine_list:
            self.engine_list[portfolio.name] = engine
            thread = threading.Thread(target=engine_run,
                          kwargs={"engine":engine}) # kwargs 传递字典，可以同时传递多个键值对
            thread_manager.thread_register(thread) # 线程管理,新建引擎的线程
        else:
            print(f'{portfolio.name} already exsist!')

    def engine_sleep(self, portfolio_name):
        if portfolio_name in self.engine_list:
            self.engine_list[portfolio_name].engine_sleep()
            print(f'{self.engine_list[portfolio_name]} sleep now.')
        else:
            print(f'There is no {self.engine_list[portfolio_name]} engine.')

    def kill_all_engine_thread(self):
        """
        停止所有引擎相关线程
        :return:
        """
        try:
            self._instance.kill_all()
        except Exception as e:
            raise e
        return


engine_portal = EnginePortal()

def engine_run(engine):
    engine._run()