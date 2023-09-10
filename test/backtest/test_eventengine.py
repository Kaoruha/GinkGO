# import unittest
# import datetime
# from time import sleep
# from ginkgo.backtest.engines import EventEngine
# from ginkgo.enums import EVENT_TYPES
# from ginkgo.backtest.events import EventCapitalUpdate


# class EventEngineTest(unittest.TestCase):
#     """
#     UnitTest for EventEngine.
#     """

#     # Init
#     def __init__(self, *args, **kwargs) -> None:
#         super(EventEngineTest, self).__init__(*args, **kwargs)

#         self.params = [
#             {},
#         ]

#     def test_EngineInit(self) -> None:
#         for i in self.params:
#             engine = EventEngine()

#     def test_EngineStart(self) -> None:
#         engine = EventEngine()
#         self.assertEqual(engine.is_active, False)
#         engine.start()
#         self.assertEqual(engine.is_active, True)
#         engine.stop()

#     def test_EnginStop(self) -> None:
#         engine = EventEngine()
#         self.assertEqual(engine.is_active, False)
#         engine.start()
#         self.assertEqual(engine.is_active, True)
#         sleep(0.2)
#         engine.stop()
#         self.assertEqual(engine.is_active, False)

#     def test_EngineRegiste(self) -> None:
#         engine = EventEngine()

#         def halo() -> None:
#             print("test")

#         self.assertEqual(engine.handle_count, 0)
#         engine.register(EVENT_TYPES.OTHER, halo)
#         self.assertEqual(engine.handle_count, 1)

#     def test_EngineUnregiste(self) -> None:
#         engine = EventEngine()

#         def halo() -> None:
#             print("test")

#         self.assertEqual(engine.handle_count, 0)
#         engine.register(EVENT_TYPES.OTHER, halo)
#         self.assertEqual(engine.handle_count, 1)
#         engine.unregister(EVENT_TYPES.CAPITALUPDATE, halo)
#         self.assertEqual(engine.handle_count, 1)
#         engine.unregister(EVENT_TYPES.OTHER, halo)
#         self.assertEqual(engine.handle_count, 0)

#     def test_EngineRegisteGeneral(self) -> None:
#         engine = EventEngine()

#         def halo() -> None:
#             print("test")

#         self.assertEqual(engine.general_count, 0)
#         engine.register_general(halo)
#         self.assertEqual(engine.general_count, 1)

#     def test_EngineUnregisteGeneral(self) -> None:
#         engine = EventEngine()

#         def halo() -> None:
#             print("test")

#         self.assertEqual(engine.general_count, 0)
#         engine.register_general(halo)
#         self.assertEqual(engine.general_count, 1)
#         engine.unregister_general(halo)
#         self.assertEqual(engine.general_count, 0)

#     def test_EngineRegisteTimer(self) -> None:
#         engine = EventEngine()

#         def halo() -> None:
#             print("test")

#         self.assertEqual(engine.timer_count, 0)
#         engine.register_timer(halo)
#         self.assertEqual(engine.timer_count, 1)

#     def test_EngineUnregisteTimer(self) -> None:
#         engine = EventEngine()

#         def halo() -> None:
#             print("test")

#         self.assertEqual(engine.timer_count, 0)
#         engine.register_timer(halo)
#         self.assertEqual(engine.timer_count, 1)
#         engine.unregister_timer(halo)
#         self.assertEqual(engine.timer_count, 0)

#     def test_EnginePut(self) -> None:
#         engine = EventEngine()
#         e = EventCapitalUpdate()
#         engine.put(e)
#         self.assertEqual(engine.todo_count, 1)
#         engine.put(e)
#         self.assertEqual(engine.todo_count, 2)

#     def test_EngineProcess(self) -> None:
#         engine = EventEngine()
#         global a
#         a = 0

#         def test_handle(event) -> None:
#             global a
#             a += 1

#         engine.register(EVENT_TYPES.CAPITALUPDATE, test_handle)
#         e = EventCapitalUpdate()
#         engine._process(e)
#         self.assertEqual(a, 1)
#         engine._process(e)
#         self.assertEqual(a, 2)
#         engine._process(e)
#         self.assertEqual(a, 3)

#     def test_EngineGeneralProcess(self) -> None:
#         engine = EventEngine()
#         global a
#         a = 0

#         def test_handle(event) -> None:
#             global a
#             a += 1

#         def test_general(event) -> None:
#             global a
#             a += 2

#         engine.register(EVENT_TYPES.CAPITALUPDATE, test_handle)
#         engine.register_general(test_general)
#         e = EventCapitalUpdate()
#         engine._process(e)
#         self.assertEqual(a, 3)
#         engine._process(e)
#         self.assertEqual(a, 6)
#         engine._process(e)
#         self.assertEqual(a, 9)

#     def test_EngineTimerProcess(self) -> None:
#         engine = EventEngine(0.01)
#         global a
#         a = 0

#         def test_handle() -> None:
#             global a
#             a += 1

#         engine.register_timer(test_handle)
#         engine.start()
#         sleep(0.055)
#         engine.stop()
#         self.assertEqual(a, 6)
