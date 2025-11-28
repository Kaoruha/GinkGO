"""
通用数据完整性检查结果类
用于所有数据类型的完整性检查统一返回格式
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
from datetime import datetime


@dataclass
class DataIntegrityCheckResult:
    """通用数据完整性检查结果"""

    # 基础检查信息 - 没有默认值的字段放在前面
    entity_type: str    # "bars", "ticks", "stockinfo" 等
    entity_identifier: str  # 具体实体标识
    check_range: Tuple[datetime, datetime]
    total_records: int
    missing_records: int
    duplicate_records: int
    integrity_score: float  # 0-100
    check_duration: float  # 检查耗时（秒）

    # 有默认值的字段放在后面
    integrity_issues: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue_type: str, description: str, location: Any = None):
        """添加完整性问题"""
        issue = {
            "type": issue_type,
            "description": description,
            "location": location,
            "timestamp": datetime.now()
        }
        self.integrity_issues.append(issue)
        # 重新计算完整性评分
        self._recalculate_integrity_score()

    def add_recommendation(self, recommendation: str):
        """添加改进建议"""
        self.recommendations.append(recommendation)

    def set_metadata(self, key: str, value: Any):
        """设置实体特定的元数据"""
        self.metadata[key] = value

    def _recalculate_integrity_score(self):
        """重新计算完整性评分"""
        # 基础分数100分
        score = 100.0

        # 缺失记录影响评分
        if self.total_records > 0:
            missing_ratio = self.missing_records / self.total_records
            score -= missing_ratio * 50  # 缺失最多扣50分

        # 重复记录影响评分
        if self.total_records > 0:
            duplicate_ratio = self.duplicate_records / self.total_records
            score -= duplicate_ratio * 30  # 重复最多扣30分

        # 其他问题影响评分
        score -= len(self.integrity_issues) * 5  # 每个问题扣5分

        # 确保分数在0-100范围内
        self.integrity_score = max(0.0, min(100.0, score))

    def is_healthy(self) -> bool:
        """判断数据是否健康（完整性良好）"""
        return (
            self.integrity_score >= 80.0 and
            self.missing_records == 0 and
            self.duplicate_records == 0 and
            len(self.integrity_issues) == 0
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "entity_type": self.entity_type,
            "entity_identifier": self.entity_identifier,
            "check_range": (self.check_range[0].isoformat(), self.check_range[1].isoformat()),
            "total_records": self.total_records,
            "missing_records": self.missing_records,
            "duplicate_records": self.duplicate_records,
            "integrity_issues": self.integrity_issues,
            "integrity_score": self.integrity_score,
            "recommendations": self.recommendations,
            "check_duration": self.check_duration,
            "metadata": self.metadata,
            "is_healthy": self.is_healthy()
        }

    @classmethod
    def create_for_entity(
        cls,
        entity_type: str,
        entity_identifier: str,
        check_range: Tuple[datetime, datetime],
        check_duration: float = 0.0
    ) -> 'DataIntegrityCheckResult':
        """为特定实体创建完整性检查结果实例"""
        return cls(
            entity_type=entity_type,
            entity_identifier=entity_identifier,
            check_range=check_range,
            total_records=0,
            missing_records=0,
            duplicate_records=0,
            integrity_score=100.0,
            check_duration=check_duration
        )