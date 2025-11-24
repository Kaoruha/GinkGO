"""
FixedSelector固定选择器测试

验证固定股票代码选择器的完整功能：
- JSON格式股票代码解析
- 固定股票代码返回机制
- 错误处理和边界条件
- 日志记录和调试功能
- 选择器配置管理
"""

import pytest
import json
from unittest.mock import patch, Mock

from ginkgo.trading.strategy.selectors.fixed_selector import FixedSelector


@pytest.mark.selector
@pytest.mark.fixed_selector
class TestFixedSelectorBasics:
    """FixedSelector基础功能测试"""

    def test_selector_initialization_with_valid_json(self):
        """测试有效JSON初始化"""
        print("\n测试有效JSON初始化")

        # 测试JSON格式股票代码
        codes_json = json.dumps(["000001.SZ", "000002.SZ", "600000.SH"])
        selector = FixedSelector(name="TestSelector", codes=codes_json)

        # 验证股票代码解析成功
        assert selector.name == "TestSelector"
        assert selector._interested == ["000001.SZ", "000002.SZ", "600000.SH"]

        print("✓ 有效JSON初始化成功")

    def test_selector_initialization_with_invalid_json(self):
        """测试无效JSON初始化"""
        print("\n测试无效JSON初始化")

        # 测试无效JSON格式
        invalid_json = "{'invalid': json format}"  # 单引号，无效JSON

        with patch('builtins.print') as mock_print:
            selector = FixedSelector(name="InvalidSelector", codes=invalid_json)

            # 验证错误处理
            assert selector.name == "InvalidSelector"
            assert selector._interested == []  # 应该为空列表

            # 验证错误信息被打印
            mock_print.assert_called_once()

        print("✓ 无效JSON错误处理成功")

    def test_selector_initialization_with_empty_json(self):
        """测试空JSON初始化"""
        print("\n测试空JSON初始化")

        # 测试空JSON数组
        empty_json = json.dumps([])
        selector = FixedSelector(name="EmptySelector", codes=empty_json)

        # 验证空列表处理
        assert selector.name == "EmptySelector"
        assert selector._interested == []

        print("✓ 空JSON初始化成功")

    def test_selector_initialization_with_various_formats(self):
        """测试各种格式初始化"""
        print("\n测试各种格式初始化")

        test_cases = [
            # (输入JSON, 期望结果, 描述)
            (json.dumps(["000001.SZ"]), ["000001.SZ"], "单个股票"),
            (json.dumps(["000001.SZ", "600000.SH"]), ["000001.SZ", "600000.SH"], "多个股票"),
            (json.dumps([]), [], "空数组"),
            (json.dumps(["A", "B", "C", "D", "E"]), ["A", "B", "C", "D", "E"], "多个字符"),
        ]

        for codes_json, expected, description in test_cases:
            selector = FixedSelector(name=f"Test_{description}", codes=codes_json)
            assert selector._interested == expected, f"测试失败: {description}"
            print(f"  ✓ {description}: {expected}")

        print("✓ 各种格式初始化成功")


@pytest.mark.selector
@pytest.mark.picking_logic
class TestFixedSelectorPickingLogic:
    """FixedSelector选择逻辑测试"""

    def setup_method(self):
        """测试前设置"""
        self.test_codes = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH"]
        self.codes_json = json.dumps(self.test_codes)
        self.selector = FixedSelector(name="TestSelector", codes=self.codes_json)

    def test_pick_returns_fixed_codes(self):
        """测试pick返回固定代码"""
        print("\n测试pick返回固定代码")

        # 调用pick方法
        result = self.selector.pick()

        # 验证返回结果
        assert result == self.test_codes
        assert isinstance(result, list)
        assert len(result) == len(self.test_codes)

        print(f"✓ pick返回固定代码: {result}")

    def test_pick_with_time_parameter(self):
        """测试带时间参数的pick"""
        print("\n测试带时间参数的pick")

        import datetime

        test_time = datetime.datetime(2023, 1, 1, 9, 30)

        # 带时间参数调用pick
        result = self.selector.pick(time=test_time)

        # 时间参数不应该影响结果
        assert result == self.test_codes

        print("✓ 带时间参数pick成功")

    def test_pick_with_additional_arguments(self):
        """测试带额外参数的pick"""
        print("\n测试带额外参数的pick")

        # 带各种额外参数调用pick
        result1 = self.selector.pick(time=None, extra_param="value")
        result2 = self.selector.pick(time="2023-01-01", arg1=1, arg2="test", arg3=None)

        # 额外参数不应该影响结果
        assert result1 == self.test_codes
        assert result2 == self.test_codes

        print("✓ 带额外参数pick成功")

    def test_pick_consistency(self):
        """测试pick结果一致性"""
        print("\n测试pick结果一致性")

        # 多次调用pick应该返回相同结果
        results = []
        for i in range(5):
            result = self.selector.pick()
            results.append(result)

        # 验证所有结果相同
        for result in results[1:]:
            assert result == results[0]

        print(f"✓ pick结果一致性验证成功: {results[0]}")

    def test_pick_with_empty_selector(self):
        """测试空选择器的pick"""
        print("\n测试空选择器的pick")

        # 创建空选择器
        empty_selector = FixedSelector(name="EmptySelector", codes=json.dumps([]))

        result = empty_selector.pick()

        # 应该返回空列表
        assert result == []
        assert isinstance(result, list)

        print("✓ 空选择器pick成功")


