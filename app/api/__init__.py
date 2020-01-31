from flask import Blueprint
from app.api.user import yp_user
from app.api.book import yp_book
from app.api.test import yp_test


def create_blueprint():
    bp = Blueprint('bp_api', __name__, url_prefix='/api')
    yp_user.register(bp)
    yp_book.register(bp)
    yp_test.register(bp)
    return bp
