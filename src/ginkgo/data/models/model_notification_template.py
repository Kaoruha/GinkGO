# Upstream: NotificationTemplateCRUD (通知模板CRUD操作)、TemplateEngine (模板引擎渲染)
# Downstream: MMongoBase (继承提供MongoDB ORM能力)、TEMPLATE_TYPES (模板类型枚举)
# Role: MNotificationTemplate通知模板模型继承MMongoBase定义模板核心字段(template_id/template_name/template_type/subject/content/variables)支持通知模板管理功能


"""
Notification Template Model

通知模板模型，用于存储和管理各种通知模板。
支持纯文本、Markdown和Discord嵌入格式。
"""

import uuid
import datetime
from typing import Optional, Dict, Any, List
from pydantic import Field, field_validator

from ginkgo.data.models.model_mongobase import MMongoBase
from ginkgo.enums import SOURCE_TYPES, TEMPLATE_TYPES


class MNotificationTemplate(MMongoBase):
    """
    通知模板模型

    用于存储各种通知消息的模板，支持变量替换。
    模板可以用于邮件、Discord消息、Kafka消息等多种通知渠道。

    Attributes:
        template_id: 模板唯一标识符（业务ID，非UUID）
        template_name: 模板显示名称
        template_type: 模板类型（TEXT/MARKDOWN/EMBEDDED）
        subject: 消息主题（可选，用于邮件等）
        content: 模板内容，支持Jinja2语法和变量占位符
        variables: 模板变量定义（JSON格式）
        is_active: 是否启用
        tags: 标签列表（用于分类和搜索）
    """

    # 集合名称
    __collection__ = "notification_templates"

    # 核心字段
    template_id: str = Field(
        ...,
        description="模板唯一标识符（业务ID）",
        min_length=1,
        max_length=64
    )

    template_name: str = Field(
        ...,
        description="模板显示名称",
        min_length=1,
        max_length=128
    )

    template_type: int = Field(
        default=TEMPLATE_TYPES.TEXT.value,
        description="模板类型枚举值"
    )

    subject: Optional[str] = Field(
        default="",
        description="消息主题（用于邮件等）",
        max_length=256
    )

    content: str = Field(
        ...,
        description="模板内容，支持Jinja2语法",
        min_length=1
    )

    variables: str = Field(
        default="{}",
        description="模板变量定义（JSON字符串）"
    )

    is_active: bool = Field(
        default=True,
        description="是否启用此模板"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="模板标签列表"
    )

    # Pydantic 配置
    class Config:
        """Pydantic 配置"""
        from_attributes = True
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "template_id": "trade_signal_alert",
                "template_name": "交易信号提醒",
                "template_type": TEMPLATE_TYPES.MARKDOWN.value,
                "subject": "新交易信号: {{symbol}}",
                "content": "# 交易信号通知\n\n**代码**: {{symbol}}\n**方向**: {{direction}}\n**价格**: {{price}}",
                "variables": '{"symbol": "股票代码", "direction": "方向", "price": "价格"}',
                "is_active": True,
                "tags": ["trading", "signal"]
            }
        }

    @field_validator("template_type")
    @classmethod
    def validate_template_type(cls, v):
        """验证模板类型"""
        if v is None:
            return TEMPLATE_TYPES.TEXT.value
        validated = TEMPLATE_TYPES.validate_input(v)
        if validated is None:
            raise ValueError(f"Invalid template_type: {v}")
        return validated

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, v):
        """验证变量JSON格式"""
        import json
        if not v or v.strip() == "":
            return "{}"
        try:
            json.loads(v)
        except json.JSONDecodeError:
            raise ValueError(f"variables must be valid JSON string: {v}")
        return v

    def get_template_type_enum(self) -> TEMPLATE_TYPES:
        """获取模板类型枚举"""
        return TEMPLATE_TYPES.from_int(self.template_type)

    def get_variables_dict(self) -> Dict[str, Any]:
        """获取变量字典"""
        import json
        try:
            return json.loads(self.variables)
        except json.JSONDecodeError:
            return {}

    def set_variables_dict(self, variables: Dict[str, Any]) -> None:
        """设置变量字典"""
        import json
        self.variables = json.dumps(variables, ensure_ascii=False)

    def get_required_variables(self) -> List[str]:
        """
        从内容中提取必需的变量名

        使用简单的正则表达式提取 {{ variable }} 格式的变量
        """
        import re
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        variables = re.findall(pattern, self.content)
        return list(set(variables))

    def render_content(self, context: Dict[str, Any]) -> str:
        """
        使用 Jinja2 渲染模板内容

        Args:
            context: 变量上下文

        Returns:
            str: 渲染后的内容
        """
        from jinja2 import Template, TemplateError

        try:
            template = Template(self.content)
            return template.render(**context)
        except TemplateError as e:
            raise ValueError(f"Template rendering error: {e}")

    def model_dump_mongo(self) -> Dict[str, Any]:
        """
        转换为 MongoDB 文档格式

        Returns:
            Dict: MongoDB 文档
        """
        return {
            "uuid": self.uuid,
            "template_id": self.template_id,
            "template_name": self.template_name,
            "template_type": self.template_type,
            "subject": self.subject,
            "content": self.content,
            "variables": self.variables,
            "is_active": self.is_active,
            "tags": self.tags,
            "meta": self.meta,
            "desc": self.desc,
            "create_at": self.create_at,
            "update_at": self.update_at,
            "is_del": self.is_del,
            "source": self.source
        }

    @classmethod
    def from_mongo(cls, doc: Dict[str, Any]) -> "MNotificationTemplate":
        """
        从 MongoDB 文档创建模型实例

        Args:
            doc: MongoDB 文档

        Returns:
            MNotificationTemplate: 模型实例
        """
        # 处理 datetime
        if "create_at" in doc and isinstance(doc["create_at"], datetime.datetime):
            pass  # 已经是 datetime
        elif "create_at" in doc and doc["create_at"]:
            doc["create_at"] = datetime.datetime.fromisoformat(doc["create_at"])

        if "update_at" in doc and isinstance(doc["update_at"], datetime.datetime):
            pass  # 已经是 datetime
        elif "update_at" in doc and doc["update_at"]:
            doc["update_at"] = datetime.datetime.fromisoformat(doc["update_at"])

        return cls(**doc)

    def __repr__(self) -> str:
        """字符串表示"""
        type_str = self.get_template_type_enum().name if self.get_template_type_enum() else "UNKNOWN"
        active = "Active" if self.is_active else "Inactive"
        return (
            f"<MNotificationTemplate(uuid={self.uuid[:8]}..., "
            f"template_id={self.template_id}, "
            f"name={self.template_name}, "
            f"type={type_str}, "
            f"{active})>"
        )