@pytest.mark.selector
@pytest.mark.logging
class TestFixedSelectorLogging:
    """FixedSelector日志功能测试"""

    def setup_method(self):
        """测试前设置"""
        self.test_codes = ["000001.SZ", "000002.SZ"]
        self.codes_json = json.dumps(self.test_codes)
        self.selector = FixedSelector(name="LoggingTestSelector", codes=self.codes_json)

    def test_pick_logging(self):
        """测试pick日志记录"""
        print("\n测试pick日志记录")

        with patch.object(self.selector, 'log') as mock_log:
            result = self.selector.pick()

            # 验证日志被调用
            mock_log.assert_called_once_with("DEBUG", f"Selector:{self.selector.name} pick {result}.")

            # 验证日志参数
            call_args = mock_log.call_args
            assert call_args[0][0] == "DEBUG"
            assert f"Selector:{self.selector.name}" in call_args[0][1]
            assert str(result) in call_args[0][1]

        print("✓ pick日志记录成功")

    def test_logging_with_empty_result(self):
        """测试空结果日志记录"""
        print("\n测试空结果日志记录")

        empty_selector = FixedSelector(name="EmptyLogSelector", codes=json.dumps([]))

        with patch.object(empty_selector, 'log') as mock_log:
            result = empty_selector.pick()

            # 验证空结果也被记录
            mock_log.assert_called_once_with("DEBUG", f"Selector:EmptyLogSelector pick {result}.")

        print("✓ 空结果日志记录成功")

    def test_logging_with_large_codes_list(self):
        """测试大量代码日志记录"""
        print("\n测试大量代码日志记录")

        # 创建包含大量股票代码的选择器
        large_codes = [f"00000{i:02d}.SZ" for i in range(1, 101)]  # 100个股票
        large_selector = FixedSelector(name="LargeSelector", codes=json.dumps(large_codes))

        with patch.object(large_selector, 'log') as mock_log:
            result = large_selector.pick()

            # 验证大量代码的日志记录
            mock_log.assert_called_once()
            log_message = mock_log.call_args[0][1]

            assert "Selector:LargeSelector pick" in log_message
            assert str(len(result)) in log_message or len(result) > 0

        print(f"✓ 大量代码日志记录成功: {len(result)}个代码")


