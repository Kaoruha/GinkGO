# Upstream: ExecutionNode（管理Portfolio订阅）
# Downstream: PortfolioProcessor（路由事件）
# Role: InterestMap维护股票代码到Portfolio ID的映射，优化事件路由性能


"""
InterestMap - 股票代码订阅映射表

InterestMap维护股票代码到Portfolio ID列表的映射关系，用于优化ExecutionNode的事件路由性能：

核心功能：
- 维护 {code: [portfolio_ids]} 映射
- O(1) 查询订阅某股票的Portfolio列表
- 支持动态添加/移除订阅
- 线程安全（使用Lock）

性能优势：
- 无InterestMap：O(n) 遍历所有Portfolio
- 有InterestMap：O(1) 直接查询订阅者

使用场景：
- ExecutionNode.route_message() - 根据股票代码路由事件
- Portfolio加载/卸载 - 更新订阅关系
- 动态订阅更新 - 策略运行时调整订阅
"""

from typing import Dict, List, Set
from threading import Lock


class InterestMap:
    """股票代码订阅映射表"""

    def __init__(self):
        """
        初始化InterestMap

        数据结构：
        - interest_map: {code: set(portfolio_ids)}
          - code: 股票代码（如 "000001.SZ"）
          - portfolio_ids: 订阅该股票的Portfolio ID集合
        """
        self.interest_map: Dict[str, Set[str]] = {}
        self.lock = Lock()

    def add_portfolio(self, portfolio_id: str, codes: List[str]):
        """
        添加Portfolio及其订阅的股票代码

        Args:
            portfolio_id: Portfolio ID
            codes: 订阅的股票代码列表

        示例：
            interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])
        """
        with self.lock:
            for code in codes:
                if code not in self.interest_map:
                    self.interest_map[code] = set()

                self.interest_map[code].add(portfolio_id)

    def remove_portfolio(self, portfolio_id: str, codes: List[str]):
        """
        移除Portfolio的订阅

        Args:
            portfolio_id: Portfolio ID
            codes: 取消订阅的股票代码列表

        注意：
            - 如果某个code的订阅者列表为空，会自动删除该code条目
        """
        with self.lock:
            for code in codes:
                if code in self.interest_map:
                    self.interest_map[code].discard(portfolio_id)

                    # 如果没有订阅者了，删除该code条目
                    if not self.interest_map[code]:
                        del self.interest_map[code]

    def get_portfolios(self, code: str) -> List[str]:
        """
        根据股票代码查询订阅的Portfolio列表（O(1)查询）

        Args:
            code: 股票代码

        Returns:
            List[str]: 订阅该股票的Portfolio ID列表，如果没有订阅者返回空列表

        示例：
            portfolios = interest_map.get_portfolios("000001.SZ")
            # 返回: ["portfolio_1", "portfolio_2"]
        """
        with self.lock:
            if code in self.interest_map:
                return list(self.interest_map[code])
            return []

    def update_portfolio(self, portfolio_id: str, old_codes: List[str], new_codes: List[str]):
        """
        更新Portfolio的订阅（原子操作）

        Args:
            portfolio_id: Portfolio ID
            old_codes: 旧的订阅列表
            new_codes: 新的订阅列表

        用途：
            策略调整订阅股票池时使用，确保更新过程原子性
        """
        with self.lock:
            # 移除旧订阅
            for code in old_codes:
                if code in self.interest_map:
                    self.interest_map[code].discard(portfolio_id)
                    if not self.interest_map[code]:
                        del self.interest_map[code]

            # 添加新订阅
            for code in new_codes:
                if code not in self.interest_map:
                    self.interest_map[code] = set()
                self.interest_map[code].add(portfolio_id)

    def get_all_subscriptions(self, portfolio_id: str) -> List[str]:
        """
        获取Portfolio订阅的所有股票代码

        Args:
            portfolio_id: Portfolio ID

        Returns:
            List[str]: Portfolio订阅的股票代码列表
        """
        with self.lock:
            subscriptions = []
            for code, portfolio_ids in self.interest_map.items():
                if portfolio_id in portfolio_ids:
                    subscriptions.append(code)
            return subscriptions

    def clear(self):
        """清空所有订阅关系"""
        with self.lock:
            self.interest_map.clear()

    def size(self) -> int:
        """
        获取订阅的股票代码数量

        Returns:
            int: 唯一股票代码数量
        """
        with self.lock:
            return len(self.interest_map)

    def __len__(self) -> int:
        """获取订阅的股票代码数量"""
        return self.size()

    def __contains__(self, code: str) -> bool:
        """
        检查股票代码是否被订阅

        Args:
            code: 股票代码

        Returns:
            bool: 是否有Portfolio订阅该股票
        """
        with self.lock:
            return code in self.interest_map

    def __repr__(self) -> str:
        """字符串表示"""
        with self.lock:
            total_subscriptions = sum(len(ids) for ids in self.interest_map.values())
            return f"InterestMap(codes={len(self.interest_map)}, subscriptions={total_subscriptions})"
