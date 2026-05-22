"""BaseCRUD 内部实现：数据验证和 ClickHouse 特殊处理。

此模块是 BaseCRUD 的文件拆分部分，不是独立的 Mixin。
仅通过 BaseCRUD 使用，不对外导出。
"""

from typing import Any, Dict

import pandas as pd

from ginkgo.libs import GLOG


class _Validation:
    """BaseCRUD 的数据验证和 ClickHouse 字符串清理实现。

    依赖 CoreCRUD.__init__ 设置的实例属性：
    - self._is_clickhouse
    - self._is_mysql
    - self._is_mongo
    - self.model_class
    """

ClickHouse string fields that need null byte cleaning (from external sources or user input)
    CLICKHOUSE_STRING_FIELDS = [
        "code",  # Stock code (from external data sources like Tushare, Yahoo)
        "name",  # Names (user-defined)
        "reason",  # Reasons (user input or strategy generated)
        "meta",  # Metadata (may contain external data)
        "desc",  # Descriptions (user input)
        "portfolio_id",  # Portfolio ID (may have FixedString padding)
    ]

    def _clean_clickhouse_strings(self, data):
        """
        Clean ClickHouse FixedString null bytes for configured string fields.

        Args:
            data: Can be a list of values, pandas DataFrame, or single value

        Returns:
            Cleaned data in the same format as input
        """
        if not self._is_clickhouse:
            return data

        # Handle list of string values (for DISTINCT queries)
        if isinstance(data, list):
            return [str(value).strip("\x00") if isinstance(value, str) else value for value in data]

        # Handle pandas DataFrame
        elif isinstance(data, pd.DataFrame) and data.shape[0] > 0:
            df = data.copy()
            for field in self.CLICKHOUSE_STRING_FIELDS:
                if field in df.columns:
                    df[field] = df[field].astype(str).str.replace("\x00", "", regex=False)
            return df

        # Handle single string value
        elif isinstance(data, str):
            return data.strip("\x00")

        return data

    # ============================================================================
    # 配置化数据验证 - 简洁统一的验证方法
    # ============================================================================

    def _validate_before_database(self, data: dict) -> dict:
        """
        两层配置化数据验证：数据库必填字段 + 业务特定字段

        Args:
            data: 待验证的数据字典

        Returns:
            验证并转换后的数据字典

        Raises:
            ValidationError: 当验证失败时
        """
        from ginkgo.data.crud.validation import validate_data_by_config, ValidationError

        try:
            validated = data.copy()

            # 第一层：数据库必填字段验证
            database_required_config = self._get_database_required_config()
            if database_required_config:
                validated = validate_data_by_config(validated, database_required_config)
                GLOG.DEBUG(f"Database required fields validation passed for {self.model_class.__name__}")

            # 第二层：业务特定字段验证
            business_field_config = self._get_field_config()
            if business_field_config:
                validated = validate_data_by_config(validated, business_field_config)
                GLOG.DEBUG(f"Business fields validation passed for {self.model_class.__name__}")

            # 如果两层都没有配置
            if not database_required_config and not business_field_config:
                GLOG.DEBUG(f"No validation config defined for {self.model_class.__name__}, skipping validation")

            GLOG.DEBUG(f"Complete data validation passed for {self.model_class.__name__}")
            return validated

        except ValidationError as e:
            GLOG.ERROR(f"Data validation failed for {self.model_class.__name__}: {e}")
            raise e
        except Exception as e:
            GLOG.ERROR(f"Unexpected error during validation for {self.model_class.__name__}: {e}")
            raise ValidationError(f"Unexpected validation error: {str(e)}")

    def _get_database_required_config(self) -> dict:
        """
        获取数据库必填字段配置 - 基于模型基类定义添加数据时必须传入的字段

        Returns:
            dict: 数据库必填字段配置
        """
        if self._is_mysql:
            return self._get_mysql_required_config()
        elif self._is_clickhouse:
            return self._get_clickhouse_required_config()
        return {}

    def _get_mysql_required_config(self) -> dict:
        """
        MySQL 必填字段配置 - 基于 MMysqlBase

        MMysqlBase 的所有字段都有默认值，因此无必填字段：
        - uuid: 自动生成
        - meta: 默认 "{}"
        - desc: 默认描述文本
        - create_at: 自动生成当前时间
        - update_at: 自动生成当前时间
        - is_del: 默认 False
        - source: 默认 OTHER

        Returns:
            dict: MySQL 必填字段配置（通常为空）
        """
        return {}

    def _get_clickhouse_required_config(self) -> dict:
        """
        ClickHouse 必填字段配置 - 基于 MClickBase

        MClickBase 必填字段：
        - timestamp: 没有默认值，必须传入（MergeTree 排序键）

        其他字段都有默认值：
        - uuid: 自动生成
        - meta: 默认 "{}"
        - desc: 默认描述文本
        - source: 默认 OTHER

        Returns:
            dict: ClickHouse 必填字段配置
        """
        return {"timestamp": {"type": ["datetime", "string"]}}

    def _get_field_config(self) -> dict:
        """
        获取业务字段配置 - 子类重写此方法定义业务必填字段要求

        配置中的所有字段都是必填的，支持的配置参数：
        - type: 字段类型，可以是单个类型或类型列表
        - min/max: 数值范围或字符串长度范围
        - choices: 枚举值列表
        - pattern: 正则表达式（用于字符串）

        Returns:
            dict: 业务字段配置字典，格式如下：
            {
                'field_name': {
                    'type': 'string' | ['int', 'string'],  # 单类型或多类型
                    'min': 0,                               # 最小值/长度
                    'max': 100,                             # 最大值/长度
                    'choices': [value1, value2],            # 枚举值
                    'pattern': r'regex_pattern'             # 正则表达式
                },
                ...
            }

        Example:
            return {
                'code': {'type': 'string', 'pattern': r'^[0-9]{6}\\.(SZ|SH)$'},
                'price': {'type': ['decimal', 'float'], 'min': 0.001},
                'volume': {'type': ['int', 'string'], 'min': 0}
            }
        """
        return {}
