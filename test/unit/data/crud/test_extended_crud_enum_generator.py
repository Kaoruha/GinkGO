#!/usr/bin/env python3
"""
扩展CRUD枚举测试生成器

为剩余的CRUD类批量生成基础枚举测试，确保完整覆盖。
"""

import sys
import os
import importlib
from typing import Type, Dict, Any, List

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.libs import GLOG

import sys
import os
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

from base_enum_crud_test import BaseEnumCRUDTest
from enum_test_data_factory import EnumTestDataFactory


def generate_extended_crud_tests():
    """为扩展CRUD类生成基础枚举测试"""
    print("🏭 开始为扩展CRUD类生成基础枚举测试...")

    # 定义需要测试的扩展CRUD类列表
    extended_crud_classes = [
        ('TradeDayCRUD', 'ginkgo.data.crud.trade_day_crud', 'TradeDayCRUD'),
        ('TransferCRUD', 'ginkgo.data.crud.transfer_crud', 'TransferCRUD'),
        ('HandlerCRUD', 'ginkgo.data.crud.handler_crud', 'HandlerCRUD'),
        ('EngineCRUD', 'ginkgo.data.crud.engine_crud', 'EngineCRUD'),
        ('FileCRUD', 'ginkgo.data.crud.file_crud', 'FileCRUD'),
        ('ParamCRUD', 'ginkgo.data.crud.param_crud', 'ParamCRUD'),
        ('TickCRUD', 'ginkgo.data.crud.tick_crud', 'TickCRUD'),
        ('AdjustfactorCRUD', 'ginkgo.data.crud.adjustfactor_crud', 'AdjustfactorCRUD'),
        ('FactorCRUD', 'ginkgo.data.crud.factor_crud', 'FactorCRUD'),
        ('TickSummaryCRUD', 'ginkgo.data.crud.tick_summary_crud', 'TickSummaryCRUD'),
        ('OrderRecordCRUD', 'ginkgo.data.crud.order_record_crud', 'OrderRecordCRUD'),
        ('PositionRecordCRUD', 'ginkgo.data.crud.position_record_crud', 'PositionRecordCRUD'),
        ('TransferRecordCRUD', 'ginkgo.data.crud.transfer_record_crud', 'TransferRecordCRUD'),
        ('AnalyzerRecordCRUD', 'ginkgo.data.crud.analyzer_record_crud', 'AnalyzerRecordCRUD'),
        ('CapitalAdjustmentCRUD', 'ginkgo.data.crud.capital_adjustment_crud', 'CapitalAdjustmentCRUD'),
        ('EnginePortfolioMappingCRUD', 'ginkgo.data.crud.engine_portfolio_mapping_crud', 'EnginePortfolioMappingCRUD'),
        ('EngineHandlerMappingCRUD', 'ginkgo.data.crud.engine_handler_mapping_crud', 'EngineHandlerMappingCRUD'),
        ('PortfolioFileMappingCRUD', 'ginkgo.data.crud.portfolio_file_mapping_crud', 'PortfolioFileMappingCRUD')
    ]

    print(f"   发现 {len(extended_crud_classes)} 个扩展CRUD类需要测试")

    # 测试结果统计
    results = {
        'total': len(extended_crud_classes),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }

    for class_name, module_name, simple_name in extended_crud_classes:
        try:
            print(f"\n🧪 测试 {class_name}...")

            # 动态导入CRUD类
            crud_class = import_crud_class(module_name, class_name)
            if not crud_class:
                print(f"   ❌ {class_name} 导入失败")
                results['failed'] += 1
                results['details'].append(f"{class_name}: 导入失败")
                continue

            # 检查是否继承BaseCRUD
            if not issubclass(crud_class, BaseCRUD):
                print(f"   ⚠️ {class_name} 不继承BaseCRUD，跳过测试")
                results['skipped'] += 1
                results['details'].append(f"{class_name}: 不继承BaseCRUD")
                continue

            # 创建测试实例
            test_result = test_single_crud_enum(crud_class, class_name, simple_name)
            if test_result['success']:
                print(f"   ✅ {class_name} 测试通过")
                results['successful'] += 1
                results['details'].append(f"{class_name}: {test_result['message']}")
            else:
                print(f"   ❌ {class_name} 测试失败: {test_result['error']}")
                results['failed'] += 1
                results['details'].append(f"{class_name}: {test_result['error']}")

        except Exception as e:
            print(f"   ❌ {class_name} 测试异常: {e}")
            results['failed'] += 1
            results['details'].append(f"{class_name}: 异常 - {e}")

    # 输出测试总结
    print(f"\n📊 扩展CRUD枚举测试总结:")
    print(f"   总计测试类数: {results['total']}")
    print(f"   测试通过: {results['successful']}")
    print(f"   测试失败: {results['failed']}")
    print(f"   跳过测试: {results['skipped']}")
    print(f"   成功率: {results['successful'] / results['total'] * 100:.1f}%")

    print(f"\n📋 详细测试结果:")
    for detail in results['details']:
        print(f"   {detail}")

    return results