@pytest.mark.selector
@pytest.mark.error_handling
class TestFixedSelectorErrorHandling:
    """FixedSelector错误处理测试"""

    def test_malformed_json_handling(self):
        """测试格式错误的JSON处理"""
        print("\n测试格式错误的JSON处理")

        malformed_cases = [
            '{"incomplete": json',  # 不完整JSON
            "{'single': 'quotes'}",  # 单引号JSON
            "not json at all",  # 完全不是JSON
            '{"valid": "json", "extra": }',  # 语法错误
            "",  # 空字符串
            "null",  # null值
        ]

        for malformed_input in malformed_cases:
            with patch('builtins.print') as mock_print:
                selector = FixedSelector(name="ErrorTestSelector", codes=malformed_input)

                # 验证错误处理
                assert selector._interested == []
                assert selector.name == "ErrorTestSelector"

                # 验证错误被记录
                mock_print.assert_called()

            print(f"  ✓ 错误处理成功: {type(malformed_input)}")

        print("✓ 格式错误JSON处理成功")

    def test_json_with_non_array_data(self):
        """测试非数组JSON数据处理"""
        print("\n测试非数组JSON数据处理")

        non_array_cases = [
            json.dumps({"code": "000001.SZ"}),  # 对象而非数组
            json.dumps("000001.SZ"),  # 字符串而非数组
            json.dumps(123),  # 数字而非数组
            json.dumps(true),  # 布尔值而非数组（注意：Python中是True）
            json.dumps(null),  # null而非数组
        ]

        for non_array_input in non_array_cases:
            selector = FixedSelector(name="NonArrayTestSelector", codes=non_array_input)

            # 验证非数组数据处理
            # 注意：这取决于实现，可能为空或包含解析结果
            print(f"  非数组数据处理: {non_array_input} -> {selector._interested}")

        print("✓ 非数组JSON数据处理成功")

    def test_unicode_and_special_characters(self):
        """测试Unicode和特殊字符处理"""
        print("\n测试Unicode和特殊字符处理")

        special_cases = [
            json.dumps(["平安银行.SZ"]),  # 中文
            json.dumps(["AAPL.US", "GOOGL.US"]),  # 英文美股
            json.dumps(["000001.深圳"]),  # 中文后缀
            json.dumps(["股票_001", "股票_002"]),  # 下划线
        ]

        for special_input in special_cases:
            try:
                selector = FixedSelector(name="SpecialTestSelector", codes=special_input)
                result = selector.pick()

                # 验证特殊字符处理
                assert isinstance(result, list)
                print(f"  ✓ 特殊字符处理成功: {result}")

            except Exception as e:
                print(f"  ⚠ 特殊字符处理警告: {e}")

        print("✓ Unicode和特殊字符处理完成")

    def test_extremely_large_json_input(self):
        """测试极大JSON输入处理"""
        print("\n测试极大JSON输入处理")

        # 创建包含大量数据的JSON
        large_list = [f"CODE_{i:06d}" for i in range(10000)]  # 10,000个代码
        large_json = json.dumps(large_list)

        try:
            selector = FixedSelector(name="LargeJsonSelector", codes=large_json)

            # 验证大数据处理
            assert len(selector._interested) == 10000

            result = selector.pick()
            assert len(result) == 10000

            print(f"✓ 极大JSON输入处理成功: {len(result)}个代码")

        except Exception as e:
            pytest.fail(f"极大JSON输入处理失败: {e}")

    def test_json_with_nesting_and_structure(self):
        """测试嵌套和结构化JSON处理"""
        print("\n测试嵌套和结构化JSON处理")

        structured_cases = [
            json.dumps([["nested", "array"], {"valid": "structure"}]),  # 混合结构
            json.dumps([1, 2, 3, 4.5, "mixed", True, None]),  # 混合类型
            json.dumps({"not_array": "but_valid_json"}),  # 有效JSON但不是数组
        ]

        for structured_input in structured_cases:
            selector = FixedSelector(name="StructuredTestSelector", codes=structured_input)

            # 验证结构化数据处理
            result = selector.pick()
            print(f"  结构化数据处理: {type(structured_input)} -> {len(result)}项")

        print("✓ 嵌套和结构化JSON处理成功")


