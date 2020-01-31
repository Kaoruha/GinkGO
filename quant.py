# 入口文件
from werkzeug.exceptions import HTTPException

from app.app import create_app
from app.libs.error import APIException
from app.libs.error_code import ServerError

app = create_app()


@app.errorhandler(Exception)
def framework_error(e):
    # APIException
    # HTTPException
    # Exception
    if isinstance(e, APIException):
        return e
    if isinstance(e, HTTPException):
        code = e.code
        msg = e.description
        error_code = 1007
        return APIException(code=code, msg=msg, error_code=error_code)
    else:
        if app.config['DEBUG']:
            return e
        else:
            return ServerError()


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',  # 设置IP
        port=5000,  # 设置端口号
        debug=app.config['DEBUG'],  # 开启Debug模式，保存后服务器自动重启
        threaded=True  # 开启多线程
    )
