import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt


def t_test(
    backtest_values: list,
    observe_values: list,
    level_of_confidence: float = 0.99,
) -> None:
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
    print(result)
    print(result.pvalue)
    print(t_critical)


def chi2_test(backtest_values: list, observe_values: list, category_count: int = 7) -> None:
    # Independent test
    # H0: There is no relation between backtest_values and observe_values.
    # H1: There is relation between backtest_values and observe_values.
    # if p < 0.05, refuse H0. accept H1. Two samples are from the same distribution.
    # if p > 0.05, accept H0. refuse H1. Two samples are from different distribution.
    # 卡方检验要求观测频数表中的每个分类的观测频数都大于或等于 5。
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
    print(chi2)
    print(p)
    print(degree_of_freedom)
    # 检验结果
    if p < 0.05:
        print("Refuse the null hypothesis. Two samples are from the same distribution.")
    else:
        print("Accept the null hypothesis. Two samples are from the different distribution.")

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
