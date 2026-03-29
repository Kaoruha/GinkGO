# Upstream: FileService (继承使用)
# Downstream: BaseService (依赖 _crud_repo 和 _logger)
# Role: 文件搜索功能混入，提供按名称/描述/内容/多字段统一搜索能力

"""
文件搜索功能模块 (Mixin)

从 FileService 中提取的搜索相关方法，作为 Mixin 供 FileService 继承使用。
包含 search_by_name、search_by_description、search_by_content、search 四个方法。

使用方式：FileService 继承 FileSearchMixin，外部 API 完全不变。
"""

from typing import List, Optional

from ginkgo.enums import FILE_TYPES
from ginkgo.data.services.base_service import ServiceResult


class FileSearchMixin:
    """文件搜索功能混入类，提供多种搜索能力"""

    def search_by_name(
        self,
        keyword: str,
        file_type: Optional[FILE_TYPES] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        page: int = 0,
        page_size: int = 50
    ) -> ServiceResult:
        """
        按文件名称搜索文件，支持模糊匹配和分页功能

        Args:
            keyword: 搜索关键词
            file_type: 可选的文件类型过滤
            exact_match: 是否精确匹配
            case_sensitive: 是否区分大小写
            page: 页码（从0开始）
            page_size: 每页结果数量

        Returns:
            ServiceResult: 包含搜索结果和分页信息的查询结果
        """
        try:
            # Input validation
            if not keyword or not keyword.strip():
                return ServiceResult.error("Search keyword cannot be empty")

            # Build filters using database-level LIKE queries
            filters = {"is_del": False}
            if file_type:
                filters["type"] = file_type

            # Use database-level filtering
            if exact_match:
                # Exact match: use exact field filter
                filters["name"] = keyword
            else:
                # Fuzzy match: use LIKE operator
                filters["name__like"] = f"%{keyword}%"

            # Get total count for pagination
            total_count = self._crud_repo.count(filters=filters)

            # Query database with pagination
            files = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="create_at",
                desc_order=True
            )

            # Format results - no need for in-memory filtering
            search_results = []
            for file_record in files:
                search_results.append({
                    "uuid": file_record.uuid,
                    "name": file_record.name,
                    "type": file_record.type,
                    "desc": file_record.desc,
                    "create_at": file_record.create_at,
                    "update_at": file_record.update_at,
                    "relevance": "name_match"
                })

            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
            has_next = page < total_pages - 1
            has_prev = page > 0

            return ServiceResult.success(
                data={
                    "search_type": "name_search",
                    "keyword": keyword,
                    "file_type": file_type,
                    "exact_match": exact_match,
                    "case_sensitive": case_sensitive,
                    "results": search_results,
                    "count": len(search_results),  # 向后兼容
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": has_next,
                        "has_prev": has_prev,
                        "count_on_page": len(search_results)
                    }
                },
                message=f"Found {len(search_results)} files matching name '{keyword}' (page {page + 1}/{total_pages})"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to search files by name: {e}")
            return ServiceResult.error(f"Search by name failed: {str(e)}")

    def search_by_description(
        self,
        keyword: str,
        file_type: Optional[FILE_TYPES] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        page: int = 0,
        page_size: int = 50
    ) -> ServiceResult:
        """
        按描述信息搜索文件，支持模糊匹配和分页功能

        Args:
            keyword: 搜索关键词
            file_type: 可选的文件类型过滤
            exact_match: 是否精确匹配
            case_sensitive: 是否区分大小写
            page: 页码（从0开始）
            page_size: 每页结果数量

        Returns:
            ServiceResult: 包含搜索结果和分页信息的查询结果
        """
        try:
            # Input validation
            if not keyword or not keyword.strip():
                return ServiceResult.error("Search keyword cannot be empty")

            # Build filters using database-level LIKE queries
            filters = {"is_del": False}
            if file_type:
                filters["type"] = file_type

            # Use database-level filtering
            if exact_match:
                # Exact match: use exact field filter
                filters["desc"] = keyword
            else:
                # Fuzzy match: use LIKE operator
                filters["desc__like"] = f"%{keyword}%"

            # Get total count for pagination
            total_count = self._crud_repo.count(filters=filters)

            # Query database with pagination
            files = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="create_at",
                desc_order=True
            )

            # Format results - no need for in-memory filtering
            search_results = []
            for file_record in files:
                search_results.append({
                    "uuid": file_record.uuid,
                    "name": file_record.name,
                    "type": file_record.type,
                    "desc": file_record.desc,
                    "create_at": file_record.create_at,
                    "update_at": file_record.update_at,
                    "relevance": "description_match"
                })

            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
            has_next = page < total_pages - 1
            has_prev = page > 0

            return ServiceResult.success(
                data={
                    "search_type": "description_search",
                    "keyword": keyword,
                    "file_type": file_type,
                    "exact_match": exact_match,
                    "case_sensitive": case_sensitive,
                    "results": search_results,
                    "count": len(search_results),  # 向后兼容
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": has_next,
                        "has_prev": has_prev,
                        "count_on_page": len(search_results)
                    }
                },
                message=f"Found {len(search_results)} files matching description '{keyword}' (page {page + 1}/{total_pages})"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to search files by description: {e}")
            return ServiceResult.error(f"Search by description failed: {str(e)}")

    def search_by_content(
        self,
        keyword: str,
        file_type: Optional[FILE_TYPES] = None,
        page: int = 0,
        page_size: int = 50
    ) -> ServiceResult:
        """
        按文件内容搜索文件，在二进制数据中搜索文本内容

        Args:
            keyword: 搜索关键词
            file_type: 可选的文件类型过滤
            page: 页码（从0开始）
            page_size: 每页结果数量

        Returns:
            ServiceResult: 包含搜索结果和分页信息的查询结果
        """
        try:
            # Input validation
            if not keyword or not keyword.strip():
                return ServiceResult.error("Search keyword cannot be empty")

            # Build filters
            filters = {"is_del": False}
            if file_type:
                filters["type"] = file_type

            # Get total count first (for pagination)
            total_count = self._crud_repo.count(filters=filters)

            # Get files with pagination for content search
            files = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size,
                order_by="create_at",
                desc_order=True
            )

            # Search in content (application-level filtering is necessary for binary data)
            search_results = []
            keyword_bytes = keyword.encode('utf-8', errors='ignore')

            for file_record in files:
                if hasattr(file_record, 'data') and file_record.data:
                    # Search for keyword in binary data
                    if keyword_bytes.lower() in file_record.data.lower():
                        search_results.append({
                            "uuid": file_record.uuid,
                            "name": file_record.name,
                            "type": file_record.type,
                            "desc": file_record.desc,
                            "content_size": len(file_record.data),
                            "create_at": file_record.create_at,
                            "update_at": file_record.update_at,
                            "relevance": "content_match"
                        })

            # Calculate pagination info
            total_pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
            has_next = page < total_pages - 1
            has_prev = page > 0

            return ServiceResult.success(
                data={
                    "search_type": "content_search",
                    "keyword": keyword,
                    "file_type": file_type,
                    "results": search_results,
                    "count": len(search_results),  # 向后兼容
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": has_next,
                        "has_prev": has_prev,
                        "count_on_page": len(search_results)
                    }
                },
                message=f"Found {len(search_results)} files containing keyword '{keyword}' (page {page + 1}/{total_pages})"
            )

        except Exception as e:
            self._logger.ERROR(f"Failed to search files by content: {e}")
            return ServiceResult.error(f"Search by content failed: {str(e)}")

    def search(
        self,
        keyword: str,
        search_in: List[str] = ["name", "description"],
        file_type: Optional[FILE_TYPES] = None,
        exact_match: bool = False,
        case_sensitive: bool = False,
        page: int = 0,
        page_size: int = 50
    ) -> ServiceResult:
        """
        统一搜索方法，可在多个字段中搜索并返回合并结果

        Args:
            keyword: 搜索关键词
            search_in: 搜索字段列表，如["name", "description"]
            file_type: 可选的文件类型过滤
            exact_match: 是否精确匹配
            case_sensitive: 是否区分大小写
            page: 页码（从0开始）
            page_size: 每页结果数量

        Returns:
            ServiceResult: 包含所有指定字段的搜索结果
        """
        try:
            # Input validation
            if not keyword or not keyword.strip():
                return ServiceResult.error("Search keyword cannot be empty")

            if not search_in:
                return ServiceResult.error("Search fields cannot be empty")

            # Validate search fields
            valid_fields = ["name", "description"]
            invalid_fields = [field for field in search_in if field not in valid_fields]
            if invalid_fields:
                return ServiceResult.error(f"Invalid search fields: {invalid_fields}. Valid fields: {valid_fields}")

            # Use direct database query with OR conditions for better performance
            from sqlalchemy import or_
            from ginkgo.data.models import MFile

            conn = self._crud_repo._get_connection()
            with conn.get_session() as session:
                query = session.query(MFile).filter(MFile.is_del == False)

                # Build OR conditions for multi-field search
                or_conditions = []

                for field in search_in:
                    if field == "name":
                        if exact_match:
                            or_conditions.append(MFile.name == keyword)
                        else:
                            or_conditions.append(MFile.name.like(f"%{keyword}%"))
                    elif field == "description":
                        if exact_match:
                            or_conditions.append(MFile.desc == keyword)
                        else:
                            or_conditions.append(MFile.desc.like(f"%{keyword}%"))

                # Apply OR conditions
                if or_conditions:
                    query = query.filter(or_(*or_conditions))

                # Apply file type filter if specified
                if file_type is not None:
                    query = query.filter(MFile.type == file_type.value)

                # Count total results
                total_count = query.count()

                # Apply pagination and ordering
                query = query.order_by(MFile.create_at.desc())
                query = query.offset(page * page_size).limit(page_size)

                # Execute query
                files = query.all()

                # Format results similar to other search methods
                results = []
                for file_record in files:
                    results.append({
                        "uuid": file_record.uuid,
                        "name": file_record.name,
                        "type": file_record.type,
                        "desc": file_record.desc,
                        "create_at": file_record.create_at,
                        "update_at": file_record.update_at,
                        "relevance": "multi_field_match"
                    })

                self._logger.DEBUG(
                    f"Unified search completed: {total_count} files found, "
                    f"returning {len(results)} results (page {page})"
                )

                return ServiceResult.success(
                    data={
                        "search_type": "unified_search",
                        "keyword": keyword,
                        "search_in": search_in,
                        "file_type": file_type,
                        "exact_match": exact_match,
                        "case_sensitive": case_sensitive,
                        "results": results,
                        "count": len(results),  # 向后兼容
                        "total_found": total_count,
                        "pagination": {
                            "page": page,
                            "page_size": page_size,
                            "total_count": total_count,
                            "total_pages": (total_count + page_size - 1) // page_size,
                            "has_next": (page + 1) * page_size < total_count,
                            "has_prev": page > 0,
                            "count_on_page": len(results)
                        }
                    },
                    message=f"Found {total_count} files matching '{keyword}' in {search_in}"
                )

        except Exception as e:
            self._logger.ERROR(f"Failed to perform unified search: {e}")
            return ServiceResult.error(f"Unified search failed: {str(e)}")
