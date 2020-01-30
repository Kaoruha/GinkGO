from flask import request
from wtforms import Form
from libs.error_code import TestError


class BaseForm(Form):
    def __init__(self):
        data = request.json
        super(BaseForm, self).__init__(data=data)

    def validate_for_api(self):
        valid = super(BaseForm, self).validate()
        if not valid:
            raise TestError(msg=self.errors)
        return self
