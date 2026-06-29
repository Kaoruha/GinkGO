# Upstream: 回测评估模块、分析器模块 (统计检验)
# Downstream: numpy, pandas, scipy.stats(延迟导入)
# Role: 统计检验工具模块，提供t_test独立样本t检验和chi2_test卡方检验，用于回测与实盘分布对比分析






import numpy as np
import pandas as pd
from collections import namedtuple

# scipy使用延迟导入避免启动时冲突
# import scipy.stats as stats
# import matplotlib.pyplot as plt


# 统计检验结构化结果（#5521：库函数返回结构化对象，不再以 print 作为副作用输出）
TTestResult = namedtuple(
    "TTestResult", ["statistic", "pvalue", "t_critical", "degree_of_freedom"]
)
Chi2TestResult = namedtuple(
    "Chi2TestResult", ["chi2", "p", "degree_of_freedom", "expected"]
)


def t_test(
    backtest_values: list,
    observe_values: list,
    level_of_confidence: float = 0.99,
) -> TTestResult:
    """独立样本 t 检验（回测 vs 实盘分布对比）。

    Returns:
        TTestResult(statistic, pvalue, t_critical, degree_of_freedom)。
        #5521：移除 print 副作用，返回结构化结果含 t_critical。
    """
    # 延迟导入scipy以避免启动时冲突
    try:
        import scipy.stats as stats
    except ImportError as e:
        raise ImportError(f"scipy is required for t_test function: {e}")

    # 兼容 list / np.array 输入（签名标注 list，内部 .var() 需数组）
    backtest_values = np.asarray(backtest_values, dtype=float)
    observe_values = np.asarray(observe_values, dtype=float)

    len1 = len(backtest_values)
    len2 = len(observe_values)
    var1 = backtest_values.var()
    var2 = observe_values.var()
    result = stats.ttest_ind(backtest_values, observe_values)

    if var1 == var2:
        degree_of_freedom = len1 + len2 - 2
    else:
        degree_of_freedom = (len1 - 1) * (len2 - 1) / (var1 / len1 + var2 / len2)
    t_critical = stats.t.ppf(level_of_confidence, degree_of_freedom)
    return TTestResult(
        statistic=result.statistic,
        pvalue=result.pvalue,
        t_critical=t_critical,
        degree_of_freedom=degree_of_freedom,
    )


def chi2_test(
    backtest_values: list,
    observe_values: list,
    category_count: int = 7,
) -> Chi2TestResult:
    """卡方独立性检验（回测 vs 实盘分布对比）。

    Returns:
        Chi2TestResult(chi2, p, degree_of_freedom, expected)。
        #5521：移除 print 副作用返回结构化结果；修正原注释/文本与 p 值逻辑相反的错误。
    """
    # 卡方独立性检验
    # H0: backtest_values 与 observe_values 独立（无关联）
    # H1: 两者存在关联
    # p < 0.05 拒 H0：两样本有关联（分布显著不同）
    # p >= 0.05 接受 H0：无足够证据否定独立
    # （原代码注释/文本与此逻辑完全相反，#5521 修正）
    # 注：卡方检验要求观测频数表中每个分类的频数 >= 5

    # 延迟导入scipy以避免启动时冲突
    try:
        import scipy.stats as stats
    except ImportError as e:
        raise ImportError(f"scipy is required for chi2_test function: {e}")

    df1 = pd.DataFrame({"data": backtest_values})
    df2 = pd.DataFrame({"data": observe_values})
    min_value = min(min(backtest_values), min(observe_values))
    max_value = max(max(backtest_values), max(observe_values))
    bins = np.linspace(min_value, max_value, category_count)
    group1 = df1["data"].groupby(pd.cut(df1["data"], bins))
    group2 = df2["data"].groupby(pd.cut(df2["data"], bins))

    observed = np.array([group1.size().tolist(), group2.size().tolist()])

    # Remove empty bins to avoid zero elements in contingency table
    non_zero_mask = (observed[0] > 0) | (observed[1] > 0)
    if not non_zero_mask.any():
        raise ValueError("No valid bins with data found")

    observed_filtered = observed[:, non_zero_mask]

    # Check if we have at least 2 bins after filtering
    if observed_filtered.shape[1] < 2:
        raise ValueError("Insufficient non-empty bins for chi-square test")

    chi2, p, degree_of_freedom, expected = stats.chi2_contingency(observed_filtered)
    return Chi2TestResult(
        chi2=chi2,
        p=p,
        degree_of_freedom=degree_of_freedom,
        expected=expected,
    )

    # plt.bar(
    #     bins[:-1],
    #     group1.size(),
    #     width=(max_value - min_value) / category_count,
    #     color="b",
    #     alpha=0.5,
    # )
    # plt.bar(
    #     bins[:-1],
    #     group2.size(),
    #     width=(max_value - min_value) / category_count,
    #     color="r",
    #     alpha=0.5,
    # )
    # plt.xlabel("Category")
    # plt.ylabel("Frequency")
    # plt.legend(["Backtest", "Observe"])
    # plt.show()


def kolmogorov_smirnov_test() -> None:
    pass


def rank_sum_test() -> None:
    pass

