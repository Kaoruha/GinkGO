"""
BaseAnalyzer分析器TDD测试

通过TDD方式开发BaseAnalyzer的核心逻辑测试套件
聚焦于模板方法模式、钩子机制和扩展性验证
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class ConcreteAnalyzer(BaseAnalyzer):
    """用于测试的具体Analyzer子类，实现抽象方法"""

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        self._activated = True
        self._last_stage = stage
        self._last_portfolio_info = portfolio_info

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        self._recorded = True
        self._last_record_stage = stage
        self._last_record_info = portfolio_info


@pytest.mark.unit
class TestBaseAnalyzerConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试构造函数"""
        analyzer = ConcreteAnalyzer(name="TestAnalyzer")

        # 验证name参数被正确设置
        assert analyzer.name == "TestAnalyzer"

        # 验证_active_stage初始化为空列表
        assert analyzer._active_stage == []

        # 验证_record_stage默认为RECORDSTAGE_TYPES.NEWDAY
        assert analyzer._record_stage == RECORDSTAGE_TYPES.NEWDAY

        # 验证性能监控属性初始化
        assert analyzer._activation_count == 0
        assert analyzer._record_count == 0
        assert analyzer._total_activation_time == 0.0

    def test_dual_inheritance(self):
        """测试双继承"""
        from ginkgo.trading.core.backtest_base import BacktestBase
        from ginkgo.entities.mixins import TimeMixin

        analyzer = ConcreteAnalyzer(name="DualTest")

        # 验证继承BacktestBase
        assert isinstance(analyzer, BacktestBase)

        # 验证继承TimeMixin
        assert isinstance(analyzer, TimeMixin)

        # 验证有uuid等Base属性
        assert analyzer.uuid is not None

        # 验证有timestamp相关属性（TimeMixin提供）
        assert callable(getattr(analyzer, 'get_current_time', None))

    def test_performance_monitoring_initialization(self):
        """测试性能监控初始化"""
        analyzer = ConcreteAnalyzer(name="PerfTest")

        # 验证性能监控属性初始化
        assert analyzer._activation_count == 0
        assert analyzer._record_count == 0
        assert analyzer._total_activation_time == 0.0
        assert analyzer._total_record_time == 0.0
        assert analyzer._error_count == 0
        assert analyzer._last_error is None
        assert analyzer._error_log == []


@pytest.mark.unit
class TestActivateTemplateMethod:
    """2. activate()模板方法测试"""

    def test_activate_calls_do_activate(self):
        """测试activate调用_do_activate"""
        analyzer = ConcreteAnalyzer(name="ActivateTest")
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)

        portfolio_info = {"cash": 100000, "positions": []}

        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 验证_do_activate()被调用
        assert analyzer._activated is True
        assert analyzer._last_stage == RECORDSTAGE_TYPES.NEWDAY
        assert analyzer._last_portfolio_info == portfolio_info

    def test_activate_stage_filtering(self):
        """测试activate的阶段过滤"""
        analyzer = ConcreteAnalyzer(name="StageFilterTest")
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)

        portfolio_info = {"cash": 100000}

        # 只在NEWDAY阶段激活
        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        assert analyzer._activated is True

        # 其他阶段不应调用_do_activate
        analyzer._activated = False
        analyzer.activate(RECORDSTAGE_TYPES.ORDERSEND, portfolio_info)
        assert analyzer._activated is False

    def test_do_activate_abstract_method(self):
        """测试_do_activate是抽象方法"""
        # 直接实例化BaseAnalyzer（不实现抽象方法）
        # 因为ConcreteAnalyzer实现了_do_activate，这里用另一种方式验证
        # 直接调用BaseAnalyzer._do_activate应抛出NotImplementedError
        analyzer = BaseAnalyzer(name="AbstractTest")

        with pytest.raises(NotImplementedError, match="_do_activate"):
            analyzer._do_activate(RECORDSTAGE_TYPES.NEWDAY, {})

    def test_activate_performance_tracking(self):
        """测试activate性能追踪"""
        import time

        analyzer = ConcreteAnalyzer(name="PerfTrackTest")
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)

        assert analyzer._activation_count == 0
        assert analyzer._total_activation_time == 0.0

        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, {"cash": 100000})

        # 验证_activation_count增加
        assert analyzer._activation_count == 1

        # 验证_total_activation_time增加
        assert analyzer._total_activation_time > 0.0

        # 性能摘要应反映调用
        summary = analyzer.performance_summary
        assert summary['activation_count'] == 1
        assert summary['avg_activation_time'] > 0.0


