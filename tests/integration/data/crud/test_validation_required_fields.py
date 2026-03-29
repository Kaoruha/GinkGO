"""
validate_data_by_config required=False 测试

测试范围:
1. required=False 字段缺失时不报错
2. required=False 字段存在时正常验证
3. required=False 字段存在但值无效时报错
4. required=True (默认) 字段缺失时报错
5. 混合 required 字段配置
6. required=False 与 default 共存
7. required=False 字段不出现在结果中
"""
import pytest

from ginkgo.data.crud.validation import validate_data_by_config, ValidationError


class TestRequiredFalseSkipping:
    """required=False 字段缺失时跳过验证"""

    def test_optional_field_missing_no_error(self):
        """required=False 字段不在 data 中时不报错"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'memo': {'type': 'string', 'required': False},
        }
        result = validate_data_by_config({'code': '000001.SZ'}, field_config)
        assert result['code'] == '000001.SZ'

    def test_optional_field_missing_not_in_result(self):
        """required=False 字段缺失时不出现在结果中"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'memo': {'type': 'string', 'required': False},
        }
        result = validate_data_by_config({'code': '000001.SZ'}, field_config)
        assert 'memo' not in result

    def test_optional_field_present_validated(self):
        """required=False 字段存在时正常验证"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'memo': {'type': 'string', 'required': False, 'min': 3},
        }
        result = validate_data_by_config({'code': '000001.SZ', 'memo': 'hello'}, field_config)
        assert result['memo'] == 'hello'

    def test_optional_field_present_invalid_raises(self):
        """required=False 字段存在但值无效时仍报错"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'memo': {'type': 'string', 'required': False, 'min': 10},
        }
        with pytest.raises(ValidationError, match='below minimum'):
            validate_data_by_config({'code': '000001.SZ', 'memo': 'hi'}, field_config)

    def test_optional_field_present_type_conversion(self):
        """required=False 字段存在时执行类型转换"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'price': {'type': 'decimal', 'required': False},
        }
        result = validate_data_by_config({'code': '000001.SZ', 'price': '10.5'}, field_config)
        from decimal import Decimal
        assert result['price'] == Decimal('10.5')


class TestRequiredTrueDefault:
    """required=True (默认) 字段缺失时报错"""

    def test_default_required_true_missing_raises(self):
        """未指定 required 时默认为 True，缺失报错"""
        field_config = {
            'code': {'type': 'string'},
        }
        with pytest.raises(ValidationError, match='Missing required field'):
            validate_data_by_config({}, field_config)

    def test_explicit_required_true_missing_raises(self):
        """显式 required=True 字段缺失报错"""
        field_config = {
            'code': {'type': 'string', 'required': True},
        }
        with pytest.raises(ValidationError, match='Missing required field'):
            validate_data_by_config({}, field_config)

    def test_required_true_present_ok(self):
        """required=True 字段存在时正常"""
        field_config = {
            'code': {'type': 'string', 'required': True},
        }
        result = validate_data_by_config({'code': '000001.SZ'}, field_config)
        assert result['code'] == '000001.SZ'


class TestMixedRequiredFields:
    """混合 required 字段配置"""

    def test_all_optional_empty_data(self):
        """全部 required=False 时空数据不报错"""
        field_config = {
            'memo': {'type': 'string', 'required': False},
            'tag': {'type': 'string', 'required': False},
        }
        result = validate_data_by_config({}, field_config)
        assert result == {}

    def test_one_required_one_optional(self):
        """一个必填一个可选"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'memo': {'type': 'string', 'required': False},
        }
        # 只有必填字段
        result = validate_data_by_config({'code': '000001.SZ'}, field_config)
        assert 'code' in result
        assert 'memo' not in result
        # 两个字段都有
        result = validate_data_by_config({'code': '000002.SZ', 'memo': 'test'}, field_config)
        assert result['code'] == '000002.SZ'
        assert result['memo'] == 'test'

    def test_required_missing_with_optional_present(self):
        """必填缺失即使可选存在也报错"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'memo': {'type': 'string', 'required': False},
        }
        with pytest.raises(ValidationError, match='Missing required field.*code'):
            validate_data_by_config({'memo': 'test'}, field_config)


class TestOptionalWithDefault:
    """required=False 与 default 共存"""

    def test_optional_with_default_missing_applies_default(self):
        """required=False 有 default 时缺失字段仍应用默认值"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'status': {'type': 'int', 'required': False, 'default': 0},
        }
        result = validate_data_by_config({'code': '000001.SZ'}, field_config)
        # 步骤1先应用默认值 → 步骤2 required=False 跳过缺失检查
        # 步骤3 required=False 但字段已在 data_with_defaults 中 → 正常验证
        assert result['status'] == 0

    def test_optional_with_default_present(self):
        """required=False 有 default 但字段存在时使用实际值"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'status': {'type': 'int', 'required': False, 'default': 0},
        }
        result = validate_data_by_config({'code': '000001.SZ', 'status': '1'}, field_config)
        assert result['status'] == 1

    def test_required_true_with_default_missing(self):
        """required=True 有 default 时缺失字段使用默认值"""
        field_config = {
            'code': {'type': 'string', 'required': True},
            'status': {'type': 'int', 'required': True, 'default': 0},
        }
        result = validate_data_by_config({'code': '000001.SZ'}, field_config)
        assert result['status'] == 0


class TestEmptyFieldConfig:
    """空字段配置"""

    def test_empty_field_config(self):
        """空 field_config 直接返回 data 副本"""
        result = validate_data_by_config({'code': '000001.SZ'}, {})
        assert result == {'code': '000001.SZ'}

    def test_none_field_config(self):
        """None field_config 直接返回 data 副本"""
        result = validate_data_by_config({'code': '000001.SZ'}, None)
        assert result == {'code': '000001.SZ'}
