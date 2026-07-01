# Issue #4630: ComponentLoader 提取组件类检测逻辑消除重复
# Upstream: ginkgo.trading.services._assembly.component_loader (_detect_component_class,
#           _is_component_class, COMPONENT_TYPE_INFO, SOURCE_FALLBACK_IMPORT_MAP)
# Downstream: _instantiate_component_from_file 主路径 + 源码 fallback 路径
# Role: 钉住提取后的组件类检测行为（三种检测方法 + 排除规则）与单一类型映射源。
#
# 这些测试在 helper 提取前为 RED（函数/常量不存在），提取后转 GREEN。
# 行为源自主路径原检测逻辑（component_loader.py 250-298），属"钉住既有行为"非想象。

import types

import pytest

from ginkgo.trading.services._assembly.component_loader import (
    COMPONENT_TYPE_INFO,
    SOURCE_FALLBACK_IMPORT_MAP,
    _detect_component_class,
    _is_component_class,
)
from ginkgo.enums import FILE_TYPES


# --------------------------------------------------------------------------- #
# 测试用 fake 组件类（真实 type，带 __bases__，非 SimpleNamespace）
# --------------------------------------------------------------------------- #

class _AbstractThing:
    """模拟抽象类：__abstract__=True、名无组件后缀，三种方法都不应命中。"""
    __abstract__ = True


class _ConcreteBaseStrategy:
    """基类名精确等于 BaseStrategy，供 method 2 精确匹配。"""
    pass


# 给 _ConcreteBaseStrategy 一个能命中 method 2 精确匹配的名字
_ConcreteBaseStrategy.__name__ = "BaseStrategy"
_ConcreteBaseStrategy.__abstract__ = True  # 抽象基类自身不应被当组件


class _InheritedStrategy(_ConcreteBaseStrategy):
    """子类：继承自名为 BaseStrategy 的基类 → method 2 命中。"""
    pass


class _LonelyStrategy:
    """类名以 Strategy 结尾、无识别基类、无 __abstract__ → method 3 命中。

    这是源码 fallback 路径原本缺失的检测能力（AC#2 要求收敛到主路径）。
    """
    pass


class _AbstractFlagged:
    """__abstract__=False、无识别基类/名 → 仅靠 method 1 命中。"""
    __abstract__ = False


class _PlainFoo:
    """无关类，三种方法都不应命中。"""
    pass


class _UnderscoreStrategy:
    """下划线开头，_detect_component_class 应跳过。"""
    pass


# --------------------------------------------------------------------------- #
# _is_component_class：单一类的判定（三种方法 + 排除）
# --------------------------------------------------------------------------- #

class TestIsComponentClass:
    """三种检测方法（任一命中即为组件类）+ 排除规则。"""

    def test_method1_abstract_flagged_is_component(self):
        """method 1：__abstract__ 属性为 False → 组件类"""
        assert _is_component_class(_AbstractFlagged, "_AbstractFlagged") is True

    def test_method1_abstract_true_not_component(self):
        """method 1：__abstract__=True 且名无后缀 → 三种方法都不命中"""
        assert _is_component_class(_AbstractThing, "_AbstractThing") is False

    def test_method2_base_exact_match(self):
        """method 2：基类名精确等于 BaseStrategy → 组件类"""
        assert _is_component_class(_InheritedStrategy, "_InheritedStrategy") is True

    def test_method2_selector_base_suffix(self):
        """method 2：基类名以 SelectorBase 结尾 → 组件类（fallback 原缺）"""
        # 构造一个直接继承名以 SelectorBase 结尾的基类
        BaseSelectorBase = type("BaseSelectorBase", (), {})
        Derived = type("Derived", (BaseSelectorBase,), {})
        assert _is_component_class(Derived, "Derived") is True

    def test_method3_class_name_suffix(self):
        """method 3：类名以 Strategy 结尾、无识别基类 → 组件类（fallback 原缺）"""
        assert _is_component_class(_LonelyStrategy, "_LonelyStrategy") is True

    def test_base_strategy_itself_excluded(self):
        """名为 BaseStrategy 的抽象基类自身不应被当组件（method 3 排除 Base*）"""
        # _ConcreteBaseStrategy 名为 BaseStrategy 且 __abstract__=True
        assert _is_component_class(_ConcreteBaseStrategy, "BaseStrategy") is False

    def test_plain_foo_not_component(self):
        """无关类 Foo 三种方法都不命中"""
        assert _is_component_class(_PlainFoo, "_PlainFoo") is False