@pytest.mark.unit
class TestRecordTemplateMethod:
    """3. record()模板方法测试"""

    def test_record_calls_do_record(self):
        """测试record调用_do_record"""
        analyzer = ConcreteAnalyzer(name="RecordTest")
        # 默认_record_stage就是NEWDAY

        portfolio_info = {"cash": 100000}

        analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 验证_do_record()被调用
        assert analyzer._recorded is True
        assert analyzer._last_record_stage == RECORDSTAGE_TYPES.NEWDAY
        assert analyzer._last_record_info == portfolio_info

    def test_record_stage_filtering(self):
        """测试record的阶段过滤"""
        analyzer = ConcreteAnalyzer(name="RecordFilterTest")
        # _record_stage默认是NEWDAY

        # 在NEWDAY阶段记录
        analyzer.record(RECORDSTAGE_TYPES.NEWDAY, {"cash": 100000})
        assert analyzer._recorded is True

        # 其他阶段不应调用_do_record
        analyzer._recorded = False
        analyzer.record(RECORDSTAGE_TYPES.ORDERSEND, {"cash": 100000})
        assert analyzer._recorded is False

    def test_do_record_abstract_method(self):
        """测试_do_record是抽象方法"""
        analyzer = BaseAnalyzer(name="AbstractRecordTest")

        with pytest.raises(NotImplementedError, match="_do_record"):
            analyzer._do_record(RECORDSTAGE_TYPES.NEWDAY, {})

    def test_record_performance_tracking(self):
        """测试record性能追踪"""
        analyzer = ConcreteAnalyzer(name="RecordPerfTest")

        assert analyzer._record_count == 0
        assert analyzer._total_record_time == 0.0

        analyzer.record(RECORDSTAGE_TYPES.NEWDAY, {"cash": 100000})

        # 验证_record_count增加
        assert analyzer._record_count == 1

        # 验证_total_record_time增加
        assert analyzer._total_record_time > 0.0

        # 性能摘要应反映调用
        summary = analyzer.performance_summary
        assert summary['record_count'] == 1
        assert summary['avg_record_time'] > 0.0


@pytest.mark.unit
class TestStageHookMechanism:
    """4. 阶段钩子机制测试"""

    def test_active_stage_hook_list(self):
        """测试_active_stage钩子列表"""
        analyzer = ConcreteAnalyzer(name="MultiStageTest")

        # 设置多个激活阶段
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        analyzer.add_active_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
        analyzer.add_active_stage(RECORDSTAGE_TYPES.ORDERFILLED)

        assert len(analyzer._active_stage) == 3
        assert RECORDSTAGE_TYPES.NEWDAY in analyzer._active_stage
        assert RECORDSTAGE_TYPES.SIGNALGENERATION in analyzer._active_stage
        assert RECORDSTAGE_TYPES.ORDERFILLED in analyzer._active_stage

        # 验证这些阶段都会触发activate()
        portfolio_info = {"cash": 100000}

        for stage in [RECORDSTAGE_TYPES.NEWDAY, RECORDSTAGE_TYPES.SIGNALGENERATION, RECORDSTAGE_TYPES.ORDERFILLED]:
            analyzer._activated = False
            analyzer.activate(stage, portfolio_info)
            assert analyzer._activated is True

    def test_record_stage_single_hook(self):
        """测试_record_stage单一钩子"""
        analyzer = ConcreteAnalyzer(name="SingleHookTest")

        # _record_stage是单一值，不是列表
        assert isinstance(analyzer._record_stage, RECORDSTAGE_TYPES)

        # 设置到特定阶段
        analyzer.set_record_stage(RECORDSTAGE_TYPES.ORDERSEND)
        assert analyzer._record_stage == RECORDSTAGE_TYPES.ORDERSEND

        # 验证只有该阶段触发record()
        analyzer.record(RECORDSTAGE_TYPES.ORDERSEND, {"cash": 100000})
        assert analyzer._recorded is True

        analyzer._recorded = False
        analyzer.record(RECORDSTAGE_TYPES.NEWDAY, {"cash": 100000})
        assert analyzer._recorded is False

    def test_stage_enum_validation(self):
        """测试阶段枚举验证"""
        analyzer = ConcreteAnalyzer(name="EnumValidationTest")

        # set_record_stage只接受RECORDSTAGE_TYPES枚举
        # 传入非枚举值应被忽略（不会报错但也不会设置）
        original_stage = analyzer._record_stage
        analyzer.set_record_stage("not_a_stage")
        assert analyzer._record_stage == original_stage, "非枚举值不应改变record_stage"

        # 正常枚举值应被接受
        analyzer.set_record_stage(RECORDSTAGE_TYPES.ORDERFILLED)
        assert analyzer._record_stage == RECORDSTAGE_TYPES.ORDERFILLED

    def test_portfolio_info_parameter_passing(self):
        """测试portfolio_info参数传递"""
        analyzer = ConcreteAnalyzer(name="ParamPassingTest")
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)

        portfolio_info = {
            "cash": 50000.0,
            "worth": 200000.0,
            "positions": [{"code": "000001.SZ", "volume": 100, "price": 15.0}]
        }

        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 验证portfolio_info完整传递给_do_activate
        assert analyzer._last_portfolio_info == portfolio_info
        assert analyzer._last_portfolio_info["cash"] == 50000.0
        assert analyzer._last_portfolio_info["worth"] == 200000.0
        assert len(analyzer._last_portfolio_info["positions"]) == 1