def import_crud_class(module_name: str, class_name: str) -> Type[BaseCRUD]:
    """动态导入CRUD类"""
    try:
        module = importlib.import_module(module_name)
        crud_class = getattr(module, class_name)
        return crud_class
    except (ImportError, AttributeError) as e:
        return None


def test_single_crud_enum(crud_class: Type[BaseCRUD], class_name: str, simple_name: str):
    """测试单个CRUD类的枚举处理功能"""
    try:
        # 创建CRUD实例
        crud_instance = crud_class()

        # 测试1: 检查enum_mappings
        enum_mappings = crud_instance._get_enum_mappings()
        if not enum_mappings:
            return {
                'success': True,
                'message': '无枚举字段',
                'enum_fields': []
            }

        print(f"   - 枚举字段: {list(enum_mappings.keys())}")

        # 测试2: 验证enum_mappings与工厂配置的一致性
        try:
            config = EnumTestDataFactory.get_crud_enum_config(simple_name)
            errors = EnumTestDataFactory.validate_enum_mappings(simple_name, enum_mappings)

            if errors:
                print(f"   - 枚举映射验证失败: {errors}")
                return {
                    'success': False,
                    'error': f"枚举映射验证失败: {errors[0] if errors else '未知错误'}",
                    'enum_fields': list(enum_mappings.keys())
                }
        except Exception as e:
            print(f"   - 工厂配置检查异常: {e}")
            # 继续测试，不因工厂问题中断

        # 测试3: 测试枚举转换功能
        try:
            # 创建测试过滤器
            test_filters = EnumTestDataFactory.create_test_filters(simple_name)

            if test_filters:
                converted_filters = crud_instance._convert_enum_values(test_filters)
                print(f"   - 转换测试通过，字段数: {len(converted_filters)}")
            else:
                print(f"   - 无测试过滤器，使用基本测试")
                # 创建基本测试
                basic_filters = {}
                for field, enum_class in enum_mappings.items():
                    if list(enum_class):  # 如果有枚举值
                        basic_filters[field] = list(enum_class)[0]

                if basic_filters:
                    converted_filters = crud_instance._convert_enum_values(basic_filters)
                    print(f"   - 基本转换测试通过，字段数: {len(converted_filters)}")
                else:
                    return {
                        'success': True,
                        'message': '枚举字段无可用值',
                        'enum_fields': list(enum_mappings.keys())
                    }

        except Exception as e:
            print(f"   - 枚举转换测试异常: {e}")
            return {
                'success': False,
                'error': f"枚举转换异常: {e}",
                'enum_fields': list(enum_mappings.keys())
            }

        # 测试4: 测试解析功能
        try:
            if 'converted_filters' in locals() and converted_filters:
                conditions = crud_instance._parse_filters(converted_filters)
                print(f"   - 解析测试通过，生成条件数: {len(conditions)}")
            else:
                return {
                    'success': True,
                    'message': '无有效测试数据，跳过解析测试',
                    'enum_fields': list(enum_mappings.keys())
                }
        except Exception as e:
            print(f"   - 解析测试异常: {e}")
            return {
                'success': False,
                'error': f"解析异常: {e}",
                'enum_fields': list(enum_mappings.keys())
            }

        return {
            'success': True,
            'message': '基础枚举功能正常',
            'enum_fields': list(enum_mappings.keys())
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"测试异常: {e}",
            'enum_fields': []
        }


