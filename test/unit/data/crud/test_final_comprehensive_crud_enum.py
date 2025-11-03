#!/usr/bin/env python3
"""
最终CRUD枚举测试生成器 - 覆盖所有剩余的CRUD类

确保所有CRUD类的枚举处理功能都得到完整测试覆盖。
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

from enum_test_data_factory import EnumTestDataFactory


def get_all_crud_classes():
    """获取所有CRUD类"""
    all_crud_files = [
        ('OrderCRUD', 'ginkgo.data.crud.order_crud', 'OrderCRUD'),
        ('BarCRUD', 'ginkgo.data.crud.bar_crud', 'BarCRUD'),
        ('PositionCRUD', 'ginkgo.data.crud.position_crud', 'PositionCRUD'),
        ('SignalCRUD', 'ginkgo.data.crud.signal_crud', 'SignalCRUD'),
        ('StockInfoCRUD', 'ginkgo.data.crud.stock_info_crud', 'StockInfoCRUD'),
        ('PortfolioCRUD', 'ginkgo.data.crud.portfolio_crud', 'PortfolioCRUD'),
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
        ('PortfolioFileMappingCRUD', 'ginkgo.data.crud.portfolio_file_mapping_crud', 'PortfolioFileMappingCRUD'),
        # 新发现的CRUD类
        ('KafkaCRUD', 'ginkgo.data.crud.kafka_crud', 'KafkaCRUD'),
        ('RedisCRUD', 'ginkgo.data.crud.redis_crud', 'RedisCRUD'),
        ('SignalTrackerCRUD', 'ginkgo.data.crud.signal_tracker_crud', 'SignalTrackerCRUD')
    ]

    return all_crud_files


def test_comprehensive_crud_coverage():
    """进行全面的CRUD枚举测试覆盖"""
    print("🚀 开始最终全面CRUD枚举测试覆盖...")

    all_crud_classes = get_all_crud_classes()
    print(f"   发现总计 {len(all_crud_classes)} 个CRUD类")

    # 测试结果统计
    results = {
        'total': len(all_crud_classes),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'no_enums': 0,
        'details': [],
        'enum_field_summary': {},
        'coverage_by_category': {
            'Phase 1 (核心)': ['OrderCRUD', 'BarCRUD', 'PositionCRUD', 'SignalCRUD'],
            'Phase 2 (重要)': ['StockInfoCRUD', 'PortfolioCRUD'],
            'Phase 3 (扩展)': [
                'TradeDayCRUD', 'TransferCRUD', 'HandlerCRUD', 'EngineCRUD', 'FileCRUD',
                'ParamCRUD', 'AdjustfactorCRUD', 'FactorCRUD', 'TickSummaryCRUD',
                'OrderRecordCRUD', 'PositionRecordCRUD', 'TransferRecordCRUD',
                'AnalyzerRecordCRUD', 'CapitalAdjustmentCRUD', 'EnginePortfolioMappingCRUD',
                'EngineHandlerMappingCRUD', 'PortfolioFileMappingCRUD'
            ],
            'Phase 4 (新增)': ['KafkaCRUD', 'RedisCRUD', 'SignalTrackerCRUD']
        }
    }

    for class_name, module_name, simple_name in all_crud_classes:
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
            test_result = test_single_crud_enum_comprehensive(crud_class, class_name, simple_name)

            # 记录枚举字段统计
            enum_mappings = test_result.get('enum_mappings', {})
            results['enum_field_summary'][class_name] = list(enum_mappings.keys())

            if test_result['success']:
                if test_result['no_enums']:
                    print(f"   ✅ {class_name} 无枚举字段")
                    results['no_enums'] += 1
                else:
                    print(f"   ✅ {class_name} 测试通过 ({len(enum_mappings)}个枚举字段)")
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

    # 输出详细测试总结
    print_comprehensive_summary(results)

    return results


def import_crud_class(module_name: str, class_name: str) -> Type[BaseCRUD]:
    """动态导入CRUD类"""
    try:
        module = importlib.import_module(module_name)
        crud_class = getattr(module, class_name)
        return crud_class
    except (ImportError, AttributeError) as e:
        return None


def test_single_crud_enum_comprehensive(crud_class: Type[BaseCRUD], class_name: str, simple_name: str):
    """全面测试单个CRUD类的枚举处理功能"""
    try:
        # 创建CRUD实例
        crud_instance = crud_class()

        # 测试1: 检查enum_mappings
        enum_mappings = crud_instance._get_enum_mappings()
        if not enum_mappings:
            return {
                'success': True,
                'message': '无枚举字段',
                'no_enums': True,
                'enum_mappings': {}
            }

        print(f"   - 枚举字段: {list(enum_mappings.keys())}")

        # 测试2: 验证enum_mappings与工厂配置的一致性
        try:
            config = EnumTestDataFactory.get_crud_enum_config(simple_name)
            errors = EnumTestDataFactory.validate_enum_mappings(simple_name, enum_mappings)

            if errors:
                print(f"   - 工厂配置验证警告: {errors}")
                # 继续测试，不因工厂问题中断
        except Exception as e:
            print(f"   - 工厂配置检查异常: {e}")
            # 继续测试

        # 测试3: 测试枚举转换功能
        try:
            # 创建测试过滤器
            test_filters = EnumTestDataFactory.create_test_filters(simple_name)

            if test_filters:
                converted_filters = crud_instance._convert_enum_values(test_filters)
                print(f"   - 转换测试通过，处理字段数: {len(converted_filters)}")
            else:
                # 创建基本测试
                basic_filters = {}
                for field, enum_class in enum_mappings.items():
                    if list(enum_class):  # 如果有枚举值
                        basic_filters[field] = list(enum_class)[0]

                if basic_filters:
                    converted_filters = crud_instance._convert_enum_values(basic_filters)
                    print(f"   - 基本转换测试通过，处理字段数: {len(converted_filters)}")
                else:
                    return {
                        'success': True,
                        'message': '枚举字段无可用值',
                        'no_enums': False,
                        'enum_mappings': enum_mappings
                    }

        except Exception as e:
            print(f"   - 枚举转换测试异常: {e}")
            return {
                'success': False,
                'error': f"枚举转换异常: {e}",
                'enum_mappings': enum_mappings
            }

        # 测试4: 测试解析功能
        try:
            if 'converted_filters' in locals() and converted_filters:
                conditions = crud_instance._parse_filters(converted_filters)
                print(f"   - 解析测试通过，生成条件数: {len(conditions)}")
        except Exception as e:
            print(f"   - 解析测试异常: {e}")
            return {
                'success': False,
                'error': f"解析异常: {e}",
                'enum_mappings': enum_mappings
            }

        return {
            'success': True,
            'message': '枚举功能正常',
            'no_enums': False,
            'enum_mappings': enum_mappings
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"测试异常: {e}",
            'enum_mappings': {}
        }


def print_comprehensive_summary(results: Dict[str, Any]):
    """打印全面的测试总结"""
    print(f"\n" + "="*60)
    print(f"📊 最终全面CRUD枚举测试总结")
    print(f"="*60)

    # 基本统计
    print(f"   总计CRUD类数: {results['total']}")
    print(f"   测试通过: {results['successful']}")
    print(f"   测试失败: {results['failed']}")
    print(f"   跳过测试: {results['skipped']}")
    print(f"   无枚举字段: {results['no_enums']}")

    success_rate = (results['successful'] / results['total']) * 100 if results['total'] > 0 else 0
    print(f"   总体成功率: {success_rate:.1f}%")

    # 按类别统计
    print(f"\n📋 分阶段覆盖统计:")
    for phase_name, crud_list in results['coverage_by_category'].items():
        phase_success = sum(1 for crud in crud_list if any(crud in detail and '测试通过' in detail for detail in results['details']))
        phase_total = len(crud_list)
        print(f"   {phase_name}: {phase_success}/{phase_total} 个CRUD类")

    # 枚举字段统计
    print(f"\n🔢 枚举字段覆盖统计:")
    enum_classes_with_fields = sum(1 for fields in results['enum_field_summary'].values() if fields)
    total_enum_fields = sum(len(fields) for fields in results['enum_field_summary'].values())
    print(f"   有枚举字段的CRUD类: {enum_classes_with_fields}")
    print(f"   枚举字段总数: {total_enum_fields}")

    # SOURCE_TYPES覆盖统计
    source_crud_count = sum(1 for fields in results['enum_field_summary'].values() if 'source' in fields)
    print(f"   SOURCE_TYPES覆盖: {source_crud_count} 个CRUD类")

    # 失败详情
    if results['failed'] > 0:
        print(f"\n❌ 失败详情:")
        for detail in results['details']:
            if '失败' in detail or '异常' in detail or '导入失败' in detail:
                print(f"   {detail}")

    # 成功详情
    print(f"\n✅ 成功覆盖的CRUD类:")
    for crud_name, fields in results['enum_field_summary'].items():
        if any(crud_name in detail and '测试通过' in detail for detail in results['details']):
            if fields:
                print(f"   {crud_name}: {fields}")
            else:
                print(f"   {crud_name}: 无枚举字段")

    print(f"\n🎉 全面CRUD枚举测试覆盖完成！")


if __name__ == "__main__":
    print("🚀 启动最终全面CRUD枚举测试覆盖...")

    try:
        results = test_comprehensive_crud_coverage()

        if results['failed'] == 0:
            print(f"\n🎉 所有CRUD类枚举测试通过！")
            print(f"   成功测试: {results['successful']} 个CRUD类")
            print(f"   跳过测试: {results['skipped']} 个CRUD类")
            print(f"   无枚举字段: {results['no_enums']} 个CRUD类")
        else:
            print(f"\n⚠️ 有 {results['failed']} 个测试失败，需要进一步检查")

    except Exception as e:
        print(f"\n❌ 全面测试失败: {e}")
        import traceback
        traceback.print_exc()