# --------------------------------------------------------------------------- #
# _detect_component_class：模块级扫描
# --------------------------------------------------------------------------- #

def _make_module(**attrs) -> types.ModuleType:
    """构造一个临时模块，挂载给定属性。"""
    mod = types.ModuleType("fake_dynamic_component")
    for name, val in attrs.items():
        setattr(mod, name, val)
    return mod


class TestDetectComponentClass:
    """从模块属性中扫描首个组件类。"""

    def test_returns_first_matching_component(self):
        """模块含一个组件类 → 返回该类"""
        mod = _make_module(MyStrategy=_LonelyStrategy)
        result = _detect_component_class(mod)
        assert result is _LonelyStrategy

    def test_skips_underscore_attrs(self):
        """下划线开头的属性被跳过"""
        mod = _make_module(_Hidden=_LonelyStrategy, Visible=_PlainFoo)
        # _Hidden 被跳过，Visible 是 Foo 不命中 → None
        assert _detect_component_class(mod) is None

    def test_returns_none_when_no_component(self):
        """模块无组件类 → None"""
        mod = _make_module(Foo=_PlainFoo, Bar=_PlainFoo)
        assert _detect_component_class(mod) is None

    def test_skips_non_type_attrs(self):
        """非 type 属性（函数/常量）被跳过，组件类按其模块属性名被识别"""
        mod = _make_module(
            some_func=lambda: None,
            COUNT=42,
            RealStrategy=_LonelyStrategy,
        )
        assert _detect_component_class(mod) is _LonelyStrategy

    def test_picks_component_over_noise(self):
        """混杂属性中精确选出组件类"""
        mod = _make_module(
            Helper=_PlainFoo,
            DataValue=42,
            TheStrategy=_LonelyStrategy,
        )
        assert _detect_component_class(mod) is _LonelyStrategy


# --------------------------------------------------------------------------- #
# COMPONENT_TYPE_INFO 单一映射源（AC#3）
# --------------------------------------------------------------------------- #

class TestComponentTypeInfo:
    """type_map 与 SOURCE_FALLBACK_IMPORT_MAP 统一为单一映射源。"""

    @pytest.mark.parametrize("ftype,name", [
        (FILE_TYPES.STRATEGY.value, "strategy"),
        (FILE_TYPES.SELECTOR.value, "selector"),
        (FILE_TYPES.SIZER.value, "sizer"),
        (FILE_TYPES.RISKMANAGER.value, "risk_manager"),
        (FILE_TYPES.ANALYZER.value, "analyzer"),
    ])
    def test_each_type_has_name(self, ftype, name):
        """5 种组件类型在单一源中均有 name 字段"""
        assert COMPONENT_TYPE_INFO[ftype]["name"] == name

    @pytest.mark.parametrize("ftype", [
        FILE_TYPES.STRATEGY.value,
        FILE_TYPES.SELECTOR.value,
        FILE_TYPES.SIZER.value,
        FILE_TYPES.RISKMANAGER.value,
        FILE_TYPES.ANALYZER.value,
    ])
    def test_each_type_has_module_path_and_subpackage(self, ftype):
        """每条记录含 module_path / subpackage（供 fallback 派生）"""
        info = COMPONENT_TYPE_INFO[ftype]
        assert "module_path" in info and isinstance(info["module_path"], str)
        assert "subpackage" in info and isinstance(info["subpackage"], str)

    def test_source_fallback_map_derived_from_single_source(self):
        """SOURCE_FALLBACK_IMPORT_MAP 必须与单一源完全一致（防双映射漂移）"""
        for ftype, info in COMPONENT_TYPE_INFO.items():
            assert SOURCE_FALLBACK_IMPORT_MAP[ftype] == (
                info["module_path"],
                info["subpackage"],
            )

    def test_no_engine_in_mappings(self):
        """ENGINE(=7) 非用户上传组件，不进映射（回归保护，#5880 缺陷4a）"""
        assert FILE_TYPES.ENGINE.value not in COMPONENT_TYPE_INFO
        assert FILE_TYPES.ENGINE.value not in SOURCE_FALLBACK_IMPORT_MAP
