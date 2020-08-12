"""
负责引擎相关的线程调度
"""
import threading
from ginkgo.libs.thread_manager import thread_manager
from ginkgo.backtest.simulate_engine import Ginkgo_Engine


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

    def engine_register(self, engine: Ginkgo_Engine):
        """
        注册引擎

        :param engine: 一个引擎实例
        :type engine: Ginkgo_Engine
        """
        if engine.portfolio.name not in self.engine_list:
            portfolio_name = engine.portfolio.name
            self.engine_list[portfolio_name] = engine
            thread_name = f'{portfolio_name}\'s engine thread'
            thread = threading.Thread(target=engine_run,
                                      name=thread_name,
                                      kwargs={"engine": engine
                                              })  # kwargs 传递字典，可以同时传递多个键值对
            thread_manager.thread_register(thread)  # 线程管理,新建引擎的线程
            return f'{portfolio_name} register!'
        else:
            return f'{engine.portfolio.name} already exist!'

    def engine_sleep(self, portfolio_name):
        """
        引擎休眠
        """
        if portfolio_name in self.engine_list:
            self.engine_list[portfolio_name].engine_sleep()
            return f'{portfolio_name} sleep now.'
        else:
            return f'There is no {portfolio_name} engine.'

    def engine_resume(self, portfolio_name):
        """
        引擎恢复
        """
        if portfolio_name in self.engine_list:
            self.engine_list[portfolio_name].engine_start()
            return f'{portfolio_name} resume now.'
        else:
            return f'There is no {portfolio_name} engine.'

    def info_injection(self, portfolio_name, info):
        """
        数据注入
        """
        if portfolio_name in self.engine_list:
            self.engine_list[portfolio_name].add_info(info)
            # print(f'{portfolio_name} add 1 info.')
        else:
            return f'There is no {portfolio_name} engine.'

    def kill_all_engine_thread(self):
        """
        停止所有引擎相关线程
        :return:
        """
        # TODO
        try:
            self._instance.kill_all()
        except Exception as e:
            raise e
        return


engine_portal = EnginePortal()


def engine_run(engine:Ginkgo_Engine):
    engine._run()
