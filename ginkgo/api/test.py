from ginkgo.libs.yellowprint import YellowPrint
# from ginkgo.test.u_backtest import u_backtest_boost, unit_test_feed, unit_test_engine_sleep
from ginkgo.test.test_data import update_all_data
from ginkgo.libs.response import NoException
import threading
from ginkgo.libs.thread_manager import thread_manager

yp_test = YellowPrint('rp_test', url_prefix='/test')


# 单元测试
@yp_test.route('/backtest_boost', methods=['POST'])
def backtest():
    print('start backtest!')
    # u_backtest_boost()
    return NoException(msg='Start backtest successful1122!!')

@yp_test.route('/all', methods=['POST'])
def update_all():
    t = threading.Thread(target=update_all_data,name='DataUpdate Thread')
    thread_manager.thread_register(t)
    return NoException(msg='开始更新所有数据')


@yp_test.route('/backtest_feed', methods=['POST'])
def backtest_feed():
    print('start feed!')
    # unit_test_feed()
    return NoException(msg='Unit_backtest began to feed now!!!')

@yp_test.route('/backtest_sleep', methods=['POST'])
def backtest_sleep():
    print('Engine sleep!')
    # unit_test_engine_sleep()
    return NoException(msg='Unit_backtest has sleep!!!')
