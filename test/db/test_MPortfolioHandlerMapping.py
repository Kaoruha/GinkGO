# import unittest
# import uuid
# import base64
# import random
# import time
# import pandas as pd
# import datetime
# from ginkgo.libs.ginkgo_normalize import datetime_normalize
# from ginkgo.data.models import MPortfolioHandlerMapping
# from ginkgo.enums import FILE_TYPES, SOURCE_TYPES


# class ModelPortfolioHandlerMappingTest(unittest.TestCase):
#     """
#     Examples for UnitTests of models Backtest
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelPortfolioHandlerMappingTest, self).__init__(*args, **kwargs)
#         self.count = 10
#         self.model = MPortfolioHandlerMapping
#         self.params = [
#             {
#                 "portfolio_id": uuid.uuid4().hex,
#                 "handler_id": uuid.uuid4().hex,
#                 "type": random.choice([i for i in FILE_TYPES]),
#                 "name": uuid.uuid4().hex,
#                 "source": random.choice([i for i in SOURCE_TYPES]),
#             }
#             for i in range(self.count)
#         ]

#     def test_ModelPortfolioHandlerMapping_Init(self) -> None:
#         for i in self.params:
#             o = self.model(portfolio_id=i["portfolio_id"], handler_id=i["handler_id"], type=i["type"], name=i["name"])
#             self.assertEqual(o.portfolio_id, i["portfolio_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.type, i["type"])
#             self.assertEqual(o.name, i["name"])

#     def test_ModelPortfolioHandlerMapping_SetFromData(self) -> None:
#         for i in self.params:
#             o = self.model()
#             # update portfolio_id
#             o.update(i["portfolio_id"])
#             self.assertEqual(o.portfolio_id, i["portfolio_id"])

#             # update handler_id
#             o.update(i["portfolio_id"], handler_id=i["handler_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])

#             # update type
#             o.update(i["portfolio_id"], type=i["type"])
#             self.assertEqual(o.type, i["type"])

#             # update map name
#             o.update(i["portfolio_id"], name=i["name"])
#             self.assertEqual(o.name, i["name"])

#         # Update all
#         for i in self.params:
#             o = self.model()
#             o.update(i["portfolio_id"], handler_id=i["handler_id"], type=i["type"], name=i["name"])
#             self.assertEqual(o.portfolio_id, i["portfolio_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.type, i["type"])
#             self.assertEqual(o.name, i["name"])

#     def test_ModelPortfolioHandlerMapping_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o = self.model()
#             o.update(df)
#             self.assertEqual(o.portfolio_id, i["portfolio_id"])
#             self.assertEqual(o.handler_id, i["handler_id"])
#             self.assertEqual(o.type, i["type"])
#             self.assertEqual(o.name, i["name"])
#             self.assertEqual(o.source, i["source"])
