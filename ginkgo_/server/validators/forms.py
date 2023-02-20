from wtforms import StringField, IntegerField, BooleanField, FileField
from wtforms.validators import DataRequired, length, Regexp
from ..models.user import User

from ..validators.base import BaseForm
from wtforms import Form


class ClientForm(BaseForm):
    account = StringField(validators=[
        DataRequired(message='不允许为空'),
        length(min=4, max=32)
    ])
    password = StringField()

class GameForm(BaseForm):
    name = StringField(validators=[
        DataRequired(message='不允许为空'),
        length(min=4, max=32)
    ])
    description = StringField()

class HospitalForm(BaseForm):
    name = StringField(validators=[
        DataRequired(message='不允许为空'),
        length(min=2, max=32)
    ])
    description = StringField()
    scale = StringField()
    type_ = StringField()


class TokenForm(Form):
    token = StringField(validators=[DataRequired()])


class FilterForm(BaseForm):
    start_row = IntegerField()
    count = IntegerField()
    account_filter = StringField()
    sort_by = StringField()
    descending = BooleanField()


class TagForm(BaseForm):
    name = StringField()
    description = StringField()
    icon_url = StringField()


class TagImageForm(Form):
    file = FileField()  # TODO 文件类型校验
    id = IntegerField()