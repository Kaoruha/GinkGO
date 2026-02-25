# Upstream: datetime, typing, ginkgo.validation.models
# Downstream: ginkgo.client.validation_cli
# Role: 走步验证 - 滑动窗口验证，计算过拟合程度

"""
WalkForwardValidator - 走步验证

使用滑动窗口进行样本外验证，评估策略过拟合程度。

核心功能:
- 生成滚动/扩展窗口折
- 在训练期优化参数
- 在测试期评估性能
- 计算退化程度

Usage:
    from ginkgo.validation.walk_forward import WalkForwardValidator
    from datetime import datetime

    validator = WalkForwardValidator(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        n_folds=5,
        train_ratio=0.7,
    )

    validator.set_backtest_function(my_backtest)
    validator.set_test_function(my_test)
    result = validator.validate(params={})
    print(f"退化程度: {result.degradation:.2%}")
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
import time

from ginkgo.validation.models import WalkForwardFold, WalkForwardResult
from ginkgo.libs import GLOG


class WalkForwardValidator:
    """
    走步验证器

    使用滑动窗口进行样本外验证。

    Attributes:
        start_date: 开始日期
        end_date: 结束日期
        n_folds: 折数
        train_ratio: 训练期比例
        expanding: 是否使用扩展窗口 (默认 True)
    """

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        n_folds: int = 5,
        train_ratio: float = 0.7,
        expanding: bool = True,
    ):
        """
        初始化走步验证器

        Args:
            start_date: 开始日期
            end_date: 结束日期
            n_folds: 折数 (默认 5)
            train_ratio: 训练期比例 (默认 0.7)
            expanding: 是否使用扩展窗口 (默认 True)
        """
        self.start_date = start_date
        self.end_date = end_date
        self.n_folds = n_folds
        self.train_ratio = train_ratio
        self.expanding = expanding

        self._backtest_function: Optional[Callable] = None
        self._test_function: Optional[Callable] = None
        self._folds: List[WalkForwardFold] = []
        self._result: Optional[WalkForwardResult] = None

        GLOG.INFO(
            f"WalkForwardValidator 初始化: {n_folds} 折, "
            f"训练比例 {train_ratio:.0%}, "
            f"{'扩展' if expanding else '滚动'}窗口"
        )

    def set_backtest_function(self, func: Callable):
        """
        设置训练期回测函数

        Args:
            func: 回测函数，签名 func(params, start, end) -> Dict
        """
        self._backtest_function = func

    def set_test_function(self, func: Callable):
        """
        设置测试期评估函数

        Args:
            func: 测试函数，签名 func(params, start, end) -> Dict
        """
        self._test_function = func

    def generate_folds(self) -> List[WalkForwardFold]:
        """
        生成验证折

        Returns:
            折列表
        """
        total_days = (self.end_date - self.start_date).days + 1
        fold_size = total_days // (self.n_folds + 1)  # +1 确保有足够的测试期
        train_days = int(fold_size * self.train_ratio)
        test_days = fold_size - train_days

        self._folds = []

        for i in range(self.n_folds):
            if self.expanding:
                # 扩展窗口：训练期逐渐扩大
                train_start = self.start_date
                train_end = self.start_date + timedelta(days=(i + 1) * train_days + i * test_days)
                test_start = train_end + timedelta(days=1)
                test_end = test_start + timedelta(days=test_days - 1)
            else:
                # 滚动窗口：训练期长度固定
                train_start = self.start_date + timedelta(days=i * test_days)
                train_end = train_start + timedelta(days=train_days - 1)
                test_start = train_end + timedelta(days=1)
                test_end = test_start + timedelta(days=test_days - 1)

            # 确保不超过结束日期
            if test_end > self.end_date:
                test_end = self.end_date

            fold = WalkForwardFold(
                fold_num=i + 1,
                train_start=train_start.strftime("%Y-%m-%d"),
                train_end=train_end.strftime("%Y-%m-%d"),
                test_start=test_start.strftime("%Y-%m-%d"),
                test_end=test_end.strftime("%Y-%m-%d"),
            )
            self._folds.append(fold)

        GLOG.INFO(f"生成 {len(self._folds)} 折验证窗口")
        return self._folds

    def validate(self, params: Dict[str, Any]) -> WalkForwardResult:
        """
        执行走步验证

        Args:
            params: 策略参数

        Returns:
            WalkForwardResult 验证结果
        """
        start_time = time.time()

        if not self._folds:
            self.generate_folds()

        if self._backtest_function is None:
            raise ValueError("未设置训练期回测函数，请调用 set_backtest_function()")

        if self._test_function is None:
            raise ValueError("未设置测试期评估函数，请调用 set_test_function()")

        result = WalkForwardResult(n_folds=self.n_folds)

        GLOG.INFO(f"开始走步验证: {self.n_folds} 折")

        for fold in self._folds:
            # 训练期回测
            train_result = self._backtest_function(
                params,
                fold.train_start,
                fold.train_end,
            )
            fold.train_score = train_result.get("score", 0.0)
            fold.train_metrics = {k: v for k, v in train_result.items() if k != "score"}
            fold.params = params.copy()

            # 测试期评估
            test_result = self._test_function(
                params,
                fold.test_start,
                fold.test_end,
            )
            fold.test_score = test_result.get("score", 0.0)
            fold.test_metrics = {k: v for k, v in test_result.items() if k != "score"}

            result.add_fold_result(fold)

            GLOG.INFO(
                f"折 {fold.fold_num}: 训练分数 {fold.train_score:.4f}, "
                f"测试分数 {fold.test_score:.4f}"
            )

        # 计算退化程度
        degradation = result.calculate_degradation()

        duration = time.time() - start_time
        GLOG.INFO(
            f"走步验证完成: 平均训练分数 {result.mean_train_score:.4f}, "
            f"平均测试分数 {result.mean_test_score:.4f}, "
            f"退化程度 {degradation:.2%}, "
            f"耗时 {duration:.2f}s"
        )

        self._result = result
        return result

    def get_summary(self) -> Dict[str, Any]:
        """
        获取验证摘要

        Returns:
            摘要字典
        """
        summary = {
            "n_folds": self.n_folds,
            "train_ratio": self.train_ratio,
            "expanding": self.expanding,
            "start_date": self.start_date.strftime("%Y-%m-%d"),
            "end_date": self.end_date.strftime("%Y-%m-%d"),
        }

        if self._result:
            summary.update({
                "mean_train_score": self._result.mean_train_score,
                "mean_test_score": self._result.mean_test_score,
                "degradation": self._result.degradation,
                "is_overfitting": self._result.is_overfitting(),
            })

        return summary

    def get_folds(self) -> List[WalkForwardFold]:
        """获取折列表"""
        return self._folds.copy()
