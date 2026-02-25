# Upstream: FileService (文件管理业务服务)、PortfolioService (文件绑定管理)
# Downstream: BaseCRUD (继承提供标准CRUD能力和装饰器@time_logger/@retry/@cache)、MFile (MySQL文件模型)、FileInfo实体(业务文件信息实体)、FILE_TYPES (文件类型枚举STRATEGY/ANALYZER/SELECTOR/SIZER/RISKMANAGER/DATA/OTHER)
# Role: FileCRUD文件CRUD操作继承BaseCRUD提供文件管理和业务查询方法支持交易系统功能和组件集成提供完整业务支持






from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models import MFile
from ginkgo.enums import SOURCE_TYPES, FILE_TYPES
from ginkgo.libs import GLOG
from ginkgo.trading.core.file_info import FileInfo
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class FileCRUD(BaseCRUD[MFile]):
    """
    File CRUD operations.
    """

    # 类级别声明，支持自动注册

    _model_class = MFile

    def __init__(self):
        super().__init__(MFile)

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """
        🎯 Define field-to-enum mappings for FileCRUD.

        Returns:
            Dictionary mapping field names to enum classes
        """
        return {
            'type': FILE_TYPES,
        }

    def _get_field_config(self) -> dict:
        """
        定义 File 数据的字段配置 - 必填字段验证

        Returns:
            dict: 字段配置字典
        """
        return {
            # 文件类型 - 枚举值
            'type': {
                'type': 'enum',
                'choices': [f for f in FILE_TYPES]
            },

            # 文件名 - 非空字符串，最大40字符（与模型String(40)一致）
            'name': {
                'type': 'string',
                'min': 1,
                'max': 40
            },

            # 文件数据 - 二进制数据
            'data': {
                'type': 'bytes'
            },

            # version, parent_uuid, is_latest 字段有默认值，不需要验证为必填
            # source字段移除验证配置，使用模型默认值 SOURCE_TYPES.OTHER
        }

    def _create_from_params(self, **kwargs) -> MFile:
        """
        Hook method: Create MFile from parameters.
        """
        # Convert string file_type to enum if needed
        file_type = kwargs.get("file_type", kwargs.get("type", FILE_TYPES.OTHER))
        if isinstance(file_type, str):
            # Map common string types to enum values
            type_mapping = {
                "TEXT": FILE_TYPES.OTHER,
                "PYTHON": FILE_TYPES.STRATEGY,
                "JSON": FILE_TYPES.OTHER,
                "ANALYZER": FILE_TYPES.ANALYZER,
                "INDEX": FILE_TYPES.INDEX,
                "STRATEGY": FILE_TYPES.STRATEGY,
                "ENGINE": FILE_TYPES.ENGINE,
                "HANDLER": FILE_TYPES.HANDLER,
            }
            file_type = type_mapping.get(file_type.upper(), FILE_TYPES.OTHER)
        
        return MFile(
            type=FILE_TYPES.validate_input(file_type),
            name=kwargs.get("filename", kwargs.get("name", "ginkgo_file")),
            data=kwargs.get("data", b""),
            source=SOURCE_TYPES.validate_input(kwargs.get("source", SOURCE_TYPES.SIM)),
            desc=kwargs.get("desc"),  # 添加desc参数
        )

    def _convert_input_item(self, item: Any) -> Optional[MFile]:
        """
        Hook method: Convert file objects to MFile.
        """
        if isinstance(item, FileInfo):
            # Convert string type to enum if needed
            file_type = item.type
            if isinstance(file_type, str):
                type_mapping = {
                    "TEXT": FILE_TYPES.OTHER,
                    "PYTHON": FILE_TYPES.STRATEGY,
                    "JSON": FILE_TYPES.OTHER,
                    "ANALYZER": FILE_TYPES.ANALYZER,
                    "INDEX": FILE_TYPES.INDEX,
                    "STRATEGY": FILE_TYPES.STRATEGY,
                    "ENGINE": FILE_TYPES.ENGINE,
                    "HANDLER": FILE_TYPES.HANDLER,
                }
                file_type = type_mapping.get(file_type.upper(), FILE_TYPES.OTHER)
            
            return MFile(
                type=FILE_TYPES.validate_input(file_type),
                name=item.name,
                data=getattr(item, 'data', b""),
                source=SOURCE_TYPES.validate_input(item.source),
            )
        return None


    def _convert_models_to_business_objects(self, models: List) -> List:
        """
        🎯 Convert models to business objects.

        Args:
            models: List of models with enum fields already fixed

        Returns:
            List of models (business object doesn't exist yet)
        """
        # For now, return models as-is since business object doesn't exist yet
        return models

    def _convert_output_items(self, items: List, output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert objects for business layer.
        """
        return items

    def _convert_output_items(self, items: List[MFile], output_type: str = "model") -> List[Any]:
        """
        Hook method: Convert MFile objects for business layer.
        """
        if output_type == "file_info":
            return [FileInfo(item) for item in items]
        return items

    # Business Helper Methods
    def find_by_file_id(self, file_id: str, as_dataframe: bool = False) -> Union[List[MFile], pd.DataFrame]:
        """
        Business helper: Find file by ID.
        """
        return self.find(filters={"uuid": file_id}, page_size=1,
                        as_dataframe=as_dataframe)

    def find_by_filename(self, filename: str, as_dataframe: bool = False) -> Union[List[MFile], pd.DataFrame]:
        """
        Business helper: Find files by filename pattern.
        """
        return self.find(filters={"name__like": filename}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe)

    def find_by_type(self, file_type: str, as_dataframe: bool = False) -> Union[List[MFile], pd.DataFrame]:
        """
        Business helper: Find files by type.
        """
        # Convert string type to enum if needed
        if isinstance(file_type, str):
            type_mapping = {
                "TEXT": FILE_TYPES.OTHER,
                "PYTHON": FILE_TYPES.STRATEGY,
                "JSON": FILE_TYPES.OTHER,
                "ANALYZER": FILE_TYPES.ANALYZER,
                "INDEX": FILE_TYPES.INDEX,
                "STRATEGY": FILE_TYPES.STRATEGY,
                "ENGINE": FILE_TYPES.ENGINE,
                "HANDLER": FILE_TYPES.HANDLER,
            }
            file_type = type_mapping.get(file_type.upper(), FILE_TYPES.OTHER)
        
        return self.find(filters={"type": file_type}, order_by="update_at", desc_order=True,
                        as_dataframe=as_dataframe)

    def find_by_size_range(self, min_size: int, max_size: int,
                          as_dataframe: bool = False) -> Union[List[MFile], pd.DataFrame]:
        """
        Business helper: Find files by size range (not supported by MFile model).
        """
        GLOG.DEBUG("File size range search not supported by MFile model")
        return self.find(filters={}, as_dataframe=as_dataframe)

    def get_total_size_by_type(self, file_type: str) -> int:
        """
        Business helper: Get total size of files by type (not supported by MFile model).
        """
        GLOG.DEBUG("File size calculation not supported by MFile model")
        files = self.find_by_type(file_type, as_dataframe=False)
        return len(files)

    def delete_by_file_id(self, file_id: str) -> None:
        """
        Business helper: Delete file by ID.
        """
        GLOG.DEBUG(f"删除文件记录: {file_id}")
        return self.remove({"uuid": file_id})

    # 版本管理方法
    def get_latest_by_name(self, name: str, file_type: FILE_TYPES = None) -> Optional[MFile]:
        """
        获取指定名称的最新版本文件

        Args:
            name: 文件名称
            file_type: 文件类型（可选）

        Returns:
            最新版本的MFile对象，如果不存在则返回None
        """
        filters = {"name": name, "is_latest": True}
        if file_type is not None:
            filters["type"] = file_type
        result = self.find(filters=filters, page_size=1)
        return result[0] if result else None

    def get_version_history(self, name: str, file_type: FILE_TYPES = None) -> List[MFile]:
        """
        获取指定文件的所有版本

        Args:
            name: 文件名称
            file_type: 文件类型（可选）

        Returns:
            按创建时间排序的版本列表
        """
        filters = {"name": name}
        if file_type is not None:
            filters["type"] = file_type
        return self.find(filters=filters, order_by="create_at", desc_order=False)

    def create_new_version(self, file_uuid: str, new_data: bytes = None, new_name: str = None) -> MFile:
        """
        基于现有文件创建新版本

        Args:
            file_uuid: 当前文件的UUID（可以是任意版本）
            new_data: 新的代码内容（可选）
            new_name: 新的名称（可选）

        Returns:
            新创建的MFile对象
        """
        old_files = self.find(filters={"uuid": file_uuid}, page_size=1)
        if not old_files:
            raise ValueError(f"File not found: {file_uuid}")
        old_file = old_files[0]

        # 获取该文件名的最新版本，用于计算新版本号
        latest_file = self.get_latest_by_name(old_file.name, old_file.type)
        if not latest_file:
            raise ValueError(f"No latest version found for: {old_file.name}")

        # 将所有版本标记为非最新
        self.modify(filters={"name": old_file.name, "type": old_file.type}, updates={"is_latest": False})

        # 从最新版本号递增
        new_version = self._increment_version(latest_file.version)

        # 创建新版本
        return MFile(
            name=new_name or old_file.name,
            type=old_file.type,
            version=new_version,
            parent_uuid=latest_file.uuid,  # 指向之前的最新版本
            is_latest=True,
            data=new_data if new_data is not None else old_file.data,
            source=old_file.source,
            desc=old_file.desc,
        )

    def _increment_version(self, version: str) -> str:
        """
        版本号递增: 1.0.0 -> 1.0.1 -> 1.0.2...

        Args:
            version: 当前版本号

        Returns:
            递增后的版本号
        """
        try:
            parts = version.split('.')
            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                return f"{major}.{minor}.{patch + 1}"
        except (ValueError, AttributeError):
            pass
        return "1.0.1"  # 默认新版本
