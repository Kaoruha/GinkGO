from flask import request
from wtforms import Form
from ginkgo.libs.error_code import ParameterException


class BaseForm(Form):
    # 网络请求相关的元表单
    # 数据传输为Json
    def __init__(self):
        data = request.get_json(silent=True)
        args = request.args.to_dict()
        super(BaseForm, self).__init__(data=data, **args)

    def validate_for_api(self):
        valid = super(BaseForm, self).validate()
        if not valid:
            # form errors
            raise ParameterException(msg=self.errors)
        return self
