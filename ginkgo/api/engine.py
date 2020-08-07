from ginkgo.libs.yellowprint import YellowPrint
from ginkgo.libs.response import NoException

yp_engine = YellowPrint('rp_engine', url_prefix='/engine')


@yp_engine.route('/start', methods=['POST'])
def engine_start():
    return NoException('Nothing goes wrong!!')


@yp_engine.route('/sleep', methods=['POST'])
def engine_sleep():
    return NoException('All threades killed')
