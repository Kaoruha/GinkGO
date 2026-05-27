# Issue: _parse_filters 只支持 AND 条件
# Upstream: BaseCRUD.find(), BaseCRUD.count()
# Downstream: StockinfoService.search(), FileService.list_components()
# Role: 验证 __or__ filter 正确生成 OR 条件

"""
BaseCRUD __or__ filter 测试

验证 _parse_filters 支持 __or__ 特殊 key，
将子条件列表用 or_() 组合后嵌入 AND 链。
"""

import pytest


class TestOrFilter:
    """__or__ filter 测试"""

    def test_or_generates_or_condition(self):
        """__or__ 应生成 or_ 条件"""

        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        crud = StockInfoCRUD()
        filters = {
            "__or__": [
                {"code__like": "000001"},
                {"code_name__like": "平安"},
            ]
        }
        conditions = crud._parse_filters(filters)

        assert len(conditions) == 1
        condition_str = str(conditions[0])
        assert "OR" in condition_str.upper()

    def test_or_combined_with_and_conditions(self):
        """__or__ 与普通 AND 条件共存"""

        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        crud = StockInfoCRUD()
        filters = {
            "is_del": False,
            "__or__": [
                {"code__like": "000001"},
                {"code_name__like": "平安"},
            ]
        }
        conditions = crud._parse_filters(filters)

        # 两个条件：is_del == False + or_(code LIKE, code_name LIKE)
        assert len(conditions) == 2

        # 一个是等值条件，一个是 OR
        cond_strs = [str(c) for c in conditions]
        or_cond = [s for s in cond_strs if "OR" in s.upper()]
        eq_cond = [s for s in cond_strs if "OR" not in s.upper()]
        assert len(or_cond) == 1
        assert len(eq_cond) == 1

    def test_empty_or_list_produces_no_condition(self):
        """空 __or__ 列表不应生成条件"""

        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        crud = StockInfoCRUD()
        filters = {"__or__": []}
        conditions = crud._parse_filters(filters)

        assert len(conditions) == 0

    def test_or_with_equality_and_operator(self):
        """__or__ 子条件可以是等值和操作符混合"""

        from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
        crud = StockInfoCRUD()
        filters = {
            "__or__": [
                {"code": "000001.SZ"},
                {"code_name__like": "平安"},
            ]
        }
        conditions = crud._parse_filters(filters)

        assert len(conditions) == 1
        cond_str = str(conditions[0])
        assert "OR" in cond_str.upper()
