"""
通用数据验证结果类
用于所有数据类型的验证结果统一返回格式
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class DataValidationResult:
    """通用数据验证结果"""

    # 基础验证信息 - 没有默认值的字段放在前面
    is_valid: bool
    error_count: int
    warning_count: int
    data_quality_score: float  # 0-100
    validation_timestamp: datetime
    validation_type: str  # "business_rules", "data_quality", "integrity"
    entity_type: str    # "bars", "ticks", "stockinfo", "orders" 等
    entity_identifier: str  # 具体实体标识，如股票代码

    # 有默认值的字段放在后面
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, error_message: str):
        """添加错误信息"""
        self.errors.append(error_message)
        self.error_count = len(self.errors)
        # 重新计算质量评分
        self._recalculate_quality_score()

    def add_warning(self, warning_message: str):
        """添加警告信息"""
        self.warnings.append(warning_message)
        self.warning_count = len(self.warnings)
        # 重新计算质量评分
        self._recalculate_quality_score()

    def set_metadata(self, key: str, value: Any):
        """设置实体特定的元数据"""
        self.metadata[key] = value

    def _recalculate_quality_score(self):
        """重新计算数据质量评分"""
        # 基础分数100分
        score = 100.0

        # 每个错误扣10分
        score -= self.error_count * 10

        # 每个警告扣2分
        score -= self.warning_count * 2

        # 确保分数在0-100范围内
        self.data_quality_score = max(0.0, min(100.0, score))

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "is_valid": self.is_valid,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": self.errors,
            "warnings": self.warnings,
            "data_quality_score": self.data_quality_score,
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "validation_type": self.validation_type,
            "entity_type": self.entity_type,
            "entity_identifier": self.entity_identifier,
            "metadata": self.metadata
        }

    @classmethod
    def create_for_entity(
        cls,
        entity_type: str,
        entity_identifier: str,
        validation_type: str = "business_rules"
    ) -> 'DataValidationResult':
        """为特定实体创建验证结果实例"""
        return cls(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type=validation_type,
            entity_type=entity_type,
            entity_identifier=entity_identifier
        )