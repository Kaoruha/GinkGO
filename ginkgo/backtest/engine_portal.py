"""
负责引擎相关的线程调度
"""
import threading
from ginkgo.libs.thread_manager import ThreadManager


class EnginePortal(ThreadManager):
    engine_list = {}
    def __new__(self, *args, **kwargs):
        if not hasattr(self, '_instance'):
            with EnginePortal._instance_lock:
                if not hasattr(self, '_instance'):
                    EnginePortal._instance = super().__new__(self)

            return EnginePortal._instance
  
    def engine_register(self, engine, portfolio):
        if portfolio.name not in self.engine_list:
            self.engine_list[portfolio.name] = engine
            t = threading.Thread(target=engine_run,
                          kwargs={"engine":engine}) # kwargs 传递字典，可以同时传递多个键值对
            self._instance.thread_register(t)
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