import datetime
from mongoengine import Document, StringField, BooleanField


class BaseModel(Document):
    """
    数据Model的基类，用来设置一些的属性与方法
    """
    # __abstract__ = True  # 变成抽象类，只声明不实现
    create_time = StringField(max_length=40)
    last_updated = StringField(max_length=40)
    is_delete = BooleanField(default=False)

    meta = {'allow_inheritance': True, 'abstract': True}

    def __init__(self, *args, **kwargs):
        Document.__init__(self, *args, **kwargs)
        self.create_time = datetime.datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S')
        self.last_updated = datetime.datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S')

    def delete(self):
        """
        软删除
        """
        if self.is_delete is True:
            return
        else:
            self.is_delete = True

    def update_time(self):
        self.last_updated = datetime.datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S')