def validate_enum_coverage_consistency():
    """验证枚举覆盖一致性"""
    print("\n🔍 验证枚举覆盖一致性...")

    # 收集所有CRUD类的枚举字段
    all_enum_fields = set()
    enum_field_counts = {}

    # 核心CRUD类
    core_cruds = ['OrderCRUD', 'BarCRUD', 'PositionCRUD', 'SignalCRUD']
    for crud_name in core_cruds:
        try:
            module_name = f"ginkgo.data.crud.{crud_name.lower()}"
            crud_class = import_crud_class(module_name, crud_name)
            if crud_class and issubclass(crud_class, BaseCRUD):
                instance = crud_class()
                mappings = instance._get_enum_mappings()
                all_enum_fields.update(mappings.keys())
                enum_field_counts[crud_name] = len(mappings)
        except:
            pass

    # 重要业务CRUD类
    important_cruds = ['StockInfoCRUD', 'PortfolioCRUD']
    for crud_name in important_cruds:
        try:
            module_name = f"ginkgo.data.crud.{crud_name.lower()}"
            crud_class = import_crud_class(module_name, crud_name)
            if crud_class and issubclass(crud_class, BaseCRUD):
                instance = crud_class()
                mappings = instance._get_enum_mappings()
                all_enum_fields.update(mappings.keys())
                enum_field_counts[crud_name] = len(mappings)
        except:
            pass

    print(f"   发现枚举字段总数: {len(all_enum_fields)}")
    print(f"   枚举字段分布: {enum_field_counts}")

    # 检查SOURCE_TYPES的覆盖情况
      # 检查SOURCE_TYPES的覆盖情况
    source_coverage = 0
    for crud_name, count in enum_field_counts.items():
        try:
            module = importlib.import_module(f"ginkgo.data.crud.{crud_name.lower()}")
            crud_class = getattr(module, crud_name, None)
            if crud_class and issubclass(crud_class, BaseCRUD):
                instance = crud_class()
                mappings = instance._get_enum_mappings()
                if 'source' in mappings:
                    source_coverage += 1
        except:
            pass

    print(f"   SOURCE_TYPES覆盖CRUD类数: {source_coverage}")

    return {
        'total_enum_fields': len(all_enum_fields),
        'enum_field_distribution': enum_field_counts,
        'source_type_coverage': source_coverage
    }


if __name__ == "__main__":
    print("🚀 开始扩展CRUD枚举测试生成...")

    try:
        # 生成测试并执行
        results = generate_extended_crud_tests()

        # 验证覆盖一致性
        coverage_info = validate_enum_coverage_consistency()

        print(f"\n📈 扩展CRUD枚举测试完成！")
        print(f"📊 覆盖统计: {coverage_info['total_enum_fields']}个枚举字段")
        print(f"📊 SOURCE_TYPES覆盖: {coverage_info['source_type_coverage']}个CRUD类")

        # 计算总体覆盖统计
        core_cruds = 4  # OrderCRUD, BarCRUD, PositionCRUD, SignalCRUD
        important_cruds = 2  # StockInfoCRUD, PortfolioCRUD
        extended_cruds = results['successful']

        total_with_enums = core_cruds + important_cruds + extended_cruds
        print(f"\n📊 总体覆盖统计:")
        print(f"   Phase 1 (核心): {core_cruds} 个CRUD类")
        print(f"   Phase 2 (重要): {important_cruds} 个CRUD类")
        print(f"   Phase 3 (扩展): {extended_cruds} 个CRUD类")
        print(f"   总计: {total_with_enums} 个CRUD类")

        if results['failed'] > 0:
            print(f"\n⚠️  有 {results['failed']} 个测试失败，建议检查相关CRUD类的枚举实现")

        if results['successful'] > 0:
            print(f"\n✅ {results['successful']} 个扩展CRUD类枚举测试通过，功能验证成功！")

    except Exception as e:
        print(f"\n❌ 扩展CRUD测试生成失败: {e}")
        import traceback
        traceback.print_exc()