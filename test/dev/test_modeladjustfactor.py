# import unittest
# import time
# import datetime
# import pandas as pd
# from ginkgo.libs import GINKGOLOGGER as gl
# from ginkgo.data.ginkgo_data import GINKGODATA
# from ginkgo.data.models.model_adjustfactor import MAdjustfactor
# from ginkgo.libs.ginkgo_conf import GINKGOCONF


# class ModelAdjustFactorTest(unittest.TestCase):
#     """
#     UnitTest for Order.
#     """

#     # Init
#     # set data from bar
#     # store in to ginkgodata
#     # query from ginkgodata

#     def __init__(self, *args, **kwargs) -> None:
#         super(ModelAdjustFactorTest, self).__init__(*args, **kwargs)
#         self.params = [
#             {
#                 "code": "testordercode",
#                 "timestamp": datetime.datetime.now(),
#                 "foreadjustfactor": 10,
#                 "backadjustfactor": 10,
#                 "adjustfactor": 10,
#             }
#         ]

#     def test_ModelAdjustFactor_Init(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         result = True
#         for i in self.params:
#             try:
#                 o = MAdjustfactor()
#                 o.set(
#                     code=i["code"],
#                     foreadjustfactor=i["foreadjustfactor"],
#                     backadjustfactor=i["backadjustfactor"],
#                     adjustfactor=i["adjustfactor"],
#                     date=i["timestamp"],
#                 )
#                 o.set_source(i["source"])
#             except Exception as e:
#                 result = False
#         self.assertEqual(result, True)

#     def test_ModelAdjustFactor_SetFromData(self) -> None:
#         time.sleep(GINKGOCONF.HEARTBEAT)
#         for i in self.params:
#             af = MAdjustfactor()
#             data = {
#                 "code": i["code"],
#                 "foreadjustfactor": i["foreadjustfactor"],
#                 "backadjustfactor": i["backadjustfactor"],
#                 "adjustfactor": i["adjustfactor"],
#                 "date": i["timestamp"],
#             }
#             af.set(pd.Series(data))
#             self.assertEqual(af.code, i["code"])
#             self.assertEqual(af.foreadjustfactor, i["foreadjustfactor"])
#             self.assertEqual(af.backadjustfactor, i["backadjustfactor"])
#             self.assertEqual(af.adjustfactor, i["adjustfactor"])

# def test_ModelAdjustFactor_Insert(self) -> None:
#     time.sleep(GINKGOCONF.HEARTBEAT)
#     result = True
#     GINKGODATA.drop_table(MSignal)
#     GINKGODATA.create_table(MSignal)
#     try:
#         o = MSignal()
#         GINKGODATA.add(o)
#         GINKGODATA.commit()
#     except Exception as e:
#         result = False

#     self.assertEqual(result, True)

# def test_ModelAdjustFactor_BatchInsert(self) -> None:
#     time.sleep(GINKGOCONF.HEARTBEAT)
#     result = True
#     GINKGODATA.drop_table(MSignal)
#     GINKGODATA.create_table(MSignal)
#     try:
#         s = []
#         for i in range(10):
#             o = MSignal()
#             s.append(o)

#         GINKGODATA.add_all(s)
#         GINKGODATA.commit()
#     except Exception as e:
#         result = False

#     self.assertEqual(result, True)

# def test_ModelAdjustFactor_Query(self) -> None:
#     time.sleep(GINKGOCONF.HEARTBEAT)
#     result = True
#     GINKGODATA.drop_table(MSignal)
#     GINKGODATA.create_table(MSignal)
#     try:
#         o = MSignal()
#         GINKGODATA.add(o)
#         GINKGODATA.commit()
#         r = GINKGODATA.session.query(MSignal).first()
#     except Exception as e:
#         result = False

#     self.assertNotEqual(r, None)
#     self.assertEqual(result, True)
