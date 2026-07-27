# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: FactorService因子服务提供因子计算/管理和查询功能支持量化分析






"""
因子服务 - 高级因子计算和管理服务

封装FactorEngine和ExpressionEngine，提供用户友好的API，
支持便捷的因子计算、批量处理、进度跟踪等功能。
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import ENTITY_TYPES

from ginkgo.features.engines import FactorEngine, ExpressionEngine
from ginkgo.features.definitions import Alpha158Factors


class FactorService:
    """
    因子服务 - 提供高级因子计算接口
    
    功能包括：
    - Alpha158因子一键计算
    - 自定义因子表达式计算
    - 批量处理和进度跟踪
    - 错误恢复和重试机制
    """
    
    def __init__(self, factor_engine: FactorEngine, expression_engine: ExpressionEngine):
        """
        初始化因子服务
        
        Args:
            factor_engine: 因子计算引擎
            expression_engine: 表达式处理引擎
        """
        self.factor_engine = factor_engine
        self.expression_engine = expression_engine
        
        # 导入因子注册表用于查询
        from ginkgo.features.definitions.registry import factor_registry
        self.factor_registry = factor_registry
        
        GLOG.INFO("FactorService initialized successfully")
    
    def calculate_alpha158_factors(self,
                                 entity_ids: List[str],
                                 start_date: str,
                                 end_date: str,
                                 factor_names: Optional[List[str]] = None,
                                 entity_type: ENTITY_TYPES = ENTITY_TYPES.STOCK,
                                 batch_size: int = 1000) -> ServiceResult:
        """
        计算Alpha158因子集合
        
        Args:
            entity_ids: 实体ID列表
            start_date: 开始日期
            end_date: 结束日期  
            factor_names: 指定计算的因子名称，None表示计算全部
            entity_type: 实体类型
            batch_size: 批量处理大小
            
        Returns:
            ServiceResult: 计算结果和统计信息
        """
        result = ServiceResult()
        
        try:
            # 获取要计算的因子表达式
            if factor_names is None:
                expressions = Alpha158Factors.get_all_expressions()
                GLOG.INFO(f"计算全部Alpha158因子: {len(expressions)}个")
            else:
                all_expressions = Alpha158Factors.get_all_expressions()
                expressions = {name: all_expressions[name] for name in factor_names 
                             if name in all_expressions}
                GLOG.INFO(f"计算指定Alpha158因子: {len(expressions)}个")
            
            if not expressions:
                result.error = "没有找到可计算的因子表达式"
                return result
            
            # 验证表达式
            validation_result = self.expression_engine.validate_expressions(expressions)
            if not validation_result.success:
                result.error = f"表达式验证失败: {validation_result.error}"
                return result
            
            # 执行计算
            calculation_result = self.factor_engine.calculate_and_store(
                expressions=expressions,
                entity_ids=entity_ids,
                start_date=start_date,
                end_date=end_date,
                entity_type=entity_type,
                batch_size=batch_size
            )
            
            if calculation_result.success:
                result.success = True
                result.set_data("processed_entities", calculation_result.get_data("processed_entities"))
                result.set_data("total_factors_stored", calculation_result.get_data("total_factors_stored"))
                result.set_data("factor_count", len(expressions))
                
                GLOG.INFO(f"Alpha158因子计算完成: {len(expressions)}个因子, "
                         f"{calculation_result.get_data('total_factors_stored')}条记录")
            else:
                result.error = calculation_result.error
            
        except Exception as e:
            result.error = f"Alpha158因子计算失败: {str(e)}"
            GLOG.ERROR(result.error)

        return result

    def calculate_factors_by_library(
        self,
        library_name: str,
        entity_ids: List[str],
        start_date: str,
        end_date: str,
        entity_type: ENTITY_TYPES = ENTITY_TYPES.STOCK,
        batch_size: int = 1000,
        incremental: bool = True,
        factor_crud: Optional[Any] = None,
    ) -> ServiceResult:
        """计算指定因子库的因子(通用入口,支持增量物化。#6792)。

        Args:
            library_name: 因子库名(如 "alpha158",见 list_factor_libraries)
            entity_ids: 实体ID列表
            start_date/end_date: 时间范围(YYYY-MM-DD)
            entity_type: 实体类型
            batch_size: 批量存储大小
            incremental: True=跳过已物化 entity(二次运行写入为零);False=全量重算
            factor_crud: 增量查询用的 FactorCRUD;None 时降级为全量(不增量)

        Returns:
            ServiceResult: processed_entities / total_factors_stored /
                           skipped_entities / factor_count
        """
        result = ServiceResult(data={})

        try:
            expressions = self.factor_registry.get_factors_by_library(library_name)
            if not expressions:
                result.error = f"Library '{library_name}' not found or has no factors"
                return result

            validation_result = self.expression_engine.validate_expressions(expressions)
            if not validation_result.success:
                result.error = f"表达式验证失败: {validation_result.error}"
                return result

            # 增量物化:跳过 [start,end] 内对该库因子已有数据的 entity(#6792)
            target_ids = list(entity_ids)
            skipped = 0
            if incremental:
                crud = factor_crud if factor_crud is not None else getattr(self, "_factor_crud", None)
                if crud is not None:
                    materialized = set(crud.get_materialized_entities(
                        entity_type=entity_type,
                        factor_names=list(expressions.keys()),
                        start_time=start_date,
                        end_time=end_date,
                    ))
                    target_ids = [eid for eid in entity_ids if eid not in materialized]
                    skipped = len(entity_ids) - len(target_ids)
                    GLOG.INFO(f"增量物化: {skipped}/{len(entity_ids)} entity 已物化,跳过")

            if not target_ids:
                # 全已物化:零写入(满足"二次运行写入为零"验收,#6792)
                processed_entities = 0
                total_factors_stored = 0
                GLOG.INFO(f"全部 {skipped} entity 已物化,本次零写入")
            else:
                calculation_result = self.factor_engine.calculate_and_store(
                    expressions=expressions,
                    entity_ids=target_ids,
                    start_date=start_date,
                    end_date=end_date,
                    entity_type=entity_type,
                    batch_size=batch_size,
                )
                if not calculation_result.success:
                    result.error = calculation_result.error
                    return result
                # engine 成功路径必走 set_data → data 为 dict;or {} 仅兜底空 entity 边界
                calc_data = calculation_result.data or {}
                processed_entities = calc_data.get("processed_entities", 0)
                total_factors_stored = calc_data.get("total_factors_stored", 0)
                GLOG.INFO(f"库 {library_name} 因子计算完成: {len(expressions)} 个因子, "
                         f"{total_factors_stored} 条记录")

            result.success = True
            result.set_data("processed_entities", processed_entities)
            result.set_data("total_factors_stored", total_factors_stored)
            result.set_data("skipped_entities", skipped)
            result.set_data("factor_count", len(expressions))

        except Exception as e:
            result.error = f"calculate_factors_by_library failed: {str(e)}"
            GLOG.ERROR(result.error)

        return result

    def walk_forward_factor_evaluation(
        self,
        factor_name: str,
        entity_ids: List[str],
        start_date: str,
        end_date: str,
        evaluator: Callable,
        n_folds: int = 5,
        train_ratio: float = 0.7,
        factor_crud: Optional[Any] = None,
    ) -> ServiceResult:
        """走步因子评估: 滑动 train/test 折, 每折 PIT 读取因子, 输出样本外折 (#6793 验收3)。

        防全样本拟合: 不用全部数据算单一指标, 而是滑动 train/test 验证 (OOS),
        与全样本拟合的假阳性区分 (memory: iter037 OOS 证伪教训)。

        PIT: 每折只用该折时间窗内因子 — train [ts, te] / test [te+1, T],
        全部窗口 <= 评估终点 end_date (评估日 end_date 时数据已实现, 非未来)。

        evaluator 注入: (factors: List[MFactor]) -> score; 具体指标 (IC/IR/decay)
        由调用方提供 (#6794 提供 IC evaluator 并通过 CLI 调本方法)。

        Args:
            factor_name: 因子名称
            entity_ids: 实体代码列表
            start_date/end_date: 评估区间 (YYYY-MM-DD)
            evaluator: 因子效果打分函数 (因子列表 -> score)
            n_folds: 折数 (默认 5)
            train_ratio: 训练期比例 (默认 0.7)
            factor_crud: FactorCRUD (读窗口因子); None 报错

        Returns:
            ServiceResult: folds / mean_train_score / mean_test_score /
                           degradation / n_folds
        """
        result = ServiceResult(data={})

        try:
            crud = factor_crud if factor_crud is not None else getattr(self, "_factor_crud", None)
            if crud is None:
                result.error = "factor_crud required for walk-forward evaluation"
                return result

            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            total_days = (end - start).days + 1
            fold_size = total_days // (n_folds + 1)
            if fold_size <= 0:
                result.error = f"date range ({total_days}d) too small for {n_folds} folds"
                return result
            train_days = int(fold_size * train_ratio)
            test_days = fold_size - train_days

            folds_result = []
            train_scores = []
            test_scores = []

            def fetch_window(start_w: datetime, end_w: datetime) -> List[Any]:
                """PIT: 收集 [start_w, end_w] 窗口内所有 entity 的因子 (窗口有界, #6793)。"""
                out: List[Any] = []
                for eid in entity_ids:
                    out.extend(crud.get_factors_by_entity(
                        entity_type=ENTITY_TYPES.STOCK, entity_id=eid,
                        factor_names=[factor_name],
                        start_time=start_w, end_time=end_w,
                    ))
                return out

            for i in range(n_folds):
                train_start = start + timedelta(days=i * test_days)
                train_end = train_start + timedelta(days=train_days - 1)
                test_start = train_end + timedelta(days=1)
                test_end = test_start + timedelta(days=test_days - 1)
                if test_end > end:
                    test_end = end

                # PIT: 每折只用该折窗内因子 (窗口 end <= 评估终点)
                train_factors = fetch_window(train_start, train_end)
                test_factors = fetch_window(test_start, test_end)

                tr_score = evaluator(train_factors)
                te_score = evaluator(test_factors)
                train_scores.append(tr_score)
                test_scores.append(te_score)
                folds_result.append({
                    "fold": i + 1,
                    "train_start": train_start.strftime("%Y-%m-%d"),
                    "train_end": train_end.strftime("%Y-%m-%d"),
                    "test_start": test_start.strftime("%Y-%m-%d"),
                    "test_end": test_end.strftime("%Y-%m-%d"),
                    "train_score": tr_score,
                    "test_score": te_score,
                })

            mean_train = sum(train_scores) / len(train_scores) if train_scores else 0.0
            mean_test = sum(test_scores) / len(test_scores) if test_scores else 0.0
            degradation = (mean_train - mean_test) / mean_train if mean_train != 0 else 0.0

            result.success = True
            result.set_data("folds", folds_result)
            result.set_data("mean_train_score", mean_train)
            result.set_data("mean_test_score", mean_test)
            result.set_data("degradation", degradation)
            result.set_data("n_folds", len(folds_result))
            GLOG.INFO(f"走步因子评估完成: {len(folds_result)} 折, "
                     f"mean_train={mean_train:.4f}, mean_test={mean_test:.4f}, "
                     f"degradation={degradation:.2%}")

        except Exception as e:
            result.error = f"walk_forward_factor_evaluation failed: {e}"
            GLOG.ERROR(result.error)

        return result

    def calculate_core_factors(self,
                             entity_ids: List[str],
                             start_date: str,
                             end_date: str,
                             entity_type: ENTITY_TYPES = ENTITY_TYPES.STOCK) -> ServiceResult:
        """
        计算核心常用因子
        
        Args:
            entity_ids: 实体ID列表
            start_date: 开始日期
            end_date: 结束日期
            entity_type: 实体类型
            
        Returns:
            ServiceResult: 计算结果
        """
        core_expressions = Alpha158Factors.get_expressions_by_category("core")
        core_factor_names = list(core_expressions.keys())
        
        return self.calculate_alpha158_factors(
            entity_ids=entity_ids,
            start_date=start_date,
            end_date=end_date,
            factor_names=core_factor_names,
            entity_type=entity_type
        )
    
    def calculate_category_factors(self,
                                 category: str,
                                 entity_ids: List[str],
                                 start_date: str,
                                 end_date: str,
                                 entity_type: ENTITY_TYPES = ENTITY_TYPES.STOCK) -> ServiceResult:
        """
        按分类计算因子
        
        Args:
            category: 因子分类 ('price', 'ma', 'volatility', 'momentum', 'extremum', 'quantile', 'rsv')
            entity_ids: 实体ID列表
            start_date: 开始日期
            end_date: 结束日期
            entity_type: 实体类型
            
        Returns:
            ServiceResult: 计算结果
        """
        result = ServiceResult()
        
        try:
            # 根据分类获取因子表达式（对齐 BaseDefinition.CATEGORIES 真实 key）
            available = Alpha158Factors.get_category_names()
            if category not in available:
                result.error = f"未知的因子分类: {category}。可用分类: {available}"
                return result

            category_expressions = Alpha158Factors.get_expressions_by_category(category)
            factor_names = list(category_expressions.keys())
            
            return self.calculate_alpha158_factors(
                entity_ids=entity_ids,
                start_date=start_date,
                end_date=end_date,
                factor_names=factor_names,
                entity_type=entity_type
            )
            
        except Exception as e:
            result.error = f"分类因子计算失败: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态信息"""
        return {
            "factor_engine_stats": self.factor_engine.get_stats(),
            "expression_engine_stats": self.expression_engine.get_engine_stats(),
            "alpha158_total_factors": len(Alpha158Factors.get_all_expressions()),
            "alpha158_core_factors": len(Alpha158Factors.get_expressions_by_category("core")),
        }

    # ===== 新增因子查询API =====
    
    def list_factor_categories(self) -> ServiceResult:
        """
        查询所有因子分类
        
        Returns:
            ServiceResult: 包含所有分类信息
        """
        result = ServiceResult()
        
        try:
            all_categories = set()
            library_categories = {}
            
            # 收集所有库的分类信息
            for lib_name, lib_class in self.factor_registry.get_registered_libraries().items():
                categories = getattr(lib_class, 'CATEGORIES', {})
                lib_categories = list(categories.keys())
                
                library_categories[lib_name] = {
                    'categories': lib_categories,
                    'category_count': len(lib_categories)
                }
                
                all_categories.update(lib_categories)
            
            result.success = True
            result.set_data("all_categories", sorted(list(all_categories)))
            result.set_data("total_categories", len(all_categories))
            result.set_data("library_categories", library_categories)
            
            GLOG.INFO(f"查询到 {len(all_categories)} 个因子分类")
            
        except Exception as e:
            result.error = f"查询因子分类失败: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result
    
    def list_all_factors(self, include_expressions: bool = False) -> ServiceResult:
        """
        查询所有因子
        
        Args:
            include_expressions: 是否包含表达式详情
            
        Returns:
            ServiceResult: 包含所有因子信息
        """
        result = ServiceResult()
        
        try:
            all_factors = self.factor_registry.get_all_factors()
            
            if include_expressions:
                # 返回完整信息
                factor_data = all_factors
            else:
                # 仅返回因子名称列表
                factor_data = {}
                for lib_name, factors in all_factors.items():
                    factor_data[lib_name] = list(factors.keys())
            
            # 统计信息
            total_factors = sum(len(factors) for factors in all_factors.values())
            
            result.success = True
            result.set_data("factors", factor_data)
            result.set_data("total_factors", total_factors)
            result.set_data("total_libraries", len(all_factors))
            result.set_data("include_expressions", include_expressions)
            
            GLOG.INFO(f"查询到 {total_factors} 个因子，来自 {len(all_factors)} 个库")
            
        except Exception as e:
            result.error = f"查询所有因子失败: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result
    
    def get_factor_expression(self, factor_name: str, library_name: str = None) -> ServiceResult:
        """
        查询因子表达式 - 支持精确和模糊查询
        
        Args:
            factor_name: 因子名称
            library_name: 可选的库名称，用于精确查询
            
        Returns:
            ServiceResult: 包含因子表达式信息
        """
        result = ServiceResult()
        
        try:
            search_result = self.factor_registry.find_factor(factor_name, library_name)
            
            if search_result['total_matches'] == 0:
                if library_name:
                    result.error = f"未找到因子 '{library_name}.{factor_name}'"
                else:
                    result.error = f"未找到因子 '{factor_name}'"
                return result
            
            result.success = True
            result.set_data("factor_name", factor_name)
            result.set_data("library_name", library_name)
            result.set_data("matches", search_result['matches'])
            result.set_data("total_matches", search_result['total_matches'])
            
            if search_result['total_matches'] == 1:
                match = search_result['matches'][0]
                result.set_data("expression", match['expression'])
                result.set_data("library", match['library'])
                GLOG.INFO(f"找到因子: {match['library']}.{factor_name}")
            else:
                GLOG.INFO(f"找到 {search_result['total_matches']} 个匹配的因子 '{factor_name}'")
            
        except Exception as e:
            result.error = f"查询因子表达式失败: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result
    
    def find_factors_by_category(self, category: str, library_name: str = None) -> ServiceResult:
        """
        按分类查询因子
        
        Args:
            category: 分类名称
            library_name: 可选的库名称过滤
            
        Returns:
            ServiceResult: 包含分类下的所有因子
        """
        result = ServiceResult()
        
        try:
            search_result = self.factor_registry.get_factors_by_category(category, library_name)
            
            if search_result['total_matches'] == 0:
                scope = f"库 '{library_name}' 的" if library_name else ""
                result.error = f"在{scope}分类 '{category}' 中未找到任何因子"
                return result
            
            result.success = True
            result.set_data("category", category)
            result.set_data("library_name", library_name)
            result.set_data("matches", search_result['matches'])
            result.set_data("total_matches", search_result['total_matches'])
            
            # 按库分组统计
            library_stats = {}
            for match in search_result['matches']:
                lib = match['library']
                if lib not in library_stats:
                    library_stats[lib] = 0
                library_stats[lib] += 1
            
            result.set_data("library_stats", library_stats)
            
            scope_desc = f"库 '{library_name}' 的" if library_name else ""
            GLOG.INFO(f"在{scope_desc}分类 '{category}' 中找到 {search_result['total_matches']} 个因子")
            
        except Exception as e:
            result.error = f"按分类查询因子失败: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result
    
    def search_factors(self, keyword: str) -> ServiceResult:
        """
        关键词搜索因子
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            ServiceResult: 包含搜索结果
        """
        result = ServiceResult()
        
        try:
            search_result = self.factor_registry.search_factors(keyword)
            
            if search_result['total_matches'] == 0:
                result.error = f"未找到包含关键词 '{keyword}' 的因子"
                return result
            
            result.success = True
            result.set_data("keyword", keyword)
            result.set_data("matches", search_result['matches'])
            result.set_data("total_matches", search_result['total_matches'])
            
            # 按匹配类型分组统计
            match_type_stats = {'name': 0, 'expression': 0}
            for match in search_result['matches']:
                match_type_stats[match['match_type']] += 1
            
            result.set_data("match_type_stats", match_type_stats)
            
            GLOG.INFO(f"关键词 '{keyword}' 搜索到 {search_result['total_matches']} 个匹配因子")
            
        except Exception as e:
            result.error = f"关键词搜索失败: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result

    def get_factor_statistics(self) -> ServiceResult:
        """
        获取因子统计和验证报告
        
        Returns:
            ServiceResult: 包含详细统计信息
        """
        result = ServiceResult()
        
        try:
            # 获取库汇总信息
            library_summary = self.factor_registry.get_library_summary()
            
            # 获取验证结果
            validation_results = self.factor_registry.validate_libraries()
            
            # 获取元数据信息
            all_metadata = self.factor_registry.get_library_metadata()
            
            # 构建详细统计
            library_details = []
            total_duplicates = 0
            
            for lib_name, metadata in all_metadata.items():
                detail = {
                    'library_name': lib_name,
                    'display_name': metadata.get('name', lib_name),
                    'description': metadata.get('description', ''),
                    'raw_factors': metadata.get('raw_expression_count', 0),
                    'unique_factors': metadata.get('expression_count', 0),
                    'duplicate_factors': metadata.get('duplicate_count', 0),
                    'categories': metadata.get('category_count', 0),
                    'validation_errors': validation_results.get(lib_name, [])
                }
                library_details.append(detail)
                total_duplicates += detail['duplicate_factors']
            
            # 计算统计指标
            stats = {
                'total_libraries': library_summary.get('total_libraries', 0),
                'total_unique_factors': library_summary.get('total_expressions', 0),
                'total_categories': library_summary.get('total_categories', 0),
                'total_duplicates_removed': total_duplicates,
                'largest_library': library_summary.get('largest_library', None),
                'valid_libraries': len([lib for lib, errors in validation_results.items() if not errors]),
                'invalid_libraries': len([lib for lib, errors in validation_results.items() if errors])
            }
            
            result.success = True
            result.set_data("statistics", stats)
            result.set_data("library_details", library_details)
            result.set_data("validation_summary", {
                'total_libraries': len(validation_results),
                'valid_libraries': stats['valid_libraries'],
                'invalid_libraries': stats['invalid_libraries'],
                'validation_errors': {lib: errors for lib, errors in validation_results.items() if errors}
            })
            
            GLOG.INFO(f"统计完成: {stats['total_libraries']}个库, {stats['total_unique_factors']}个因子, "
                     f"{total_duplicates}个重复已去除")
            
        except Exception as e:
            result.error = f"获取因子统计失败: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result
    
    def get_library_validation_report(self) -> ServiceResult:
        """
        获取库验证详细报告
        
        Returns:
            ServiceResult: 包含验证详情
        """
        result = ServiceResult()
        
        try:
            validation_results = self.factor_registry.validate_libraries()
            
            report = {
                'validation_timestamp': None,  # 可以添加时间戳
                'libraries_validated': len(validation_results),
                'validation_details': {}
            }
            
            valid_count = 0
            for lib_name, errors in validation_results.items():
                is_valid = len(errors) == 0
                if is_valid:
                    valid_count += 1
                    
                metadata = self.factor_registry.get_library_metadata(lib_name)
                
                report['validation_details'][lib_name] = {
                    'is_valid': is_valid,
                    'error_count': len(errors),
                    'errors': errors,
                    'factor_count': metadata.get('expression_count', 0),
                    'duplicate_count': metadata.get('duplicate_count', 0),
                    'categories': metadata.get('categories', [])
                }
            
            report['summary'] = {
                'total_libraries': len(validation_results),
                'valid_libraries': valid_count,
                'invalid_libraries': len(validation_results) - valid_count,
                'validation_rate': valid_count / len(validation_results) if validation_results else 0
            }
            
            result.success = True
            result.set_data("validation_report", report)
            
            GLOG.INFO(f"验证报告生成完成: {valid_count}/{len(validation_results)} 个库通过验证")
            
        except Exception as e:
            result.error = f"生成验证报告失败: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result

