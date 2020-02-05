from sqlalchemy import Column, String, Integer
from app.models.base import Base, db

record_table_mapper = {}


class RecordBase(Base):
    __tablename__ = 'default'
    record_id = Column(Integer(), primary_key=True)
    name = Column(String(20))
    version_id = Column(String(20))

    def __init__(self):
        pass

    def show_name(self):
        print(self.name)

    def test(self, name):
        table_name = name
        if table_name not in record_table_mapper:
            t = type(table_name, (RecordBase,), {'__tablename__': table_name})
            record_table_mapper[name] = t
        print(t.hello)
        print(record_table_mapper[name].hello)