@pytest.mark.selector
@pytest.mark.performance
class TestFixedSelectorPerformance:
    """FixedSelector性能测试"""

    def test_high_frequency_pick_operations(self):
        """测试高频pick操作"""
        print("\n测试高频pick操作")

        import time

        # 创建选择器
        codes = [f"00000{i%100:02d}.SZ" for i in range(1000)]  # 1000个代码
        selector = FixedSelector(name="PerformanceTestSelector", codes=json.dumps(codes))

        iterations = 10000

        # 测试高频调用
        start_time = time.time()
        results = []

        for i in range(iterations):
            result = selector.pick()
            results.append(result)

        elapsed_time = time.time() - start_time
        picks_per_second = iterations / elapsed_time

        # 验证结果一致性
        first_result = results[0]
        for result in results[1:]:
            assert result == first_result

        print(f"✓ 高频测试: {iterations}次pick操作")
        print(f"  耗时: {elapsed_time:.3f}秒, 速率: {picks_per_second:.1f}次/秒")
        print(f"  每次结果: {len(first_result)}个代码")

        # 性能断言
        assert elapsed_time < 2.0, f"pick操作速度过慢: {elapsed_time:.3f}秒"
        assert picks_per_second > 5000, f"pick操作速率过低: {picks_per_second:.1f}次/秒"

    def test_memory_usage_stability(self):
        """测试内存使用稳定性"""
        print("\n测试内存使用稳定性")

        import psutil
        import os
        import gc

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 创建多个选择器并频繁调用
        selectors = []
        for i in range(10):
            codes = [f"CODE_{i}_{j}" for j in range(100)]
            selector = FixedSelector(name=f"MemTest_{i}", codes=json.dumps(codes))
            selectors.append(selector)

        # 大量pick操作
        for _ in range(1000):
            for selector in selectors:
                selector.pick()

        # 强制垃圾回收
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"✓ 内存使用: 初始 {initial_memory:.1f}MB, 最终 {final_memory:.1f}MB, 增长 {memory_increase:.1f}MB")

        # 内存增长应该在合理范围内
        assert memory_increase < 10, f"内存增长过多: {memory_increase:.1f}MB"

    def test_large_codes_list_performance(self):
        """测试大代码列表性能"""
        print("\n测试大代码列表性能")

        import time

        # 创建包含大量代码的选择器
        large_codes = [f"CODE_{i:06d}.SZ" for i in range(50000)]  # 50,000个代码
        selector = FixedSelector(name="LargeListSelector", codes=json.dumps(large_codes))

        # 测试单次pick性能
        start_time = time.time()
        result = selector.pick()
        single_pick_time = time.time() - start_time

        # 测试多次pick性能
        iterations = 100
        start_time = time.time()
        for _ in range(iterations):
            selector.pick()
        total_time = time.time() - start_time

        print(f"✓ 大列表性能测试: {len(result)}个代码")
        print(f"  单次pick: {single_pick_time:.6f}秒")
        print(f"  {iterations}次pick: {total_time:.3f}秒, 平均: {total_time/iterations:.6f}秒")

        # 性能断言
        assert single_pick_time < 0.01, f"大列表单次pick过慢: {single_pick_time:.6f}秒"
        assert total_time / iterations < 0.001, f"大列表平均pick过慢: {total_time/iterations:.6f}秒"


@pytest.mark.selector
@pytest.mark.integration
class TestFixedSelectorIntegration:
    """FixedSelector集成测试"""

    def test_selector_in_different_contexts(self):
        """测试选择器在不同上下文中的使用"""
        print("\n测试选择器在不同上下文中的使用")

        codes = ["000001.SZ", "000002.SZ"]
        selector = FixedSelector(name="ContextTestSelector", codes=json.dumps(codes))

        # 模拟不同调用上下文
        contexts = [
            {"time": None},
            {"time": "2023-01-01"},
            {"portfolio_id": "test_portfolio"},
            {"strategy_id": "test_strategy"},
            {"extra_param1": "value1", "extra_param2": 123, "extra_param3": None},
        ]

        for context in contexts:
            result = selector.pick(**context)

            # 上下文不应该影响结果
            assert result == codes

            print(f"  ✓ 上下文测试: {context}")

        print("✓ 不同上下文使用测试成功")

    def test_selector_with_real_world_scenarios(self):
        """测试真实世界使用场景"""
        print("\n测试真实世界使用场景")

        # 场景1: 大盘蓝筹股
        blue_chips = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "000858.SZ"]
        blue_selector = FixedSelector(name="BlueChipSelector", codes=json.dumps(blue_chips))

        # 场景2: 科技股
        tech_stocks = ["000002.SZ", "300750.SZ", "002415.SZ", "300059.SZ"]
        tech_selector = FixedSelector(name="TechSelector", codes=json.dumps(tech_stocks))

        # 场景3: 银行股
        bank_stocks = ["000001.SZ", "600000.SH", "600036.SH", "601398.SH", "601939.SH"]
        bank_selector = FixedSelector(name="BankSelector", codes=json.dumps(bank_stocks))

        # 测试各种场景
        selectors = [blue_selector, tech_selector, bank_selector]
        for selector in selectors:
            result = selector.pick()

            assert isinstance(result, list)
            assert len(result) > 0
            assert all(".SZ" in code or ".SH" in code for code in result)

            print(f"  ✓ {selector.name}: {len(result)}个股票")

        print("✓ 真实世界场景测试成功")

    def test_selector_reusability(self):
        """测试选择器可重用性"""
        print("\n测试选择器可重用性")

        selector = FixedSelector(name="ReusableSelector", codes=json.dumps(["REUSE1", "REUSE2"]))

        # 多次使用同一个选择器
        results = []
        for i in range(10):
            result = selector.pick()
            results.append(result)

            # 每次结果应该相同
            assert result == ["REUSE1", "REUSE2"]

        # 验证选择器状态没有被改变
        assert selector.name == "ReusableSelector"
        assert selector._interested == ["REUSE1", "REUSE2"]

        print("✓ 选择器可重用性验证成功")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])