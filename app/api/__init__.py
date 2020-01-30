from flask import Blueprint
from api.user import yp_user
from api.book import yp_book


def create_blueprint():
    bp = Blueprint('bp_api', __name__, url_prefix='/api')
    yp_user.register(bp)
    yp_book.register(bp)
    return bp
