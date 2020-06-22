"""
api模块
"""

from flask import Blueprint
from app.api.user import yp_user
from app.api.book import yp_book
from app.api.test import yp_test
from app.api.spider import yp_spider
from app.api.stock import yp_stock


def create_blueprint():
    bp = Blueprint('bp_api', __name__, url_prefix='/api')
    yp_user.register(bp)
    yp_book.register(bp)
    yp_test.register(bp)
    yp_spider.register(bp)
    yp_stock.register(bp)
    return bp
