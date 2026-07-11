# Upstream: CLI Commands, API Controllers, PortfolioGraphEditor (前端)
# Downstream: PortfolioFileMappingCRUD (MySQL), ParamService (MySQL), GinkgoMongo (MongoDB), FileService
# Role: PortfolioMappingService 投资组合映射服务 - MongoDB图结构与MySQL Mapping+Param双向同步


from typing import List, Optional, Dict, Any
import json
import uuid
from datetime import datetime

from ginkgo.libs import GLOG, retry
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.crud.portfolio_file_mapping_crud import PortfolioFileMappingCRUD
from ginkgo.data.services.param_service import ParamService
from ginkgo.data.services.file_service import FileService
from ginkgo.data.models import MPortfolioFileMapping
from ginkgo.enums import FILE_TYPES, SOURCE_TYPES
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo


class PortfolioMappingService(BaseService):
    """
    投资组合映射服务

    实现 MongoDB 图结构与 MySQL Mapping + Param 的双向同步：
    1. 图编辑器创建 → 保存图到 MongoDB + 同步文件到 MySQL Mapping + 同步参数到 MParam
    2. 添加文件到投资组合 → 创建 MySQL Mapping + 自动生成图结构 + 同步默认参数到 MParam

    数据流：
    ┌─────────────────────────────────────────────────────────────┐
    │                    前端图编辑器 / CLI                        │
    └─────────────────────────────────────────────────────────────┘
                              ↓
    ┌─────────────────────────┴─────────────────────────────────┐
    │              PortfolioMappingService                       │
    │  ├── MongoDB: 完整图数据 (nodes + edges + viewport)        │
    │  └── MySQL:     ┌─────────────────────────────────────┐   │
    │                │  MPortfolioFileMapping  (文件映射)    │   │
    │                │  MParam                 (节点参数)    │   │
    │                └─────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘

    Attributes:
        _mapping_crud: PortfolioFileMappingCRUD 实例
        _param_service: ParamService 实例
        _mongo_driver: GinkgoMongo 驱动实例
        _file_service: FileService 实例
    """

    def __init__(
        self,
        mapping_crud: PortfolioFileMappingCRUD,
        param_service: ParamService,
        mongo_driver: GinkgoMongo,
        file_service: FileService,
    ):
        """
        初始化服务

        Args:
            mapping_crud: PortfolioFileMappingCRUD 实例
            param_service: ParamService 实例
            mongo_driver: GinkgoMongo 驱动实例
            file_service: FileService 实例
        """
        super().__init__(
            mapping_crud=mapping_crud,
            param_service=param_service,
            mongo_driver=mongo_driver,
            file_service=file_service,
        )

    # ==================== 方向 1: 图编辑器 → Mapping + Param ====================

    @retry
    def create_from_graph_editor(
        self,
        portfolio_uuid: str,
        graph_data: Dict[str, Any],
        name: str,
        sync_mysql: bool = True,
    ) -> ServiceResult:
        """
        从图编辑器创建配置

        流程：
        1. 保存完整图数据到 MongoDB
        2. 解析 nodes 中的 file_id，同步到 MySQL Mapping
        3. 解析 nodes 中的 params，同步到 MySQL MParam

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 图数据 {"nodes": [...], "edges": [...], "viewport": {...}}
            name: 配置名称
            sync_mysql: 是否回写 MySQL Mapping/MParam。图编辑器场景为 True（以图为权威，
                删除图外孤立映射）；deploy 克隆场景传 False —— MySQL 映射已由 deploy
                源组合权威复制，此处仅需搬运 Mongo 图供 UI，绝不能按（可能不完整的）
                源图删除已建的 strategy/sizer 映射。#6279

        Returns:
            ServiceResult: 包含 mongo_id、mappings_count、params_count

        Examples:
            >>> result = service.create_from_graph_editor(
            ...     portfolio_uuid="portfolio123",
            ...     graph_data={
            ...         "nodes": [
            ...             {
            ...                 "id": "node-1",
            ...                 "type": "STRATEGY",
            ...                 "data": {
            ...                     "file_id": "file_strategy_1",
            ...                     "params": {"period": [5, 20], "fast_period": 3}
            ...                 }
            ...             }
            ...         ],
            ...         "edges": []
            ...     },
            ...     name="双均线策略"
            ... )
        """
        try:
            # 1. 保存到 MongoDB（图文档本体，UI 可视化用）
            mongo_id = self._save_graph_to_mongo(
                portfolio_uuid=portfolio_uuid,
                graph_data=graph_data,
                name=name,
                source="GRAPH_EDITOR"
            )

            # 2. MySQL 同步（图编辑器权威；deploy 克隆传 False 跳过以保 step5 已建映射）
            file_mappings: list = []
            node_params: list = []
            if sync_mysql:
                file_mappings = self._extract_files_from_graph(graph_data)
                node_params = self._extract_params_from_graph(graph_data)

                # 下游 MySQL sync 失败时补偿删 Mongo 孤儿（#5559）：
                # Mongo 已在步骤1写入，若 MySQL sync 抛异常，反向删除已写的 Mongo 文档，
                # 保持跨库一致性。raise 让外层 @retry/except 决定重试或返错。
                try:
                    # 同步到 MySQL Mapping
                    self._sync_mappings_from_files(
                        portfolio_uuid=portfolio_uuid,
                        file_mappings=file_mappings
                    )

                    # 同步到 MySQL MParam
                    self._sync_params_from_nodes(
                        portfolio_uuid=portfolio_uuid,
                        node_params=node_params
                    )
                except Exception:
                    self._delete_graph_from_mongo(mongo_id)
                    raise

            GLOG.INFO(f"从图编辑器创建配置: {portfolio_uuid} ({mongo_id})")
            GLOG.DEBUG(f"  同步了 {len(file_mappings)} 个文件映射")
            GLOG.DEBUG(f"  同步了 {len(node_params)} 个节点参数")

            return ServiceResult.success(data={
                "mongo_id": mongo_id,
                "mappings_count": len(file_mappings),
                "params_count": len(node_params),
                "portfolio_uuid": portfolio_uuid,
            })

        except Exception as e:
            GLOG.ERROR(f"从图编辑器创建配置失败: {e}")
            return ServiceResult.error(f"从图编辑器创建配置失败: {str(e)}")

    @retry
    def update_from_graph_editor(
        self,
        portfolio_uuid: str,
        graph_data: Dict[str, Any],
        name: Optional[str] = None,
    ) -> ServiceResult:
        """
        从图编辑器更新配置

        流程：
        1. 更新 MongoDB 图数据
        2. 同步文件映射到 MySQL
        3. 同步节点参数到 MySQL MParam

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 新的图数据
            name: 新的配置名称（可选）

        Returns:
            ServiceResult
        """
        try:
            previous_doc = self._snapshot_graph_from_mongo(
                portfolio_uuid=portfolio_uuid,
                source="GRAPH_EDITOR"
            )

            # 1. 提取图中的文件映射和参数
            file_mappings = self._extract_files_from_graph(graph_data)
            node_params = self._extract_params_from_graph(graph_data)

            # 2. 更新 MongoDB
            mongo_id = self._update_graph_in_mongo(
                portfolio_uuid=portfolio_uuid,
                graph_data=graph_data,
                name=name,
                source="GRAPH_EDITOR"
            )

            try:
                # 3. 同步到 MySQL Mapping
                self._sync_mappings_from_files(
                    portfolio_uuid=portfolio_uuid,
                    file_mappings=file_mappings
                )

                # 4. 同步到 MySQL MParam
                self._sync_params_from_nodes(
                    portfolio_uuid=portfolio_uuid,
                    node_params=node_params
                )
            except Exception:
                if previous_doc:
                    self._restore_graph_in_mongo(previous_doc)
                else:
                    self._delete_graph_from_mongo(mongo_id)
                raise

            GLOG.INFO(f"从图编辑器更新配置: {portfolio_uuid}")

            return ServiceResult.success(data={
                "mongo_id": mongo_id,
                "mappings_count": len(file_mappings),
                "params_count": len(node_params),
            })

        except Exception as e:
            GLOG.ERROR(f"从图编辑器更新配置失败: {e}")
            return ServiceResult.error(f"从图编辑器更新配置失败: {str(e)}")

    # ==================== 方向 2: Mapping → 图结构 + Param ====================

    @retry
    def add_file(
        self,
        portfolio_uuid: str,
        file_id: str,
        file_type: FILE_TYPES,
        name: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> ServiceResult:
        """
        添加文件到投资组合

        流程：
        1. 创建 MySQL Mapping
        2. 同步默认参数到 MySQL MParam
        3. 自动在 MongoDB 图中生成对应节点

        Args:
            portfolio_uuid: 投资组合 UUID
            file_id: 文件 UUID
            file_type: 文件类型
            name: 映射名称（可选）
            params: 默认参数（可选）

        Returns:
            ServiceResult
        """
        try:
            # #5776: 校验 file_id 实际类型(MFile.type)与请求绑定的 file_type 一致，
            # 防止策略组件被错误绑定到 selector/sizer/risk 等角色。
            file_result = self._file_service.get_by_uuid(file_id)
            if not file_result.success:
                return ServiceResult.error(f"File not found: {file_id}")
            file_obj = file_result.data.get("file") if file_result.data else None
            if file_obj is None:
                return ServiceResult.error(f"File not found: {file_id}")
            actual_type = getattr(file_obj, "type", None)
            expected_value = file_type.value if hasattr(file_type, "value") else file_type
            if actual_type is None or int(actual_type) != int(expected_value):
                actual_name = (
                    FILE_TYPES(int(actual_type)).name
                    if actual_type is not None
                    else "UNKNOWN"
                )
                return ServiceResult.error(
                    f"File type mismatch: file {file_id} is {actual_name}, "
                    f"cannot bind as {file_type.name}"
                )

            # #5808: 去重 — 同 (portfolio_uuid, file_id) 已绑定时幂等返回，不创建重复 mapping
            existing_mappings = self._mapping_crud.find_by_portfolio(portfolio_uuid)
            for _existing in existing_mappings:
                if getattr(_existing, "file_id", None) == file_id:
                    GLOG.INFO(f"文件已绑定，幂等返回: {portfolio_uuid} -> {file_id}")
                    return ServiceResult.success(data={
                        "file_id": file_id,
                        "mapping_id": _existing.uuid,
                        "already_existed": True,
                    })

            # 1. 创建 MySQL Mapping
            mapping = MPortfolioFileMapping(
                portfolio_id=portfolio_uuid,
                file_id=file_id,
                name=name or f"auto_binding_{file_type.name}",
                type=file_type,
                source=SOURCE_TYPES.SIM
            )
            mapping_obj = self._mapping_crud.add(mapping)
            mapping_uuid = mapping_obj.uuid

            # 2. 同步参数到 MParam（使用 mapping_uuid）
            if params:
                self._sync_params_for_mapping(
                    mapping_uuid=mapping_uuid,
                    params=params
                )

            GLOG.INFO(f"添加文件映射: {portfolio_uuid} -> {file_id}")

            # 3. 同步到 MongoDB 图结构（非致命）
            try:
                self._sync_graph_from_mappings(portfolio_uuid)
            except Exception as e:
                GLOG.WARN(f"图结构同步失败(非致命): {e}")

            return ServiceResult.success(data={"file_id": file_id, "mapping_id": mapping_uuid})

        except Exception as e:
            GLOG.ERROR(f"添加文件失败: {e}")
            return ServiceResult.error(f"添加文件失败: {str(e)}")

    @retry
    def remove_file(
        self,
        portfolio_uuid: str,
        file_id: str,
    ) -> ServiceResult:
        """
        从投资组合移除文件

        流程：
        1. 删除 MySQL Mapping
        2. 删除对应的 MParam
        3. 从 MongoDB 图中移除对应节点

        Args:
            portfolio_uuid: 投资组合 UUID
            file_id: 文件 UUID

        Returns:
            ServiceResult
        """
        try:
            # 1. 获取要删除的 mapping
            mappings = self._mapping_crud.find(
                filters={"portfolio_id": portfolio_uuid, "file_id": file_id}
            )
            param_snapshots = {
                mapping.uuid: list(self._param_service.find_by_mapping_id(mapping.uuid))
                for mapping in mappings
            }

            try:
                # 2. 删除对应的参数
                for mapping in mappings:
                    self._param_service.remove_by_mapping(mapping.uuid)

                # 3. 删除 MySQL Mapping
                self._mapping_crud.delete_mapping(portfolio_uuid, file_id)

                GLOG.INFO(f"移除文件映射: {portfolio_uuid} -> {file_id}")

                # 4. 同步更新 MongoDB 图结构
                self._sync_graph_from_mappings(portfolio_uuid)
            except Exception:
                self._restore_removed_file_mappings(mappings, param_snapshots)
                raise

            return ServiceResult.success(data={"file_id": file_id})

        except Exception as e:
            GLOG.ERROR(f"移除文件失败: {e}")
            return ServiceResult.error(f"移除文件失败: {str(e)}")

    @retry
    def delete_graph(
        self,
        portfolio_uuid: str,
    ) -> ServiceResult:
        """
        删除投资组合的图配置（保留 portfolio 本身）

        流程：
        1. 删除该 portfolio 全部 Mapping 及其 MParam
        2. 删除 MongoDB 中的图文档

        与 remove_file 的删除范式一致（find_by_portfolio → remove_by_mapping
        → delete_mapping），只是范围从单个 file 扩展到全部。

        Args:
            portfolio_uuid: 投资组合 UUID（即 graph_uuid）

        Returns:
            ServiceResult: 包含 portfolio_uuid 与已删除 mapping 数
        """
        try:
            # 1. 删除全部 mapping 及其参数
            mappings = self._mapping_crud.find_by_portfolio(portfolio_uuid)
            for mapping in mappings:
                self._param_service.remove_by_mapping(mapping.uuid)
                self._mapping_crud.delete_mapping(portfolio_uuid, mapping.file_id)

            # 2. 删除 MongoDB 图文档
            collection = self._mongo_driver.get_collection("portfolio_graph_data")
            collection.delete_many({"portfolio_uuid": portfolio_uuid})

            GLOG.INFO(f"删除图配置: {portfolio_uuid} (mappings={len(mappings)})")

            return ServiceResult.success(data={
                "portfolio_uuid": portfolio_uuid,
                "deleted_mappings": len(mappings),
            })

        except Exception as e:
            GLOG.ERROR(f"删除图配置失败: {e}")
            return ServiceResult.error(f"删除图配置失败: {str(e)}")

    @retry
    def duplicate_graph(
        self,
        source_uuid: str,
        name: Optional[str] = None,
    ) -> ServiceResult:
        """
        复制图配置到新的 portfolio_uuid

        流程：
        1. 读取源图 (get_portfolio_graph)
        2. 生成新 portfolio_uuid
        3. 以新 uuid 调 create_from_graph_editor 写入图 + mapping + param

        注：仅复制图配置层（mongo + mapping + param），不创建 Portfolio 实体
        （create_from_graph_editor 本身不要求 Portfolio 行存在，行为一致）。

        Args:
            source_uuid: 源投资组合 UUID（即源 graph_uuid）
            name: 副本名称，缺省时自动生成

        Returns:
            ServiceResult: 包含 source_uuid / new_portfolio_uuid / mongo_id
        """
        try:
            # 1. 读源图
            read_result = self.get_portfolio_graph(source_uuid)
            if not read_result.is_success():
                return ServiceResult.error(
                    f"源图不存在: {source_uuid} ({read_result.error})"
                )
            graph_data = read_result.data.get("graph_data", {})

            # 2. 生成新 uuid 并创建副本
            new_uuid = uuid.uuid4().hex
            new_name = name or f"Copy of {source_uuid[:8]}"

            create_result = self.create_from_graph_editor(
                portfolio_uuid=new_uuid,
                graph_data=graph_data,
                name=new_name,
            )
            if not create_result.is_success():
                return ServiceResult.error(
                    create_result.error or "复制图配置失败"
                )

            GLOG.INFO(f"复制图配置: {source_uuid} -> {new_uuid}")

            return ServiceResult.success(data={
                "source_uuid": source_uuid,
                "new_portfolio_uuid": new_uuid,
                "mongo_id": create_result.data.get("mongo_id"),
                "mappings_count": create_result.data.get("mappings_count", 0),
            })

        except Exception as e:
            GLOG.ERROR(f"复制图配置失败: {e}")
            return ServiceResult.error(f"复制图配置失败: {str(e)}")

    # ==================== 查询方法 ====================

    def get_portfolio_graph(
        self,
        portfolio_uuid: str,
    ) -> ServiceResult:
        """
        获取投资组合的图数据

        优先返回 MongoDB 中的图数据，
        如果不存在则从 MySQL Mapping 自动生成

        Args:
            portfolio_uuid: 投资组合 UUID

        Returns:
            ServiceResult: 包含 graph_data
        """
        try:
            collection = self._mongo_driver.get_collection("portfolio_graph_data")

            # 查找现有图数据，按应用层优先级选图：
            #   #5742 — 原先 find_one(sort by source asc) 让 AUTO_GENERATED 空图
            #   抢占 GRAPH_EDITOR 非空图（"A" < "G"）。改为取全部后按
            #   「非空优先 + GRAPH_EDITOR 优先」选最佳文档。
            all_docs = list(collection.find({"portfolio_uuid": portfolio_uuid}))
            graph_doc = self._select_best_graph_doc(all_docs)

            if graph_doc:
                return ServiceResult.success(data={
                    "graph_data": graph_doc["graph_data"],
                    "metadata": graph_doc.get("metadata", {}),
                    "source": "MONGODB",
                    "mongo_id": graph_doc["_id"],
                })

            # 不存在，从 Mapping 自动生成
            GLOG.INFO(f"图数据不存在，从 Mapping 自动生成: {portfolio_uuid}")
            self._sync_graph_from_mappings(portfolio_uuid)

            # 再次查询
            all_docs = list(collection.find({"portfolio_uuid": portfolio_uuid}))
            graph_doc = self._select_best_graph_doc(all_docs)
            return ServiceResult.success(data={
                "graph_data": graph_doc["graph_data"] if graph_doc else {"nodes": [], "edges": []},
                "metadata": graph_doc.get("metadata", {}) if graph_doc else {},
                "source": "AUTO_GENERATED",
            })

        except Exception as e:
            GLOG.ERROR(f"获取图数据失败: {e}")
            return ServiceResult.error(f"获取图数据失败: {str(e)}")

    def _select_best_graph_doc(self, docs):
        """
        按优先级选最佳图文档 (#5742)

        规则：
          1. 非空图（有 nodes）优先于空图 —— 空图不得抢占非空图
          2. 非空图中 GRAPH_EDITOR（用户手动编辑）优先于 AUTO_GENERATED
          3. 全部为空图时返回第一个（保持旧行为兼容）

        Args:
            docs: 同 portfolio 的全部图文档列表

        Returns:
            最佳图文档，或 None（列表为空）
        """
        if not docs:
            return None

        def _has_nodes(doc):
            return bool(doc.get("graph_data", {}).get("nodes"))

        non_empty = [d for d in docs if _has_nodes(d)]
        if non_empty:
            editor = next(
                (d for d in non_empty
                 if d.get("metadata", {}).get("source") == "GRAPH_EDITOR"),
                None,
            )
            return editor or non_empty[0]

        # 全部为空图，保持旧行为返回第一个
        return docs[0]

    def get_portfolio_mappings(
        self,
        portfolio_uuid: str,
        include_params: bool = False,
    ) -> ServiceResult:
        """
        获取投资组合的文件映射

        Args:
            portfolio_uuid: 投资组合 UUID
            include_params: 是否包含参数

        Returns:
            ServiceResult: 包含映射列表
        """
        try:
            mappings = self._mapping_crud.find_by_portfolio(portfolio_uuid)

            result = []
            for m in mappings:
                mapping_data = {
                    "uuid": m.uuid,
                    "portfolio_id": m.portfolio_id,
                    "file_id": m.file_id,
                    "name": m.name,
                    "type": m.type,
                    "source": m.source,
                }

                # 如果需要包含参数
                if include_params:
                    params = self._param_service.find_by_mapping_id(m.uuid)
                    # 将参数列表转换为字典（优先使用存储的参数名）
                    params_dict = {}
                    for p in params:
                        # 尝试解析 JSON 值
                        try:
                            value = json.loads(p.value) if p.value else {}
                        except Exception as e:
                            GLOG.ERROR(f"解析参数JSON值失败: {e}")
                            value = p.value
                        params_dict[f"param_{p.index}"] = value

                    mapping_data["params"] = params_dict

                result.append(mapping_data)

            return ServiceResult.success(data=result)

        except Exception as e:
            GLOG.ERROR(f"获取映射失败: {e}")
            return ServiceResult.error(f"获取映射失败: {str(e)}")

    def get_mapping_params(
        self,
        mapping_uuid: str,
    ) -> ServiceResult:
        """
        获取映射的参数

        Args:
            mapping_uuid: Mapping UUID

        Returns:
            ServiceResult: 包含参数字典
        """
        try:
            params = self._param_service.find_by_mapping_id(mapping_uuid)

            # 转换为字典
            params_dict = {}
            for p in params:
                try:
                    value = json.loads(p.value) if p.value else {}
                except Exception as e:
                    GLOG.ERROR(f"解析参数JSON值失败: {e}")
                    value = p.value
                params_dict[f"param_{p.index}"] = value

            return ServiceResult.success(data=params_dict)

        except Exception as e:
            GLOG.ERROR(f"获取参数失败: {e}")
            return ServiceResult.error(f"获取参数失败: {str(e)}")

    # ==================== 私有辅助方法 ====================

    def _extract_files_from_graph(
        self,
        graph_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从图数据中提取文件映射

        Args:
            graph_data: 图数据

        Returns:
            文件映射列表
        """
        files = []
        for node in graph_data.get("nodes", []):
            file_id = node.get("data", {}).get("file_id")
            if file_id:
                node_type = self._parse_node_type(node.get("type", ""))
                label = node.get("data", {}).get("label", f"auto_{node_type.name}")
                files.append({
                    "file_id": file_id,
                    "type": node_type,
                    "name": label
                })
        return files

    def _extract_params_from_graph(
        self,
        graph_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        从图数据中提取节点参数

        Args:
            graph_data: 图数据

        Returns:
            节点参数列表 [{"file_id": "...", "params": {...}}, ...]
        """
        node_params = []
        for node in graph_data.get("nodes", []):
            file_id = node.get("data", {}).get("file_id")
            params = node.get("data", {}).get("params")

            if file_id and params:
                node_params.append({
                    "file_id": file_id,
                    "params": params
                })

        return node_params

    def _save_graph_to_mongo(
        self,
        portfolio_uuid: str,
        graph_data: Dict[str, Any],
        name: str,
        source: str = "GRAPH_EDITOR",
    ) -> str:
        """
        保存图数据到 MongoDB

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 图数据
            name: 配置名称
            source: 数据来源

        Returns:
            MongoDB 文档 ID
        """
        collection = self._mongo_driver.get_collection("portfolio_graph_data")

        doc_id = uuid.uuid4().hex

        document = {
            "_id": doc_id,
            "portfolio_uuid": portfolio_uuid,
            "name": name,
            "graph_data": graph_data,
            "metadata": {
                "source": source,
                "auto_generated": False,
                "synced_at": datetime.now()
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        collection.insert_one(document)
        return doc_id

    def _delete_graph_from_mongo(self, doc_id: str) -> bool:
        """从 MongoDB 删除图数据文档（补偿原语，#5559）

        用于跨库写失败时反向补偿：create_from_graph_editor 写入 MongoDB 后，
        若 MySQL Mapping/MParam 同步失败，调用此方法删除已写的 Mongo 文档，
        避免孤儿。delete_one 对不存在的 _id 无害（幂等）。

        Args:
            doc_id: MongoDB 文档 ID（_save_graph_to_mongo 返回值）

        Returns:
            True 表示删除了一条文档；False 表示文档不存在或删除异常
        """
        try:
            collection = self._mongo_driver.get_collection("portfolio_graph_data")
            result = collection.delete_one({"_id": doc_id})
            return result.deleted_count > 0
        except Exception as e:
            GLOG.ERROR(f"补偿删除 MongoDB 图文档失败: {doc_id}, {e}")
            return False

    def _snapshot_graph_from_mongo(
        self,
        portfolio_uuid: str,
        source: str = "GRAPH_EDITOR",
    ) -> Optional[Dict[str, Any]]:
        """读取当前图文档快照，用于 update 失败补偿。"""
        collection = self._mongo_driver.get_collection("portfolio_graph_data")
        return collection.find_one({
            "portfolio_uuid": portfolio_uuid,
            "metadata.source": source
        })

    def _restore_graph_in_mongo(self, document: Dict[str, Any]) -> bool:
        """恢复 MongoDB 图文档快照（补偿原语，#5559）。"""
        try:
            if not document or "_id" not in document:
                return False
            collection = self._mongo_driver.get_collection("portfolio_graph_data")
            collection.replace_one({"_id": document["_id"]}, document, upsert=True)
            return True
        except Exception as e:
            GLOG.ERROR(f"补偿恢复 MongoDB 图文档失败: {e}")
            return False

    def _update_graph_in_mongo(
        self,
        portfolio_uuid: str,
        graph_data: Dict[str, Any],
        name: Optional[str] = None,
        source: str = "GRAPH_EDITOR",
    ) -> str:
        """
        更新 MongoDB 中的图数据

        Args:
            portfolio_uuid: 投资组合 UUID
            graph_data: 新的图数据
            name: 新的配置名称（可选）
            source: 数据来源

        Returns:
            MongoDB 文档 ID
        """
        collection = self._mongo_driver.get_collection("portfolio_graph_data")

        # 查找现有文档
        existing = collection.find_one({
            "portfolio_uuid": portfolio_uuid,
            "metadata.source": source
        })

        if existing:
            # 更新现有文档
            update_data = {
                "graph_data": graph_data,
                "updated_at": datetime.now(),
                "metadata.synced_at": datetime.now()
            }
            if name:
                update_data["name"] = name

            collection.update_one(
                {"_id": existing["_id"]},
                {"$set": update_data}
            )
            return existing["_id"]
        else:
            # 创建新文档
            return self._save_graph_to_mongo(
                portfolio_uuid=portfolio_uuid,
                graph_data=graph_data,
                name=name or f"Graph for {portfolio_uuid[:8]}",
                source=source
            )

    def _sync_mappings_from_files(
        self,
        portfolio_uuid: str,
        file_mappings: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """
        从文件列表同步到 MySQL Mapping

        Args:
            portfolio_uuid: 投资组合 UUID
            file_mappings: 文件映射列表

        Returns:
            mapping_uuids: {file_id: mapping_uuid} 字典
        """
        # 获取现有映射
        existing = self._mapping_crud.find_by_portfolio(portfolio_uuid)
        existing_files = {m.file_id: m for m in existing}

        # 当前文件集合
        current_files = {fm["file_id"]: fm for fm in file_mappings}

        # 返回的 mapping_uuid 映射
        mapping_uuids = {}

        # 1. 添加新映射
        for file_id, fm in current_files.items():
            if file_id not in existing_files:
                mapping = MPortfolioFileMapping(
                    portfolio_id=portfolio_uuid,
                    file_id=fm["file_id"],
                    name=fm["name"],
                    type=fm["type"],
                    source=SOURCE_TYPES.SIM
                )
                mapping_uuid = self._mapping_crud.add(mapping)
                mapping_uuids[file_id] = mapping_uuid
            else:
                # 已存在，使用现有的 UUID
                mapping_uuids[file_id] = existing_files[file_id].uuid

        # 2. 删除不再使用的映射
        for file_id, existing_mapping in existing_files.items():
            if file_id not in current_files:
                self._mapping_crud.delete_mapping(portfolio_uuid, file_id)
                # 同时删除参数
                self._param_service.remove_by_mapping(existing_mapping.uuid)

        return mapping_uuids

    def _restore_removed_file_mappings(self, mappings: list, param_snapshots: Dict[str, list]) -> None:
        """恢复 remove_file 已删除的 MySQL mapping/params（补偿原语，#5559）。"""
        for mapping in mappings or []:
            try:
                restored = MPortfolioFileMapping(
                    portfolio_id=getattr(mapping, "portfolio_id", ""),
                    file_id=getattr(mapping, "file_id", ""),
                    name=getattr(mapping, "name", "ginkgo_bind"),
                    type=getattr(mapping, "type", FILE_TYPES.OTHER),
                    source=getattr(mapping, "source", SOURCE_TYPES.SIM),
                )
                restored_mapping = self._mapping_crud.add(restored)
                restored_uuid = getattr(restored_mapping, "uuid", None) or getattr(mapping, "uuid", "")
                for param in param_snapshots.get(getattr(mapping, "uuid", ""), []):
                    self._param_service.add_param(
                        mapping_id=restored_uuid,
                        index=int(getattr(param, "index", 0)),
                        value=getattr(param, "value", ""),
                        source=getattr(param, "source", SOURCE_TYPES.SIM),
                    )
            except Exception as e:
                GLOG.ERROR(f"补偿恢复文件映射失败: {getattr(mapping, 'uuid', '')}, {e}")

    def _sync_params_from_nodes(
        self,
        portfolio_uuid: str,
        node_params: List[Dict[str, Any]],
    ) -> None:
        """
        从节点参数同步到 MySQL MParam

        Args:
            portfolio_uuid: 投资组合 UUID
            node_params: 节点参数列表 [{"file_id": "...", "params": {...}}, ...]
        """
        # 获取该 portfolio 的所有 mappings
        mappings = self._mapping_crud.find_by_portfolio(portfolio_uuid)
        file_to_mapping = {m.file_id: m.uuid for m in mappings}

        for node_param in node_params:
            file_id = node_param["file_id"]
            params = node_param["params"]

            # 查找对应的 mapping_uuid
            mapping_uuid = file_to_mapping.get(file_id)
            if not mapping_uuid:
                GLOG.WARN(f"未找到文件 {file_id} 的映射，跳过参数同步")
                continue

            # 同步参数
            self._sync_params_for_mapping(
                mapping_uuid=mapping_uuid,
                params=params
            )

    def _sync_params_for_mapping(
        self,
        mapping_uuid: str,
        params: Dict[str, Any],
    ) -> None:
        """同步参数到指定的 mapping（落库格式与 CLI create_component_parameters 对齐）

        value 序列化：字符串原样存（对齐 CLI 原样 str），非字符串才 json.dumps，
        这样读端 json.loads+fallback（component_loader 约定）能正确还原类型。
        原实现一律 json.dumps，字符串 value 会多一层引号，与 CLI 同值产出类型分歧。
        """
        # 将参数字典转换为扁平列表
        param_list = []
        for key, value in params.items():
            if isinstance(value, str):
                value_str = value
            else:
                try:
                    value_str = json.dumps(value, ensure_ascii=False)
                except Exception as e:
                    GLOG.ERROR(f"序列化参数值失败: {e}")
                    value_str = str(value)
            param_list.append({"key": key, "value": value_str})

        # 删除旧参数
        self._param_service.remove_by_mapping(mapping_uuid)

        # 添加新参数：index 取自 params 的 key（逻辑位置），与 CLI
        # create_component_parameters 的 MParam(index=key) 对齐；enumerate 顺序位
        # 会在 key 跳号时丢失逻辑位置（#5880 缺陷5）。
        for param in param_list:
            self._param_service.add_param(
                mapping_id=mapping_uuid,
                index=int(param["key"]),
                value=param["value"],
                source=SOURCE_TYPES.SIM,
            )

    def _sync_graph_from_mappings(self, portfolio_uuid: str) -> None:
        """
        从 MySQL Mapping 同步生成图结构

        读取 MySQL 中该投资组合的所有映射，
        在 MongoDB 中生成自动布局的图结构

        Args:
            portfolio_uuid: 投资组合 UUID
        """
        # 1. 获取所有映射
        mappings = self._mapping_crud.find_by_portfolio(portfolio_uuid)

        if not mappings:
            # 没有映射，清空图数据
            self._update_graph_in_mongo(
                portfolio_uuid=portfolio_uuid,
                graph_data={"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}},
                name=f"Empty graph for {portfolio_uuid[:8]}",
                source="AUTO_GENERATED"
            )
            return

        # 2. 生成图节点
        nodes = []
        y_offset = 0
        x_positions = {
            FILE_TYPES.STRATEGY: 100,
            FILE_TYPES.SELECTOR: 100,
            FILE_TYPES.SIZER: 400,
            FILE_TYPES.RISKMANAGER: 700,
            FILE_TYPES.ANALYZER: 1000,
        }

        type_groups = {}
        for mapping in mappings:
            if mapping.type not in type_groups:
                type_groups[mapping.type] = []
            type_groups[mapping.type].append(mapping)

        for file_type, type_mappings in type_groups.items():
            x_pos = x_positions.get(file_type, 100)
            for mapping in type_mappings:
                # 获取文件信息
                file_result = self._file_service.get_by_uuid(mapping.file_id)
                file_obj = file_result.data.get("file") if file_result.success else None
                if not file_obj:
                    continue

                # 获取节点参数
                params = self._get_params_for_mapping(mapping.uuid)

                node_id = f"auto_node_{mapping.file_id[:8]}"
                nodes.append({
                    "id": node_id,
                    "type": self._file_type_to_node_type(mapping.type),
                    "position": {"x": x_pos, "y": y_offset},
                    "data": {
                        "label": file_obj.name,
                        "file_id": mapping.file_id,
                        "mapping_uuid": mapping.uuid,
                        "params": params,
                        "auto_generated": True
                    }
                })
                y_offset += 150

        # 3. 生成简单边
        edges = self._generate_default_edges(nodes, mappings)

        # 4. 保存或更新到 MongoDB
        graph_data = {
            "nodes": nodes,
            "edges": edges,
            "viewport": {"x": 0, "y": 0, "zoom": 1}
        }

        self._update_graph_in_mongo(
            portfolio_uuid=portfolio_uuid,
            graph_data=graph_data,
            name=f"Auto generated for {portfolio_uuid[:8]}",
            source="AUTO_GENERATED"
        )

    def _get_params_for_mapping(self, mapping_uuid: str) -> Dict[str, Any]:
        """
        获取 mapping 的参数字典

        Args:
            mapping_uuid: Mapping UUID

        Returns:
            参数字典
        """
        params = self._param_service.find_by_mapping_id(mapping_uuid)

        params_dict = {}
        for p in params:
            try:
                value = json.loads(p.value) if p.value else {}
            except Exception as e:
                GLOG.ERROR(f"解析参数JSON值失败: {e}")
                value = p.value
            params_dict[f"param_{p.index}"] = value

        return params_dict

    def _generate_default_edges(
        self,
        nodes: List[Dict],
        mappings: List[MPortfolioFileMapping],
    ) -> List[Dict]:
        """
        生成默认的边连接

        规则：
        - STRATEGY → RISK_MANAGEMENT
        - STRATEGY → SIZER → RISK_MANAGEMENT
        - 所有 → ANALYZER

        Args:
            nodes: 节点列表
            mappings: 映射列表

        Returns:
            边列表
        """
        edges = []

        # 按 type 分组节点
        strategy_nodes = [n for n in nodes if n["type"] == "STRATEGY"]
        risk_nodes = [n for n in nodes if n["type"] == "RISK_MANAGEMENT"]
        sizer_nodes = [n for n in nodes if n["type"] == "SIZER"]
        analyzer_nodes = [n for n in nodes if n["type"] == "ANALYZER"]

        # 生成连接
        edge_id = 0
        for strategy in strategy_nodes:
            # 连接风控
            for risk in risk_nodes:
                edges.append({
                    "id": f"auto_edge_{edge_id}",
                    "source": strategy["id"],
                    "target": risk["id"],
                    "type": "default",
                    "animated": False
                })
                edge_id += 1

            # 连接分析器
            for analyzer in analyzer_nodes:
                edges.append({
                    "id": f"auto_edge_{edge_id}",
                    "source": strategy["id"],
                    "target": analyzer["id"],
                    "sourceHandle": "analysis",
                    "targetHandle": "input"
                })
                edge_id += 1

        return edges

    @staticmethod
    def _parse_node_type(node_type_str: str) -> FILE_TYPES:
        """
        解析节点类型字符串为枚举

        Args:
            node_type_str: 节点类型字符串

        Returns:
            FILE_TYPES 枚举值
        """
        type_map = {
            "STRATEGY": FILE_TYPES.STRATEGY,
            "SELECTOR": FILE_TYPES.SELECTOR,
            "SIZER": FILE_TYPES.SIZER,
            "RISK_MANAGEMENT": FILE_TYPES.RISKMANAGER,
            "RISK": FILE_TYPES.RISKMANAGER,
            "ANALYZER": FILE_TYPES.ANALYZER,
        }
        return type_map.get(node_type_str.upper(), FILE_TYPES.OTHER)

    @staticmethod
    def _file_type_to_node_type(file_type: FILE_TYPES) -> str:
        """
        文件类型转节点类型

        Args:
            file_type: FILE_TYPES 枚举

        Returns:
            节点类型字符串
        """
        return {
            FILE_TYPES.STRATEGY: "STRATEGY",
            FILE_TYPES.SELECTOR: "SELECTOR",
            FILE_TYPES.SIZER: "SIZER",
            FILE_TYPES.RISKMANAGER: "RISK_MANAGEMENT",
            FILE_TYPES.ANALYZER: "ANALYZER",
        }.get(file_type, "OTHER")
