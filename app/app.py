# 应用初始化
from flask import Flask
from sqlalchemy import MetaData

from app.config import secure, setting


# 注册蓝图
def reg_blueprints(app):
    from app.api import create_blueprint
    app.register_blueprint(create_blueprint())


def create_app():
    app = Flask(__name__)

    # 加载配置文件
    app.config.from_object(secure)
    app.config.from_object(setting)

    # 注册蓝图
    reg_blueprints(app)
    reg_plugins(app)

    # 跨域支持
    def after_request(resp):
        resp.headers['Access-Control-Allow-Origin'] = '*'
        return resp

    app.after_request(after_request)

    return app


# 将所有插件引入并注册
def reg_plugins(app):
    # 数据库映射
    from app.models.base import db
    db.init_app(app)
    with app.app_context():
        # 引入模型包，会加载__init__下导入的所有模型(如果表没自动生成取消下面引入的注释)
        from app import models
        db.create_all()
