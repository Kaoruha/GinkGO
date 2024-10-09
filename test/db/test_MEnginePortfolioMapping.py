# import unittest
# import uuid
# import random
# import time
# import pandas as pd
# import datetime

# from ginkgo.libs.ginkgo_normalize import datetime_normalize
# from ginkgo.data.models import MEnginePortfolioMapping
# from ginkgo.enums import SOURCE_TYPES


# class ModelEnginePortfolioMappingTest(unittest.TestCase):
#     """
#     UnitTest for Bar.
#     """

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelEnginePortfolioMappingTest, self).__init__(*args, **kwargs)
#         self.count = 10
#         self.model = MEnginePortfolioMapping
#         self.params = [
#             {
#                 "engine_id": uuid.uuid4().hex,
#                 "portfolio_id": uuid.uuid4().hex,
#                 "source": random.choice([i for i in SOURCE_TYPES]),
#             }
#             for i in range(self.count)
#         ]

#     def test_ModelEnginePortfolioMapping_Init(self) -> None:
#         for i in self.params:
#             o = self.model(engine_id=i["engine_id"], portfolio_id=i["portfolio_id"], source=i["source"])
#             self.assertEqual(o.engine_id, i["engine_id"])
#             self.assertEqual(o.portfolio_id, i["portfolio_id"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelEnginePortfolioMapping_SetFromData(self) -> None:
#         for i in self.params:
#             o = self.model()
#             o.update(i["engine_id"])
#             self.assertEqual(o.engine_id, i["engine_id"])
#             o.update(i["engine_id"], portfolio_id=i["portfolio_id"])
#             self.assertEqual(o.portfolio_id, i["portfolio_id"])
#             o.update(i["engine_id"], source=i["source"])
#             self.assertEqual(o.source, i["source"])

#         for i in self.params:
#             o = self.model()
#             o.update(i["engine_id"], portfolio_id=i["portfolio_id"], source=i["source"])
#             self.assertEqual(o.engine_id, i["engine_id"])
#             self.assertEqual(o.portfolio_id, i["portfolio_id"])
#             self.assertEqual(o.source, i["source"])

#     def test_ModelEnginePortfolioMapping_SetFromDataFrame(self) -> None:
#         for i in self.params:
#             df = pd.DataFrame.from_dict(i, orient="index")[0]
#             o = self.model()
#             o.update(df)
#             self.assertEqual(o.engine_id, i["engine_id"])
#             self.assertEqual(o.portfolio_id, i["portfolio_id"])
#             self.assertEqual(o.source, i["source"])
