#!/usr/bin/env python3
"""
BaseEnumCRUDTest - CRUD枚举处理测试基类

提供统一的枚举处理测试框架，确保所有CRUD类的枚举功能一致性。
继承此基类的测试类将自动获得标准的枚举处理测试方法。
"""

import pytest
import sys
import os
from typing import Type, Dict, List, Any, Union
from abc import ABC, abstractmethod

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.libs import GLOG


class BaseEnumCRUDTest(ABC):
    """
    CRUD枚举处理测试基类

    提供标准的枚举处理测试模板，所有继承BaseCRUD的CRUD类都应该
    继承此基类并进行相应的枚举处理测试。
    """

    @abstractmethod
    def get_crud_class(self) -> Type[BaseCRUD]:
        """
        返回要测试的CRUD类

        Returns:
            Type[BaseCRUD]: 要测试的CRUD类
        """
        pass

    @abstractmethod
    def get_test_model_data(self) -> Dict[str, Any]:
        """
        返回测试用的模型数据

        Returns:
            Dict[str, Any]: 测试数据字典
        """
        pass

    @abstractmethod
    def get_expected_enum_mappings(self) -> Dict[str, Any]:
        """
        返回预期的枚举字段映射

        Returns:
            Dict[str, Any]: 预期的字段名到枚举类的映射
        """
        pass

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.crud_class = self.get_crud_class()
        self.crud_instance = self.crud_class()
        self.enum_mappings = self.crud_instance._get_enum_mappings()

    @pytest.mark.enum
    def test_enum_mappings_coverage(self):
        """
        测试_enum_mappings()方法覆盖所有预期的枚举字段
        """
        expected_mappings = self.get_expected_enum_mappings()

        # 验证预期字段都在enum_mappings中
        for field, enum_class in expected_mappings.items():
            assert field in self.enum_mappings, f"Missing enum field: {field}"
            assert self.enum_mappings[field] == enum_class, f"Wrong enum class for field {field}"

        # 验证enum_mappings中没有多余的字段
        for field in self.enum_mappings:
            assert field in expected_mappings, f"Unexpected enum field: {field}"

        GLOG.DEBUG(f"✅ {self.crud_class.__name__} enum_mappings coverage test passed")

    @pytest.mark.enum
    def test_convert_enum_values_functionality(self):
        """
        测试_convert_enum_values()方法的功能
        """
        if not self.enum_mappings:
            pytest.skip(f"{self.crud_class.__name__} has no enum fields to test")

        # 创建包含枚举值的测试过滤器
        test_filters = self._create_test_filters_with_enums()

        # 转换枚举值
        converted_filters = self.crud_instance._convert_enum_values(test_filters)

        # 验证枚举值被正确转换为整数
        for field, enum_class in self.enum_mappings.items():
            if field in test_filters:
                original_value = test_filters[field]
                converted_value = converted_filters[field]

                if isinstance(original_value, enum_class):
                    assert converted_value == original_value.value, \
                        f"Enum field {field} should convert to its integer value"
                elif isinstance(original_value, int):
                    assert converted_value == original_value, \
                        f"Integer field {field} should remain unchanged"
                elif isinstance(original_value, list):
                    # 验证列表中的枚举值被转换
                    for i, item in enumerate(original_value):
                        if isinstance(item, enum_class):
                            assert converted_value[i] == item.value, \
                                f"Enum item in list {field}[{i}] should convert to integer"

        GLOG.DEBUG(f"✅ {self.crud_class.__name__} convert_enum_values test passed")

    @pytest.mark.enum
    def test_normalize_single_enum_value(self):
        """
        测试_normalize_single_enum_value()方法
        """
        if not self.enum_mappings:
            pytest.skip(f"{self.crud_class.__name__} has no enum fields to test")

        # 选择第一个枚举字段进行测试
        test_field = list(self.enum_mappings.keys())[0]
        enum_class = self.enum_mappings[test_field]

        # 测试枚举对象转换
        enum_value = list(enum_class)[0]  # 取第一个枚举值
        result = self.crud_instance._normalize_single_enum_value(enum_value, enum_class, test_field)
        assert result == enum_value.value, "Enum object should convert to its integer value"

        # 测试有效整数转换
        int_value = enum_value.value
        result = self.crud_instance._normalize_single_enum_value(int_value, enum_class, test_field)
        assert result == int_value, "Valid integer should remain unchanged"

        # 测试无效整数处理
        invalid_int = 999999  # 通常不会是有效的枚举值
        result = self.crud_instance._normalize_single_enum_value(invalid_int, enum_class, test_field)
        assert result == invalid_int, "Invalid integer should be returned as-is with warning"

        # 测试None值处理
        result = self.crud_instance._normalize_single_enum_value(None, enum_class, test_field)
        assert result is None, "None value should remain None"

        # 测试列表处理
        enum_list = [list(enum_class)[0], list(enum_class)[1]]
        result = self.crud_instance._normalize_single_enum_value(enum_list, enum_class, test_field)
        assert isinstance(result, list), "List should remain as list"
        assert result[0] == enum_list[0].value, "Enum in list should convert to integer"
        assert result[1] == enum_list[1].value, "Enum in list should convert to integer"

        GLOG.DEBUG(f"✅ {self.crud_class.__name__} normalize_single_enum_value test passed")

    @pytest.mark.enum
    def test_parse_filters_with_enums(self):
        """
        测试_parse_filters()方法处理包含枚举的过滤条件
        """
        if not self.enum_mappings:
            pytest.skip(f"{self.crud_class.__name__} has no enum fields to test")

        # 创建包含枚举的复杂过滤条件
        complex_filters = self._create_complex_filters_with_enums()

        # 解析过滤条件
        conditions = self.crud_instance._parse_filters(complex_filters)

        # 验证生成的条件数量
        expected_condition_count = len(complex_filters)
        assert len(conditions) == expected_condition_count, \
            f"Should generate {expected_condition_count} conditions, got {len(conditions)}"

        GLOG.DEBUG(f"✅ {self.crud_class.__name__} parse_filters with enums test passed")

    @pytest.mark.enum
    def test_validate_item_enum_fields(self):
        """
        测试_validate_item_enum_fields()方法
        """
        if not self.enum_mappings:
            pytest.skip(f"{self.crud_class.__name__} has no enum fields to test")

        # 测试字典输入的枚举字段验证
        test_dict = self._create_test_dict_with_enums()
        validated_dict = self.crud_instance._validate_item_enum_fields(test_dict.copy())

        # 验证枚举字段被正确转换
        for field, enum_class in self.enum_mappings.items():
            if field in test_dict:
                original_value = test_dict[field]
                validated_value = validated_dict[field]

                if isinstance(original_value, enum_class):
                    assert validated_value == original_value.value, \
                        f"Dict enum field {field} should convert to integer"
                elif isinstance(original_value, int):
                    assert validated_value == original_value, \
                        f"Dict int field {field} should remain unchanged"

        GLOG.DEBUG(f"✅ {self.crud_class.__name__} validate_item_enum_fields test passed")

    @pytest.mark.enum
    def test_enum_field_combinations(self):
        """
        测试多个枚举字段的组合使用
        """
        if len(self.enum_mappings) < 2:
            pytest.skip(f"{self.crud_class.__name__} has less than 2 enum fields")

        # 创建包含多个枚举字段的测试数据
        combination_filters = {}
        for field, enum_class in self.enum_mappings.items():
            # 为每个枚举字段选择一个枚举值
            enum_value = list(enum_class)[0]
            combination_filters[field] = enum_value

        # 添加一些操作符字段
        for field, enum_class in list(self.enum_mappings.items())[:2]:
            combination_filters[f"{field}__in"] = [list(enum_class)[0], list(enum_class)[1]]

        # 测试转换
        converted_filters = self.crud_instance._convert_enum_values(combination_filters)

        # 验证所有枚举字段都被正确转换
        for field, enum_class in self.enum_mappings.items():
            if field in combination_filters:
                original_value = combination_filters[field]
                converted_value = converted_filters[field]

                if isinstance(original_value, enum_class):
                    assert converted_value == original_value.value, \
                        f"Combination enum field {field} should convert to integer"

        GLOG.DEBUG(f"✅ {self.crud_class.__name__} enum field combinations test passed")

    def _create_test_filters_with_enums(self) -> Dict[str, Any]:
        """
        创建包含枚举值的测试过滤器

        Returns:
            Dict[str, Any]: 包含枚举值的测试过滤器
        """
        filters = {}
        for field, enum_class in self.enum_mappings.items():
            # 为每个枚举字段选择第一个枚举值
            enum_value = list(enum_class)[0]
            filters[field] = enum_value

        return filters

    def _create_complex_filters_with_enums(self) -> Dict[str, Any]:
        """
        创建包含操作符的复杂过滤条件

        Returns:
            Dict[str, Any]: 复杂的过滤条件
        """
        filters = {}

        for i, (field, enum_class) in enumerate(self.enum_mappings.items()):
            if i == 0:
                # 第一个字段使用相等过滤
                filters[field] = list(enum_class)[0]
            elif i == 1:
                # 第二个字段使用in过滤
                filters[f"{field}__in"] = list(enum_class)[:2]
            elif i == 2:
                # 第三个字段使用gte过滤
                filters[f"{field}__gte"] = list(enum_class)[0]
            else:
                # 其他字段使用相等过滤
                filters[field] = list(enum_class)[0]

        # 添加一些模型中实际存在的非枚举字段
        common_fields = ["name", "code", "timestamp", "create_at", "update_at", "uuid"]
        existing_fields = []

        for field in common_fields:
            if hasattr(self.crud_instance.model_class, field):
                existing_fields.append(field)
                if len(existing_fields) >= 2:  # 最多添加2个字段
                    break

        # 为存在的字段添加测试值
        for field in existing_fields:
            if field in ["name", "code"]:
                filters[field] = f"test_{field}"
            elif field in ["timestamp", "create_at", "update_at"]:
                from datetime import datetime
                filters[field] = datetime(2023, 1, 1)
            elif field == "uuid":
                filters[field] = "test-uuid-12345"

        return filters

    def _create_test_dict_with_enums(self) -> Dict[str, Any]:
        """
        创建包含枚举值的测试字典

        Returns:
            Dict[str, Any]: 包含枚举值的测试字典
        """
        dict_data = {}
        for field, enum_class in self.enum_mappings.items():
            # 为每个枚举字段选择一个枚举值
            enum_value = list(enum_class)[0]
            dict_data[field] = enum_value

        # 添加一些非枚举字段
        dict_data.update({
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "volume": 1000
        })

        return dict_data

    @pytest.mark.enum
    def test_enum_conversion_roundtrip(self):
        """
        测试枚举转换的往返一致性

        验证：枚举对象 -> int值 -> 业务对象 -> 枚举对象 的完整转换链
        """
        if not self.enum_mappings:
            pytest.skip(f"{self.crud_class.__name__} has no enum fields to test")

        for field, enum_class in self.enum_mappings.items():
            # 选择一个枚举值进行往返测试
            original_enum = list(enum_class)[0]

            # 第一步：枚举对象 -> int值（通过_normalize_single_enum_value）
            int_value = self.crud_instance._normalize_single_enum_value(
                original_enum, enum_class, field
            )
            assert int_value == original_enum.value, "Enum should convert to correct int value"

            # 第二步：验证int值可以正确转换回枚举
            try:
                restored_enum = enum_class(int_value)
                assert restored_enum == original_enum, "Int should convert back to original enum"
            except ValueError:
                pytest.fail(f"Int value {int_value} should be valid for {enum_class.__name__}")

        GLOG.DEBUG(f"✅ {self.crud_class.__name__} enum conversion roundtrip test passed")

    @pytest.mark.enum
    def test_invalid_enum_handling(self):
        """
        测试无效枚举值的处理
        """
        if not self.enum_mappings:
            pytest.skip(f"{self.crud_class.__name__} has no enum fields to test")

        # 测试无效的枚举值
        for field, enum_class in self.enum_mappings.items():
            # 使用一个通常不会是有效枚举值的整数
            invalid_int = 999999

            # 测试_normalize_single_enum_value对无效值的处理
            result = self.crud_instance._normalize_single_enum_value(
                invalid_int, enum_class, field
            )

            # 无效值应该被原样返回（并记录警告）
            assert result == invalid_int, "Invalid enum value should be returned as-is"

        GLOG.DEBUG(f"✅ {self.crud_class.__name__} invalid enum handling test passed")