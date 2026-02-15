import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock
import threading
import time

from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.enums import ENGINESTATUS_TYPES


class BaseEngineTest(unittest.TestCase):
    """
    测试BaseEngine模块 - 仅测试BaseEngine
    """

    def setUp(self):
        """初始化测试用的BaseEngine实例"""
        self.engine = BaseEngine("test_engine")
        self.test_time = datetime(2024, 1, 1, 10, 0, 0)
        self.engine.on_time_goes_by(self.test_time)

    def test_BaseEngine_Init(self):
        """测试基础引擎初始化"""
        engine = BaseEngine("test_engine")
        self.assertIsNotNone(engine)

        # 检查基本属性
        self.assertTrue(hasattr(engine, "_name"))
        self.assertEqual(engine._name, "test_engine")
        self.assertEqual(engine._active, False)

    def test_default_initialization(self):
        """测试默认初始化"""
        engine = BaseEngine()
        self.assertEqual(engine._name, "BaseEngine")
        self.assertEqual(engine._active, False)

    def test_name_property(self):
        """测试name属性"""
        self.assertEqual(self.engine.name, "test_engine")

    def test_status_property(self):
        """测试status属性"""
        # 初始状态应该是Paused
        self.assertEqual(self.engine.status, "Paused")
        
        # 启动后状态应该是Active
        self.engine.start()
        self.assertEqual(self.engine.status, "Active")
        
        # 暂停后状态应该是Paused
        self.engine.pause()
        self.assertEqual(self.engine.status, "Paused")

    def test_is_active_property(self):
        """测试is_active属性"""
        # 初始状态应该是False
        self.assertFalse(self.engine.is_active)
        
        # 启动后应该是True
        self.engine.start()
        self.assertTrue(self.engine.is_active)
        
        # 暂停后应该是False
        self.engine.pause()
        self.assertFalse(self.engine.is_active)

    @patch('ginkgo.backtest.execution.engines.base_engine.BaseEngine.log')
    def test_start_method(self, mock_log):
        """测试start方法"""
        # 初始状态应该是非活跃的
        self.assertFalse(self.engine._active)
        
        # 调用start方法
        self.engine.start()
        
        # 验证状态已更改
        self.assertTrue(self.engine._active)
        self.assertEqual(self.engine.status, "Active")
        
        # 验证日志记录被调用
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        self.assertEqual(args[0], "INFO")
        self.assertIn("started", args[1])

    @patch('ginkgo.backtest.execution.engines.base_engine.BaseEngine.log')
    def test_pause_method(self, mock_log):
        """测试pause方法"""
        # 先启动引擎
        self.engine.start()
        self.assertTrue(self.engine._active)
        
        # 调用pause方法
        self.engine.pause()
        
        # 验证状态已更改
        self.assertFalse(self.engine._active)
        self.assertEqual(self.engine.status, "Paused")
        
        # 验证日志记录被调用
        mock_log.assert_called_with("INFO", unittest.mock.ANY)
        args, kwargs = mock_log.call_args
        self.assertIn("paused", args[1])

    @patch('ginkgo.backtest.execution.engines.base_engine.BaseEngine.log')
    def test_stop_method(self, mock_log):
        """测试stop方法"""
        # 先启动引擎
        self.engine.start()
        self.assertTrue(self.engine._active)
        
        # 调用stop方法
        self.engine.stop()
        
        # 验证状态已更改
        self.assertFalse(self.engine._active)
        self.assertEqual(self.engine.status, "Paused")
        
        # 验证日志记录被调用
        mock_log.assert_called_with("INFO", unittest.mock.ANY)
        args, kwargs = mock_log.call_args
        self.assertIn("stop", args[1])

    def test_inheritance_from_backtest_base(self):
        """测试是否正确继承BacktestBase"""
        from ginkgo.trading.core.backtest_base import BacktestBase
        
        # 验证继承关系
        self.assertIsInstance(self.engine, BacktestBase)
        
        # 验证继承的属性和方法
        self.assertTrue(hasattr(self.engine, "on_time_goes_by"))
        self.assertTrue(hasattr(self.engine, "now"))
        self.assertTrue(hasattr(self.engine, "_name"))
        self.assertTrue(hasattr(self.engine, "log"))

    def test_time_management(self):
        """测试时间管理功能（继承自BacktestBase）"""
        # 测试时间设置
        test_time = datetime(2024, 2, 1, 15, 30, 0)
        self.engine.on_time_goes_by(test_time)
        self.assertEqual(self.engine.now, test_time)

    def test_engine_lifecycle(self):
        """测试引擎生命周期"""
        # 初始状态
        self.assertFalse(self.engine.is_active)
        self.assertEqual(self.engine.status, "Paused")
        
        # 启动 -> 活跃
        self.engine.start()
        self.assertTrue(self.engine.is_active)
        self.assertEqual(self.engine.status, "Active")
        
        # 暂停 -> 非活跃
        self.engine.pause()
        self.assertFalse(self.engine.is_active)
        self.assertEqual(self.engine.status, "Paused")
        
        # 重新启动 -> 活跃
        self.engine.start()
        self.assertTrue(self.engine.is_active)
        self.assertEqual(self.engine.status, "Active")
        
        # 停止 -> 非活跃
        self.engine.stop()
        self.assertFalse(self.engine.is_active)
        self.assertEqual(self.engine.status, "Paused")

    def test_multiple_start_calls(self):
        """测试多次调用start方法"""
        # 多次调用start应该保持活跃状态
        self.engine.start()
        self.assertTrue(self.engine.is_active)
        
        self.engine.start()
        self.assertTrue(self.engine.is_active)
        
        self.engine.start()
        self.assertTrue(self.engine.is_active)

    def test_multiple_pause_calls(self):
        """测试多次调用pause方法"""
        # 先启动
        self.engine.start()
        self.assertTrue(self.engine.is_active)
        
        # 多次调用pause应该保持非活跃状态
        self.engine.pause()
        self.assertFalse(self.engine.is_active)
        
        self.engine.pause()
        self.assertFalse(self.engine.is_active)
        
        self.engine.pause()
        self.assertFalse(self.engine.is_active)

    def test_repr_method(self):
        """测试__repr__方法"""
        repr_str = repr(self.engine)
        self.assertIsInstance(repr_str, str)
        self.assertIn("test_engine", repr_str)

    def test_engine_id_access(self):
        """测试engine_id访问（继承自BacktestBase）"""
        # engine_id应该可以访问
        self.assertTrue(hasattr(self.engine, "engine_id"))
        
        # 可以设置engine_id
        test_id = "test_engine_123"
        self.engine.engine_id = test_id
        self.assertEqual(self.engine.engine_id, test_id)

    def test_active_attribute_direct_access(self):
        """测试_active属性的直接访问"""
        # 初始状态
        self.assertEqual(self.engine._active, False)
        
        # 通过start方法修改
        self.engine.start()
        self.assertEqual(self.engine._active, True)
        
        # 通过pause方法修改
        self.engine.pause()
        self.assertEqual(self.engine._active, False)
        
        # 直接修改_active属性
        self.engine._active = True
        self.assertTrue(self.engine.is_active)
        self.assertEqual(self.engine.status, "Active")
    
    # =========================
    # 新增：增强的生命周期和状态管理测试
    # =========================
    
    def test_state_consistency_during_rapid_operations(self):
        """测试快速操作期间的状态一致性"""
        # 快速切换状态，确保状态保持一致
        operations = ["start", "pause", "start", "stop", "start", "pause"]
        
        for operation in operations:
            getattr(self.engine, operation)()
            
            # 验证状态一致性
            if operation == "start":
                self.assertTrue(self.engine.is_active)
                self.assertEqual(self.engine.status, "Active")
            else:  # pause or stop
                self.assertFalse(self.engine.is_active)
                self.assertEqual(self.engine.status, "Paused")
    
    def test_state_transitions_with_logging(self):
        """测试状态转换时的日志记录"""
        with patch.object(self.engine, 'log') as mock_log:
            # 测试从Paused到Active的转换
            self.assertEqual(self.engine.status, "Paused")
            self.engine.start()
            self.assertEqual(self.engine.status, "Active")
            
            # 验证start日志
            mock_log.assert_called_with("INFO", unittest.mock.ANY)
            start_call_args = mock_log.call_args[0]
            self.assertIn("started", start_call_args[1])
            
            mock_log.reset_mock()
            
            # 测试从Active到Paused的转换
            self.engine.pause()
            self.assertEqual(self.engine.status, "Paused")
            
            # 验证pause日志
            mock_log.assert_called_with("INFO", unittest.mock.ANY)
            pause_call_args = mock_log.call_args[0]
            self.assertIn("paused", pause_call_args[1])
            
            mock_log.reset_mock()
            
            # 重新启动并停止
            self.engine.start()
            self.engine.stop()
            
            # 验证stop日志
            stop_call_args = mock_log.call_args[0]
            self.assertIn("stop", stop_call_args[1])
    
    def test_engine_id_in_log_messages(self):
        """测试日志消息中包含engine_id"""
        test_engine_id = "test_engine_abc123"
        self.engine.engine_id = test_engine_id
        
        with patch.object(self.engine, 'log') as mock_log:
            self.engine.start()
            
            # 验证日志消息包含engine_id
            mock_log.assert_called_once()
            log_message = mock_log.call_args[0][1]
            self.assertIn(test_engine_id, log_message)
    
    def test_concurrent_state_operations(self):
        """测试并发状态操作的线程安全性"""
        results = []
        
        def worker(operation_name):
            """工作线程函数"""
            try:
                if operation_name == "start":
                    self.engine.start()
                elif operation_name == "pause":
                    self.engine.pause()
                elif operation_name == "stop":
                    self.engine.stop()
                
                # 记录操作后的状态
                results.append((operation_name, self.engine.is_active, self.engine.status))
            except Exception as e:
                results.append((operation_name, "ERROR", str(e)))
        
        # 创建多个线程同时操作引擎
        threads = []
        operations = ["start", "pause", "start", "stop", "start"]
        
        for op in operations:
            thread = threading.Thread(target=worker, args=(op,))
            threads.append(thread)
        
        # 启动所有线程
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=1.0)
        
        # 验证最后的状态是一致的
        final_is_active = self.engine.is_active
        final_status = self.engine.status
        
        # 状态应该是一致的（要么Active要么Paused）
        if final_is_active:
            self.assertEqual(final_status, "Active")
        else:
            self.assertEqual(final_status, "Paused")
        
        # 应该没有出现错误
        error_results = [r for r in results if r[1] == "ERROR"]
        self.assertEqual(len(error_results), 0, f"Concurrent operations caused errors: {error_results}")
    
    def test_engine_status_enum_compatibility(self):
        """测试引擎状态与ENGINESTATUS_TYPES枚举的兼容性"""
        # 验证状态字符串与枚举值的对应关系
        # 注意：BaseEngine使用字符串状态，但应该与数据库中的枚举兼容
        
        # 初始状态对应IDLE
        self.assertEqual(self.engine.status, "Paused")
        
        # 活跃状态对应RUNNING
        self.engine.start()
        self.assertEqual(self.engine.status, "Active")
        
        # 暂停状态对应STOPPED
        self.engine.pause()
        self.assertEqual(self.engine.status, "Paused")
        
        # 确保枚举值存在
        self.assertTrue(hasattr(ENGINESTATUS_TYPES, 'IDLE'))
        self.assertTrue(hasattr(ENGINESTATUS_TYPES, 'RUNNING'))
        self.assertTrue(hasattr(ENGINESTATUS_TYPES, 'STOPPED'))
    
    def test_engine_lifecycle_with_time_progression(self):
        """测试引擎生命周期与时间进展的结合"""
        base_time = datetime(2024, 1, 1, 9, 0, 0)
        
        # 设置初始时间
        self.engine.on_time_goes_by(base_time)
        self.assertEqual(self.engine.now, base_time)
        self.assertEqual(self.engine.status, "Paused")
        
        # 启动引擎并推进时间
        self.engine.start()
        self.assertTrue(self.engine.is_active)
        
        # 时间推进应该不影响引擎状态
        for i in range(5):
            new_time = base_time + timedelta(hours=i+1)
            self.engine.on_time_goes_by(new_time)
            self.assertEqual(self.engine.now, new_time)
            self.assertTrue(self.engine.is_active)  # 引擎应该保持活跃
        
        # 暂停引擎，时间推进仍应正常工作
        self.engine.pause()
        final_time = base_time + timedelta(hours=10)
        self.engine.on_time_goes_by(final_time)
        self.assertEqual(self.engine.now, final_time)
        self.assertFalse(self.engine.is_active)
    
    def test_engine_error_handling_during_state_changes(self):
        """测试状态改变期间的错误处理"""
        # Mock log方法以抛出异常
        def mock_log_with_error(level, message):
            if "started" in message:
                raise Exception("Log system error")
        
        with patch.object(self.engine, 'log', side_effect=mock_log_with_error):
            # 即使日志系统出错，状态改变也应该完成
            with self.assertRaises(Exception):
                self.engine.start()
            
            # 验证状态已正确改变（尽管日志失败）
            self.assertTrue(self.engine._active)
            self.assertTrue(self.engine.is_active)
            self.assertEqual(self.engine.status, "Active")
    
    def test_engine_repr_with_different_states(self):
        """测试不同状态下的字符串表示"""
        # 测试暂停状态的repr
        paused_repr = repr(self.engine)
        self.assertIsInstance(paused_repr, str)
        self.assertIn("test_engine", paused_repr)
        
        # 测试活跃状态的repr
        self.engine.start()
        active_repr = repr(self.engine)
        self.assertIsInstance(active_repr, str)
        self.assertIn("test_engine", active_repr)
        
        # repr格式应该一致
        self.assertEqual(type(paused_repr), type(active_repr))
    
    def test_engine_memory_cleanup(self):
        """测试引擎的内存清理"""
        # 创建多个引擎实例
        engines = []
        for i in range(10):
            engine = BaseEngine(f"test_engine_{i}")
            engine.start()
            engines.append(engine)
        
        # 验证所有引擎都正常工作
        for engine in engines:
            self.assertTrue(engine.is_active)
            self.assertEqual(engine.status, "Active")
        
        # 停止所有引擎
        for engine in engines:
            engine.stop()
            self.assertFalse(engine.is_active)
        
        # 清理引用
        engines.clear()
        
        # 原始引擎应该仍然正常工作
        self.assertFalse(self.engine.is_active)
        self.engine.start()
        self.assertTrue(self.engine.is_active)
    
    def test_engine_state_persistence_across_time_changes(self):
        """测试引擎状态在时间变化中的持久性"""
        times = [
            datetime(2024, 1, 1, 9, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 1, 15, 0, 0),
            datetime(2024, 1, 1, 18, 0, 0),
        ]
        
        # 启动引擎
        self.engine.start()
        initial_active_state = self.engine.is_active
        
        # 在不同时间点验证状态持久性
        for test_time in times:
            self.engine.on_time_goes_by(test_time)
            self.assertEqual(self.engine.now, test_time)
            self.assertEqual(self.engine.is_active, initial_active_state)
        
        # 暂停引擎并重复测试
        self.engine.pause()
        paused_state = self.engine.is_active
        
        for test_time in reversed(times):
            self.engine.on_time_goes_by(test_time)
            self.assertEqual(self.engine.now, test_time)
            self.assertEqual(self.engine.is_active, paused_state)
    
    def test_engine_inheritance_and_polymorphism(self):
        """测试引擎继承和多态性"""
        # 测试多态行为
        engines = [
            BaseEngine("base_engine_1"),
            BaseEngine("base_engine_2"),
        ]
        
        # 所有引擎都应该有相同的接口
        for engine in engines:
            self.assertTrue(hasattr(engine, 'start'))
            self.assertTrue(hasattr(engine, 'pause'))
            self.assertTrue(hasattr(engine, 'stop'))
            self.assertTrue(hasattr(engine, 'is_active'))
            self.assertTrue(hasattr(engine, 'status'))
            
            # 行为应该一致
            engine.start()
            self.assertTrue(engine.is_active)
            self.assertEqual(engine.status, "Active")
            
            engine.pause()
            self.assertFalse(engine.is_active)
            self.assertEqual(engine.status, "Paused")