from ginkgo.data.models.base_model import BaseModel


class Order(BaseModel):
    __abstract__ = False
    __tablename__ = "Orders"
