"""
基于Flask的web api模块
"""

from flask import Blueprint
from ginkgo.api.user import yp_user
from ginkgo.api.test import yp_test
from ginkgo.api.spider import yp_spider
from ginkgo.api.stock import yp_stock
from ginkgo.api.engine import yp_engine


def create_blueprint():
    bp = Blueprint('bp_api', __name__, url_prefix='/api')
    yp_user.register(bp)
    yp_test.register(bp)
    yp_spider.register(bp)
    yp_stock.register(bp)
    yp_engine.register(bp)
    return bp
