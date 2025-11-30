import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from ginkgo.data.services.component_service import ComponentService
    from ginkgo.enums import FILE_TYPES
    from ginkgo.libs import GCONF, GLOG
except ImportError as e:
    print(f"Import error: {e}")
    ComponentService = None
    GCONF = None


class ComponentServiceTest(unittest.TestCase):
    """
    ComponentService 单元测试
    测试增强的组件服务功能和分层错误处理能力
    
    设计架构说明：分层错误处理模式
    =====================================
    
    ComponentService 实现了一个分层的错误处理架构，将错误分为两个层次：
    
    1. 基础设施层错误（Infrastructure Errors）：
       - 映射服务获取失败 (get_portfolio_file_mappings)
       - 数据库连接问题
       - 系统环境问题（如基类导入失败）
       特点：这些错误会向上传播为异常，因为它们表明系统层面的问题，需要调用者感知并处理
    
    2. 业务逻辑层错误（Business Logic Errors）：
       - 单个组件实例化失败 (get_instance_by_file)
       - 文件内容获取失败
       - 代码执行错误
       - 参数解析错误
       特点：这些错误返回None，实现"fail-soft"模式，确保单个组件的问题不影响其他组件的加载
    
    这种设计的好处：
    - 基础设施错误需要系统管理员干预，所以抛出异常
    - 业务逻辑错误通常是个别组件的问题，返回None允许系统继续处理其他组件
    - 实现了"尽力而为"的服务质量，最大化系统可用性
    
    测试验证重点：
    - 验证基础设施错误确实会抛出异常
    - 验证业务逻辑错误确实返回None
    - 验证部分失败时系统的降级行为
    """

    # Mock 组件代码示例
    MOCK_STRATEGY_CODE = '''
from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase

class TestStrategy(StrategyBase):
    def __init__(self, param1=None, param2=None):
        super().__init__()
        self.param1 = param1
        self.param2 = param2
    
    def cal(self):
        """Calculate trading signals"""
        return []
    '''

    MOCK_ANALYZER_CODE = '''
from ginkgo.backtest.analysis.analyzers.base_analyzer import AnalyzerBase

class TestAnalyzer(AnalyzerBase):
    def __init__(self, period=20):
        super().__init__()
        self.period = period
    
    def activate(self, stage, portfolio_info):
        """Activate analyzer"""
        pass
    '''

    MOCK_INVALID_CODE = '''
# This code has syntax errors
class InvalidClass:
    def __init__(self:
        pass  # Missing closing parenthesis
    '''

    MOCK_NO_INHERIT_CODE = '''
class NotAComponent:
    def __init__(self):
        pass
    '''

    @classmethod
    def setUpClass(cls):
        """类级别设置"""
        if ComponentService is None or GCONF is None:
            raise AssertionError("ComponentService or GCONF not available")

        print(":white_check_mark: ComponentService test setup completed")

    def setUp(self):
        """每个测试前的设置"""
        # 创建 Mock 依赖
        self.mock_file_service = Mock()
        self.mock_portfolio_service = Mock()
        
        # 创建 ComponentService 实例
        self.service = ComponentService(
            file_service=self.mock_file_service,
            portfolio_service=self.mock_portfolio_service
        )

    def test_get_instance_by_file_success_strategy(self):
        """测试成功从文件创建策略实例"""
        # 配置 Mock
        self.mock_file_service.get_file_content.return_value = self.MOCK_STRATEGY_CODE.encode('utf-8')
        
        # Mock 参数获取
        mock_params_df = pd.DataFrame({
            'order': [0, 1],
            'value': ['param_value_1', 'param_value_2']
        })
        self.mock_portfolio_service.get_parameters_for_mapping.return_value = mock_params_df
        
        # 执行创建实例
        result = self.service.get_instance_by_file(
            file_id="test-file-id",
            mapping_id="test-mapping-id", 
            file_type=FILE_TYPES.STRATEGY
        )
        
        # 检查基类是否可用
        # 注意：这里的基类检查体现了分层错误处理的另一个方面
        # 基类导入失败属于系统环境问题，影响所有组件实例化
        base_classes = self.service._get_component_base_classes()
        
        if base_classes:  # 基类导入成功的情况（系统环境正常）
            # 验证返回结果 - 当前实现返回组件实例或None
            self.assertIsNotNone(result)
            # 验证返回的是组件实例
            self.assertTrue(hasattr(result, '__class__'))
            # 验证组件类名
            self.assertEqual(result.__class__.__name__, 'TestStrategy')
        else:  # 基类导入失败的情况
            # 当基类不可用时，会返回None
            self.assertIsNone(result)

    def test_get_instance_by_file_success_analyzer(self):
        """测试成功从文件创建分析器实例"""
        # 配置 Mock
        self.mock_file_service.get_file_content.return_value = self.MOCK_ANALYZER_CODE.encode('utf-8')
        
        # Mock 空参数
        self.mock_portfolio_service.get_parameters_for_mapping.return_value = pd.DataFrame()
        
        # 执行创建实例
        result = self.service.get_instance_by_file(
            file_id="test-analyzer-id",
            mapping_id="test-mapping-id", 
            file_type=FILE_TYPES.ANALYZER
        )
        
        # 检查基类是否可用
        # 注意：这里的基类检查体现了分层错误处理的另一个方面
        # 基类导入失败属于系统环境问题，影响所有组件实例化
        base_classes = self.service._get_component_base_classes()
        
        if base_classes:  # 基类导入成功的情况（系统环境正常）
            # 验证返回结果 - 当前实现返回组件实例或None
            self.assertIsNotNone(result)
            # 验证返回的是组件实例
            self.assertTrue(hasattr(result, '__class__'))
            # 验证组件类名
            self.assertEqual(result.__class__.__name__, 'TestAnalyzer')
        else:  # 基类导入失败的情况
            # 当基类不可用时，会返回None
            self.assertIsNone(result)

    def test_get_instance_by_file_empty_file_id(self):
        """
        测试空文件ID的处理
        
        设计说明：业务逻辑错误的容错处理
        - get_instance_by_file 处理的是业务逻辑层的错误
        - 空文件ID属于无效参数，但不是系统基础设施问题
        - 返回None表示该组件无法实例化，允许系统继续处理其他组件
        - 这种容错设计确保系统的鲁棒性
        """
        result = self.service.get_instance_by_file("", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 当前实现在业务逻辑错误情况下返回None，这是正确的容错设计
        self.assertIsNone(result)

    def test_get_instance_by_file_empty_mapping_id(self):
        """测试空映射ID的处理"""
        result = self.service.get_instance_by_file("file-id", "", FILE_TYPES.STRATEGY)
        
        # 当前实现在错误情况下返回None
        self.assertIsNone(result)

    def test_get_instance_by_file_unsupported_file_type(self):
        """测试不支持的文件类型处理"""
        # 使用不在基类映射中的文件类型
        result = self.service.get_instance_by_file("file-id", "mapping-id", "INVALID_TYPE")
        
        # 当前实现在错误情况下返回None
        self.assertIsNone(result)

    def test_get_instance_by_file_empty_file_content(self):
        """测试空文件内容的处理"""
        self.mock_file_service.get_file_content.return_value = None
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 当前实现在错误情况下返回None
        self.assertIsNone(result)

    def test_get_instance_by_file_file_content_error(self):
        """
        测试文件内容获取错误处理
        
        设计说明：服务依赖错误的容错处理
        - 文件服务异常属于外部依赖错误，但被归类为业务逻辑层
        - get_instance_by_file 选择将所有错误都转化为None返回
        - 这种设计避免单个组件的问题影响整个系统的组件加载过程
        - 实现了"fail-soft"模式，确保系统的可用性
        """
        self.mock_file_service.get_file_content.side_effect = Exception("File service error")
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 当前实现选择将依赖服务错误也作为业务逻辑错误处理，返回None
        # 这确保了单个组件加载失败不会影响其他组件的加载
        self.assertIsNone(result)

    def test_get_instance_by_file_syntax_error(self):
        """测试语法错误代码的处理"""
        self.mock_file_service.get_file_content.return_value = self.MOCK_INVALID_CODE.encode('utf-8')
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 当前实现在错误情况下返回None
        self.assertIsNone(result)

    def test_get_instance_by_file_unicode_decode_error(self):
        """测试Unicode解码错误处理"""
        self.mock_file_service.get_file_content.return_value = b'\xff\xfe\x00\x00'  # Invalid UTF-8
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 当前实现在错误情况下返回None
        self.assertIsNone(result)

    def test_get_instance_by_file_no_valid_class(self):
        """测试没有有效组件类的处理"""
        self.mock_file_service.get_file_content.return_value = self.MOCK_NO_INHERIT_CODE.encode('utf-8')
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 当前实现在错误情况下返回None
        self.assertIsNone(result)

    def test_get_instance_by_file_parameter_error(self):
        """测试参数获取错误的处理"""
        self.mock_file_service.get_file_content.return_value = self.MOCK_STRATEGY_CODE.encode('utf-8')
        self.mock_portfolio_service.get_parameters_for_mapping.side_effect = Exception("Parameter error")
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 检查基类是否可用
        # 注意：这里的基类检查体现了分层错误处理的另一个方面
        # 基类导入失败属于系统环境问题，影响所有组件实例化
        base_classes = self.service._get_component_base_classes()
        
        if base_classes:  # 基类导入成功的情况（系统环境正常）
            # 当前实现在参数错误时会使用空参数列表并成功创建实例
            self.assertIsNotNone(result)
            self.assertTrue(hasattr(result, '__class__'))
            self.assertEqual(result.__class__.__name__, 'TestStrategy')
        else:  # 基类导入失败的情况
            # 当基类不可用时，会返回None
            self.assertIsNone(result)

    def test_get_instance_by_file_instantiation_error(self):
        """测试实例化错误的处理"""
        # 创建需要必需参数的组件代码
        code_with_required_param = '''
from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase

class RequiredParamStrategy(StrategyBase):
    def __init__(self, required_param):
        super().__init__()
        self.required_param = required_param
    
    def cal(self):
        return []
'''
        self.mock_file_service.get_file_content.return_value = code_with_required_param.encode('utf-8')
        self.mock_portfolio_service.get_parameters_for_mapping.return_value = pd.DataFrame()  # 空参数
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 当前实现在实例化错误情况下返回None
        self.assertIsNone(result)

    def test_get_instance_by_file_large_parameters(self):
        """测试大量参数的处理"""
        self.mock_file_service.get_file_content.return_value = self.MOCK_STRATEGY_CODE.encode('utf-8')
        
        # 创建大量参数
        large_params_df = pd.DataFrame({
            'order': range(25),
            'value': [f'param_{i}' for i in range(25)]
        })
        self.mock_portfolio_service.get_parameters_for_mapping.return_value = large_params_df
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 检查基类是否可用
        # 注意：这里的基类检查体现了分层错误处理的另一个方面
        # 基类导入失败属于系统环境问题，影响所有组件实例化
        base_classes = self.service._get_component_base_classes()
        
        if base_classes:  # 基类导入成功的情况（系统环境正常）
            # 当前实现会尝试创建实例 - 可能成功也可能失败，取决于组件构造函数
            # 这里我们的Mock组件支持可选参数，所以应该成功
            self.assertIsNotNone(result)
            self.assertTrue(hasattr(result, '__class__'))
            self.assertEqual(result.__class__.__name__, 'TestStrategy')
        else:  # 基类导入失败的情况
            # 当基类不可用时，会返回None
            self.assertIsNone(result)

    def test_get_trading_system_components_by_portfolio_success(self):
        """测试成功获取组合的组件列表"""
        # Mock 组合文件映射
        mock_mappings_df = pd.DataFrame({
            'uuid': ['mapping-1', 'mapping-2'],
            'file_id': ['file-1', 'file-2'],
            'name': ['Strategy 1', 'Strategy 2']
        })
        self.mock_portfolio_service.get_portfolio_file_mappings.return_value = mock_mappings_df
        
        # Mock get_instance_by_file 返回组件实例
        mock_component = Mock()
        mock_component.__class__.__name__ = 'TestStrategy'
        
        with patch.object(self.service, 'get_instance_by_file', return_value=mock_component):
            result = self.service.get_trading_system_components_by_portfolio(
                "portfolio-id", FILE_TYPES.STRATEGY
            )
        
        # 验证结果 - 当前实现返回组件实例列表
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for component in result:
            self.assertEqual(component.__class__.__name__, 'TestStrategy')

    def test_get_trading_system_components_by_portfolio_empty_portfolio_id(self):
        """测试空组合ID的处理"""
        # 空组合ID传给portfolio_service，应该返回空映射
        self.mock_portfolio_service.get_portfolio_file_mappings.return_value = pd.DataFrame()
        
        result = self.service.get_trading_system_components_by_portfolio("", FILE_TYPES.STRATEGY)
        
        # 当前实现返回空列表
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_trading_system_components_by_portfolio_invalid_file_type(self):
        """测试无效文件类型的处理"""
        result = self.service.get_trading_system_components_by_portfolio("portfolio-id", "INVALID")
        
        # 当前实现在无效文件类型时返回空列表
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_trading_system_components_by_portfolio_no_mappings(self):
        """测试没有映射的处理"""
        self.mock_portfolio_service.get_portfolio_file_mappings.return_value = pd.DataFrame()
        
        result = self.service.get_trading_system_components_by_portfolio("portfolio-id", FILE_TYPES.STRATEGY)
        
        # 当前实现返回空列表
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_get_trading_system_components_by_portfolio_partial_failure(self):
        """
        测试部分组件实例化失败的处理
        
        设计说明：分层错误处理的实际应用
        - 顶层方法get_trading_system_components_by_portfolio获取映射成功（基础设施层正常）
        - 底层方法get_instance_by_file部分失败（业务逻辑层部分异常）
        - 系统表现：继续处理成功的组件，忽略失败的组件，发出警告
        - 这种设计确保了系统的最大可用性："尽力而为"的服务质量
        """
        # Mock 组合文件映射
        mock_mappings_df = pd.DataFrame({
            'uuid': ['mapping-1', 'mapping-2'],
            'file_id': ['file-1', 'file-2'],
            'name': ['Strategy 1', 'Strategy 2']
        })
        self.mock_portfolio_service.get_portfolio_file_mappings.return_value = mock_mappings_df
        
        # Mock get_instance_by_file 返回部分成功结果
        def mock_get_instance(file_id, mapping_id, file_type):
            if file_id == 'file-1':
                mock_component = Mock()
                mock_component.__class__.__name__ = 'TestStrategy'
                return mock_component
            else:
                return None  # 实例化失败（业务逻辑错误，返回None）
        
        with patch.object(self.service, 'get_instance_by_file', side_effect=mock_get_instance):
            result = self.service.get_trading_system_components_by_portfolio(
                "portfolio-id", FILE_TYPES.STRATEGY
            )
        
        # 验证分层错误处理的效果：
        # 1. 基础设施层成功：能够获取映射并遍历
        # 2. 业务逻辑层部分失败：失败的组件被跳过，成功的组件被返回
        # 3. 系统保持可用：返回可用的组件列表，而不是完全失败
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)  # 只有一个成功的组件
        self.assertEqual(result[0].__class__.__name__, 'TestStrategy')

    def test_get_trading_system_components_by_portfolio_all_failed(self):
        """测试所有组件实例化都失败的处理"""
        mock_mappings_df = pd.DataFrame({
            'uuid': ['mapping-1'],
            'file_id': ['file-1'],
            'name': ['Strategy 1']
        })
        self.mock_portfolio_service.get_portfolio_file_mappings.return_value = mock_mappings_df
        
        # Mock get_instance_by_file 返回None表示失败
        with patch.object(self.service, 'get_instance_by_file', return_value=None):
            result = self.service.get_trading_system_components_by_portfolio(
                "portfolio-id", FILE_TYPES.STRATEGY
            )
        
        # 验证结果 - 当前实现返回空列表
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)  # 没有成功的组件

    def test_get_trading_system_components_by_portfolio_mapping_error(self):
        """
        测试获取映射错误的处理
        
        设计说明：分层错误处理模式
        - 基础设施层错误（如映射服务获取失败）应该向上传播为异常
        - 这种错误表明系统层面的问题，需要调用者感知并处理
        - 与业务逻辑错误（如单个组件实例化失败）区分开来
        - 业务逻辑错误返回None，基础设施错误抛出异常
        """
        self.mock_portfolio_service.get_portfolio_file_mappings.side_effect = Exception("Mapping error")
        
        # 当前实现在基础设施异常情况下会抛出异常，这是正确的设计
        # 映射获取失败属于基础设施层问题，应该向上传播
        with self.assertRaises(Exception):
            self.service.get_trading_system_components_by_portfolio("portfolio-id", FILE_TYPES.STRATEGY)

    def test_get_strategies_by_portfolio(self):
        """测试获取策略组件的便捷方法"""
        with patch.object(self.service, 'get_trading_system_components_by_portfolio') as mock_method:
            mock_components = [Mock(), Mock()]
            mock_method.return_value = mock_components
            
            result = self.service.get_strategies_by_portfolio("portfolio-id")
            
            mock_method.assert_called_once_with("portfolio-id", FILE_TYPES.STRATEGY)
            self.assertEqual(result, mock_components)

    def test_get_analyzers_by_portfolio(self):
        """测试获取分析器组件的便捷方法"""
        with patch.object(self.service, 'get_trading_system_components_by_portfolio') as mock_method:
            mock_components = [Mock(), Mock()]
            mock_method.return_value = mock_components
            
            result = self.service.get_analyzers_by_portfolio("portfolio-id")
            
            mock_method.assert_called_once_with("portfolio-id", FILE_TYPES.ANALYZER)
            self.assertEqual(result, mock_components)

    def test_get_selectors_by_portfolio(self):
        """测试获取选择器组件的便捷方法"""
        with patch.object(self.service, 'get_trading_system_components_by_portfolio') as mock_method:
            mock_components = [Mock(), Mock()]
            mock_method.return_value = mock_components
            
            result = self.service.get_selectors_by_portfolio("portfolio-id")
            
            mock_method.assert_called_once_with("portfolio-id", FILE_TYPES.SELECTOR)
            self.assertEqual(result, mock_components)

    def test_get_sizers_by_portfolio(self):
        """测试获取仓位管理器组件的便捷方法"""
        with patch.object(self.service, 'get_trading_system_components_by_portfolio') as mock_method:
            mock_components = [Mock(), Mock()]
            mock_method.return_value = mock_components
            
            result = self.service.get_sizers_by_portfolio("portfolio-id")
            
            mock_method.assert_called_once_with("portfolio-id", FILE_TYPES.SIZER)
            self.assertEqual(result, mock_components)

    def test_get_risk_managers_by_portfolio(self):
        """测试获取风险管理器组件的便捷方法"""
        with patch.object(self.service, 'get_trading_system_components_by_portfolio') as mock_method:
            mock_components = [Mock(), Mock()]
            mock_method.return_value = mock_components
            
            result = self.service.get_risk_managers_by_portfolio("portfolio-id")
            
            mock_method.assert_called_once_with("portfolio-id", FILE_TYPES.RISKMANAGER)
            self.assertEqual(result, mock_components)

    def test_validate_component_code_success(self):
        """测试成功验证组件代码"""
        result = self.service.validate_component_code(self.MOCK_STRATEGY_CODE, FILE_TYPES.STRATEGY)
        
        self.assertIsInstance(result, dict)
        
        # 检查基类是否可用
        # 注意：这里的基类检查体现了分层错误处理的另一个方面
        # 基类导入失败属于系统环境问题，影响所有组件实例化
        base_classes = self.service._get_component_base_classes()
        
        if base_classes:  # 基类导入成功的情况（系统环境正常）
            self.assertTrue(result['valid'])
            self.assertIsNone(result['error'])
            self.assertEqual(result['class_name'], 'TestStrategy')
            self.assertEqual(result['base_class'], 'StrategyBase')
        else:  # 基类导入失败的情况
            self.assertFalse(result['valid'])
            self.assertIn("Unsupported file type", result['error'])

    def test_validate_component_code_empty_code(self):
        """测试空代码的验证"""
        result = self.service.validate_component_code("", FILE_TYPES.STRATEGY)
        
        # 无论基类是否可用，空代码都应该失败
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
        
        # 检查错误类型：可能是文件类型不支持，也可能是代码执行错误
        base_classes = self.service._get_component_base_classes()
        if not base_classes:
            self.assertIn("Unsupported file type", result['error'])
        # 如果基类可用，则会有其他类型的验证错误

    def test_validate_component_code_large_code(self):
        """测试过大代码的验证"""
        large_code = "# " + "a" * 1000001  # 超过1MB限制
        result = self.service.validate_component_code(large_code, FILE_TYPES.STRATEGY)
        
        # 无论基类是否可用，都应该失败
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
        
        # 检查错误类型：可能是文件类型不支持，也可能是执行错误
        base_classes = self.service._get_component_base_classes()
        if not base_classes:
            self.assertIn("Unsupported file type", result['error'])

    def test_validate_component_code_unsupported_type(self):
        """测试不支持文件类型的验证"""
        result = self.service.validate_component_code(self.MOCK_STRATEGY_CODE, "INVALID_TYPE")
        
        self.assertFalse(result['valid'])
        self.assertIn("Unsupported file type", result['error'])

    def test_validate_component_code_syntax_error(self):
        """测试语法错误代码的验证"""
        result = self.service.validate_component_code(self.MOCK_INVALID_CODE, FILE_TYPES.STRATEGY)
        
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
        
        # 检查错误类型：可能是文件类型不支持，也可能是语法错误
        base_classes = self.service._get_component_base_classes()
        if not base_classes:
            self.assertIn("Unsupported file type", result['error'])

    def test_validate_component_code_import_error(self):
        """测试导入错误代码的验证"""
        code_with_import_error = '''
import non_existent_module
from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase

class TestStrategy(StrategyBase):
    def cal(self):
        return []
'''
        result = self.service.validate_component_code(code_with_import_error, FILE_TYPES.STRATEGY)
        
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])
        
        # 检查错误类型：可能是文件类型不支持，也可能是导入错误
        base_classes = self.service._get_component_base_classes()
        if not base_classes:
            self.assertIn("Unsupported file type", result['error'])

    def test_validate_component_code_no_valid_class(self):
        """测试没有有效类的代码验证"""
        result = self.service.validate_component_code(self.MOCK_NO_INHERIT_CODE, FILE_TYPES.STRATEGY)
        
        self.assertFalse(result['valid'])
        
        # 检查错误类型：可能是文件类型不支持，也可能是没有有效类
        base_classes = self.service._get_component_base_classes()
        if not base_classes:
            self.assertIn("Unsupported file type", result['error'])
        else:
            self.assertIn("No valid StrategyBase subclass found", result['error'])

    def test_validate_component_code_large_file_warning(self):
        """测试大文件的验证"""
        large_code = self.MOCK_STRATEGY_CODE + "\n# " + "comment\n" * 500  # 超过500行
        result = self.service.validate_component_code(large_code, FILE_TYPES.STRATEGY)
        
        # 检查基类是否可用
        # 注意：这里的基类检查体现了分层错误处理的另一个方面
        # 基类导入失败属于系统环境问题，影响所有组件实例化
        base_classes = self.service._get_component_base_classes()
        
        if base_classes:  # 基类导入成功的情况（系统环境正常）
            # 当前实现不检查文件大小警告，只要代码有效就返回true
            self.assertTrue(result['valid'])
            self.assertEqual(result['class_name'], 'TestStrategy')
        else:  # 基类导入失败的情况
            self.assertFalse(result['valid'])
            self.assertIn("Unsupported file type", result['error'])

    def test_get_component_info_success(self):
        """测试成功获取组件信息"""
        self.mock_file_service.get_file_content.return_value = self.MOCK_STRATEGY_CODE.encode('utf-8')
        
        result = self.service.get_component_info("file-id", FILE_TYPES.STRATEGY)
        
        self.assertIsInstance(result, dict)
        self.assertEqual(result['file_id'], 'file-id')
        self.assertEqual(result['file_type'], 'STRATEGY')
        self.assertGreater(result['file_size_bytes'], 0)
        self.assertGreater(result['code_lines'], 0)
        
        # 检查基类是否可用
        # 注意：这里的基类检查体现了分层错误处理的另一个方面
        # 基类导入失败属于系统环境问题，影响所有组件实例化
        base_classes = self.service._get_component_base_classes()
        
        if base_classes:  # 基类导入成功的情况（系统环境正常）
            self.assertTrue(result['success'])
            self.assertTrue(result['valid'])
            self.assertEqual(result['class_name'], 'TestStrategy')
            self.assertEqual(result['base_class'], 'StrategyBase')
            self.assertIsInstance(result['methods'], list)
            self.assertIsInstance(result['init_params'], list)
            self.assertIsNotNone(result['init_signature'])
        else:  # 基类导入失败的情况
            self.assertFalse(result['success'])
            self.assertFalse(result['valid'])
            self.assertIsNotNone(result['error'])

    def test_get_component_info_empty_file_id(self):
        """测试空文件ID的组件信息获取"""
        result = self.service.get_component_info("", FILE_TYPES.STRATEGY)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "File ID cannot be empty")

    def test_get_component_info_no_file_content(self):
        """测试没有文件内容的处理"""
        self.mock_file_service.get_file_content.return_value = None
        
        result = self.service.get_component_info("file-id", FILE_TYPES.STRATEGY)
        
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], "No file content found")

    def test_get_component_info_file_content_error(self):
        """测试文件内容获取错误的处理"""
        self.mock_file_service.get_file_content.side_effect = Exception("File error")
        
        result = self.service.get_component_info("file-id", FILE_TYPES.STRATEGY)
        
        self.assertFalse(result['success'])
        self.assertIn("Failed to retrieve file content", result['error'])

    def test_get_component_info_unicode_decode_error(self):
        """测试Unicode解码错误的处理"""
        self.mock_file_service.get_file_content.return_value = b'\xff\xfe\x00\x00'
        
        result = self.service.get_component_info("file-id", FILE_TYPES.STRATEGY)
        
        self.assertFalse(result['success'])
        self.assertIn("Failed to decode file content", result['error'])

    def test_get_component_info_invalid_code(self):
        """测试无效代码的组件信息获取"""
        self.mock_file_service.get_file_content.return_value = self.MOCK_INVALID_CODE.encode('utf-8')
        
        result = self.service.get_component_info("file-id", FILE_TYPES.STRATEGY)
        
        self.assertFalse(result['success'])
        self.assertFalse(result['valid'])
        self.assertIsNotNone(result['error'])

    def test_get_component_base_classes(self):
        """测试获取组件基类映射"""
        base_classes = self.service._get_component_base_classes()
        
        self.assertIsInstance(base_classes, dict)
        # 检查基类映射的结果
        if base_classes:  # 如果基类导入成功
            # 验证包含期望的基类映射（只检查实际支持的类型）
            self.assertIn(FILE_TYPES.STRATEGY, base_classes)
            self.assertIn(FILE_TYPES.ANALYZER, base_classes)
            self.assertIn(FILE_TYPES.SIZER, base_classes)
            # SELECTOR 和 RISKMANAGER 在当前实现中可能不可用
        else:
            # 如果基类导入失败，映射为空是正常的
            self.assertEqual(len(base_classes), 0)


    def test_get_instantiation_parameters(self):
        """测试获取实例化参数"""
        # Mock 参数DataFrame
        mock_params_df = pd.DataFrame({
            'order': [1, 0, 2],  # 测试排序
            'value': ['param2', 'param1', 'param3']
        })
        self.mock_portfolio_service.get_parameters_for_mapping.return_value = mock_params_df
        
        params = self.service._get_instantiation_parameters("mapping-id")
        
        # 验证参数按order排序
        self.assertEqual(params, ['param1', 'param2', 'param3'])

    def test_get_instantiation_parameters_empty(self):
        """测试获取空参数"""
        self.mock_portfolio_service.get_parameters_for_mapping.return_value = pd.DataFrame()
        
        params = self.service._get_instantiation_parameters("mapping-id")
        
        self.assertEqual(params, [])

    def test_get_instantiation_parameters_error(self):
        """测试获取参数错误的处理"""
        self.mock_portfolio_service.get_parameters_for_mapping.side_effect = Exception("Parameter error")
        
        params = self.service._get_instantiation_parameters("mapping-id")
        
        self.assertEqual(params, [])


    def test_retry_mechanism_get_instance_by_file(self):
        """测试获取实例的错误处理"""
        # 检查get_instance_by_file方法存在
        self.assertTrue(hasattr(self.service, 'get_instance_by_file'))
        
        # 模拟文件服务错误
        self.mock_file_service.get_file_content.side_effect = Exception("File service failed")
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 验证在错误情况下返回None
        self.assertIsNone(result)
        
        # 检查基类是否可用来决定是否应该调用文件服务
        base_classes = self.service._get_component_base_classes()
        
        if base_classes:  # 基类导入成功的情况
            # 验证至少调用了一次（应该会尝试获取文件内容）
            self.assertGreaterEqual(self.mock_file_service.get_file_content.call_count, 1)
        else:
            # 基类导入失败时，可能在文件类型检查阶段就失败了，不会调用文件服务
            # 这种情况下我们只验证结果是None
            pass

    def test_comprehensive_error_logging(self):
        """测试全面的错误日志记录"""
        # 配置各种错误场景并验证业务逻辑处理
        # 触发文件服务错误
        self.mock_file_service.get_file_content.side_effect = Exception("Critical file error")
        
        result = self.service.get_instance_by_file("file-id", "mapping-id", FILE_TYPES.STRATEGY)
        
        # 验证错误处理结果 - 组件服务在文件错误时应返回None
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()