@pytest.mark.unit
class TestAnalyzerExtensibility:
    """5. 分析器扩展性测试"""

    def test_subclass_override_template_methods(self):
        """测试子类重写模板方法"""
        custom_values = []

        class CustomAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                custom_values.append(("activate", stage.name))

            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                custom_values.append(("record", stage.name))

        analyzer = CustomAnalyzer(name="CustomTest")
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)

        portfolio_info = {"cash": 100000}
        analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)
        analyzer.record(RECORDSTAGE_TYPES.NEWDAY, portfolio_info)

        # 验证自定义逻辑被正确执行
        assert len(custom_values) == 2
        assert custom_values[0] == ("activate", "NEWDAY")
        assert custom_values[1] == ("record", "NEWDAY")

    def test_subclass_inherits_performance_monitoring(self):
        """测试子类继承性能监控"""

        class SimpleAnalyzer(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass

            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass

        analyzer = SimpleAnalyzer(name="SimplePerfTest")
        analyzer.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)

        # 多次调用activate和record
        for _ in range(5):
            analyzer.activate(RECORDSTAGE_TYPES.NEWDAY, {"cash": 100000})
            analyzer.record(RECORDSTAGE_TYPES.NEWDAY, {"cash": 100000})

        # 验证性能统计对子类透明
        assert analyzer._activation_count == 5
        assert analyzer._record_count == 5
        assert analyzer._total_activation_time > 0.0
        assert analyzer._total_record_time > 0.0

        summary = analyzer.performance_summary
        assert summary['activation_count'] == 5
        assert summary['record_count'] == 5

    def test_analyzer_polymorphism(self):
        """测试分析器多态性"""

        class AnalyzerA(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass

            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass

        class AnalyzerB(BaseAnalyzer):
            def _do_activate(self, stage, portfolio_info, *args, **kwargs):
                pass

            def _do_record(self, stage, portfolio_info, *args, **kwargs):
                pass

        analyzer_a = AnalyzerA(name="AnalyzerA")
        analyzer_b = AnalyzerB(name="AnalyzerB")

        # 验证都符合BaseAnalyzer类型（里氏替换原则）
        assert isinstance(analyzer_a, BaseAnalyzer)
        assert isinstance(analyzer_b, BaseAnalyzer)

        # 可以作为BaseAnalyzer类型使用
        analyzers: list[BaseAnalyzer] = [analyzer_a, analyzer_b]
        assert len(analyzers) == 2

        # 验证BaseAnalyzer接口一致性
        for analyzer in analyzers:
            assert callable(getattr(analyzer, 'activate', None))
            assert callable(getattr(analyzer, 'record', None))
            assert callable(getattr(analyzer, 'add_active_stage', None))
            assert callable(getattr(analyzer, 'set_record_stage', None))
            assert getattr(analyzer, 'performance_summary', None) is not None
