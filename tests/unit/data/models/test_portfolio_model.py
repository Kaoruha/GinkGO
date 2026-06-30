"""
MPortfolio model 测试

回归 #6478: MPortfolio.update() 必须刷新映射列 update_at（无 d），
而非误写为未映射的实例属性 updated_at（带 d），导致 SQLAlchemy flush 忽略、
update_at 列永不刷新。
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import datetime

import pandas as pd
import pytest

from ginkgo.data.models.model_portfolio import MPortfolio


@pytest.mark.unit
class TestMPortfolioUpdateRefreshesTimestamp:
    """update() 的每个 singledispatch 分支都必须刷新 mapped 列 update_at。"""

    def test_update_via_str_refreshes_update_at(self):
        """update(name=...) 后 update_at 必须推进（回归 #6478 str 分支）。"""
        p = MPortfolio(name="old", initial_capital=100000)
        # 锚定一个明显旧的时间，模拟 insert 时刻的 update_at
        old = datetime.datetime(2000, 1, 1, 0, 0, 0)
        p.update_at = old

        p.update("newname")

        assert p.update_at > old, (
            f"update_at 未被 update(str) 刷新（仍为 {p.update_at}）；"
            "疑似误写 self.updated_at（带 d）→ mapped 列 update_at 永不更新 #6478"
        )

    def test_update_via_series_refreshes_update_at(self):
        """update(pd.Series) 后 update_at 必须推进（回归 #6478 Series 分支）。"""
        p = MPortfolio(name="old", initial_capital=100000)
        old = datetime.datetime(2000, 1, 1, 0, 0, 0)
        p.update_at = old

        p.update(pd.Series({"name": "newname", "source": 0}))

        assert p.update_at > old, (
            f"update_at 未被 update(Series) 刷新（仍为 {p.update_at}）；"
            "疑似误写 self.updated_at（带 d）→ mapped 列 update_at 永不更新 #6478"
        )
