# Upstream: NotificationService (通知服务业务逻辑)、NotifierCLI (命令行工具)
# Downstream: NotificationTemplateCRUD (模板CRUD操作)、Jinja2 (模板渲染库)
# Role: TemplateEngine模板引擎提供模板渲染功能支持Jinja2语法和变量替换支持通知系统功能


"""
Template Engine - 模板渲染引擎

提供基于 Jinja2 的模板渲染功能，支持通知模板的变量替换。
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from jinja2 import Template, Environment, BaseLoader, TemplateError, TemplateSyntaxError, Undefined, StrictUndefined
from jinja2.exceptions import UndefinedError

# 使用 TYPE_CHECKING 避免循环导入
if TYPE_CHECKING:
    from ginkgo.data.crud.notification_template_crud import NotificationTemplateCRUD

from ginkgo.data.models.model_notification_template import MNotificationTemplate
from ginkgo.libs import GLOG


class TemplateEngine:
    """
    模板渲染引擎

    提供 Jinja2 模板渲染功能，支持：
    - 直接字符串模板渲染
    - 从 MongoDB 加载模板并渲染
    - 变量验证和错误处理
    """

    def __init__(self, template_crud: Optional["NotificationTemplateCRUD"] = None):
        """
        初始化模板引擎

        Args:
            template_crud: 通知模板 CRUD 实例（可选）
        """
        self.template_crud = template_crud

        # 创建 Jinja2 环境
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,  # 不自动转义，允许 Markdown 和 HTML
            trim_blocks=True,
            lstrip_blocks=True
        )

    def render(
        self,
        template_content: str,
        context: Dict[str, Any],
        strict: bool = False
    ) -> str:
        """
        渲染模板内容

        Args:
            template_content: 模板内容（包含 Jinja2 语法）
            context: 变量上下文
            strict: 是否严格模式（未定义变量会报错）

        Returns:
            str: 渲染后的内容

        Raises:
            ValueError: 模板语法错误或渲染失败
        """
        try:
            # 创建环境（严格模式下使用 StrictUndefined）
            if strict:
                env = Environment(
                    loader=BaseLoader(),
                    autoescape=False,
                    trim_blocks=True,
                    lstrip_blocks=True,
                    undefined=StrictUndefined
                )
            else:
                env = self.env

            # 创建模板对象
            template = env.from_string(template_content)

            # 渲染
            result = template.render(**context)

            return result

        except TemplateSyntaxError as e:
            GLOG.ERROR(f"Template syntax error: {e}")
            raise ValueError(f"Template syntax error at line {e.lineno}: {e.message}")

        except (UndefinedError, TemplateError) as e:
            GLOG.ERROR(f"Template rendering error: {e}")
            raise ValueError(f"Template rendering error: {str(e)}")

        except Exception as e:
            GLOG.ERROR(f"Unexpected error rendering template: {e}")
            raise ValueError(f"Template rendering failed: {str(e)}")

    def render_from_template_id(
        self,
        template_id: str,
        context: Dict[str, Any],
        strict: bool = False
    ) -> str:
        """
        从 MongoDB 加载模板并渲染

        Args:
            template_id: 模板唯一标识符
            context: 变量上下文
            strict: 是否严格模式

        Returns:
            str: 渲染后的内容

        Raises:
            ValueError: 模板不存在或渲染失败
        """
        if self.template_crud is None:
            raise ValueError("template_crud is not initialized")

        # 从数据库加载模板
        template = self.template_crud.get_by_template_id(template_id)

        if template is None:
            raise ValueError(f"Template not found: {template_id}")

        if not template.is_active:
            raise ValueError(f"Template is not active: {template_id}")

        # 渲染模板
        return self.render(
            template_content=template.content,
            context=context,
            strict=strict
        )

    def validate_template(self, template_content: str) -> Dict[str, Any]:
        """
        验证模板语法

        Args:
            template_content: 模板内容

        Returns:
            Dict: 验证结果
            {
                "valid": bool,
                "error": Optional[str],
                "variables": List[str]  # 提取的变量列表
            }
        """
        try:
            # 尝试解析模板
            template = self.env.from_string(template_content)

            # 提取变量
            variables = self._extract_variables(template_content)

            return {
                "valid": True,
                "error": None,
                "variables": variables
            }

        except TemplateSyntaxError as e:
            return {
                "valid": False,
                "error": f"Syntax error at line {e.lineno}: {e.message}",
                "variables": []
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "variables": []
            }

    def _extract_variables(self, template_content: str) -> List[str]:
        """
        从模板内容中提取变量名

        Args:
            template_content: 模板内容

        Returns:
            List[str]: 变量名列表（去重）
        """
        import re

        # 提取 {{ variable }} 格式的变量
        pattern = r'\{\{\s*(\w+)\s*\}\}'
        variables = re.findall(pattern, template_content)

        # 去重并返回
        return list(set(variables))

    def render_with_defaults(
        self,
        template_content: str,
        context: Dict[str, Any],
        default_values: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        使用默认值渲染模板

        对于 context 中缺少的变量，使用 default_values 中的值。

        Args:
            template_content: 模板内容
            context: 变量上下文
            default_values: 默认值字典

        Returns:
            str: 渲染后的内容
        """
        if default_values is None:
            default_values = {}

        # 合并上下文和默认值
        merged_context = {**default_values, **context}

        return self.render(template_content, merged_context)

    def preview_template(
        self,
        template_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        预览模板（用于测试）

        Args:
            template_id: 模板唯一标识符
            context: 变量上下文（可选，如果不提供则使用示例值）

        Returns:
            Dict: 预览结果
            {
                "template_id": str,
                "template_name": str,
                "template_type": str,
                "content": str,  # 原始内容
                "rendered": str,  # 渲染后内容
                "variables": List[str],  # 所需变量
                "context_used": Dict[str, Any]  # 实际使用的上下文
            }
        """
        if self.template_crud is None:
            raise ValueError("template_crud is not initialized")

        # 加载模板
        template = self.template_crud.get_by_template_id(template_id)

        if template is None:
            raise ValueError(f"Template not found: {template_id}")

        # 提取变量
        variables = template.get_required_variables()

        # 如果没有提供上下文，使用示例值
        if context is None:
            context = {var: f"<{var}>" for var in variables}

        # 渲染模板
        rendered = self.render(template.content, context)

        return {
            "template_id": template.template_id,
            "template_name": template.template_name,
            "template_type": template.get_template_type_enum().name,
            "content": template.content,
            "rendered": rendered,
            "variables": variables,
            "context_used": context
        }

    def batch_render(
        self,
        template_content: str,
        contexts: List[Dict[str, Any]]
    ) -> List[str]:
        """
        批量渲染模板

        Args:
            template_content: 模板内容
            contexts: 上下文列表

        Returns:
            List[str]: 渲染结果列表
        """
        results = []
        for context in contexts:
            try:
                rendered = self.render(template_content, context)
                results.append(rendered)
            except Exception as e:
                GLOG.ERROR(f"Error in batch render: {e}")
                results.append(f"[ERROR: {str(e)}]")

        return results
