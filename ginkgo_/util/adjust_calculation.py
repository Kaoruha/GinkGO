"""
复权计算
"""
import numpy as np


def adjust_cal(raw, adjust_factor, adjust_flag=1, frequency="d"):
    """
    复权计算

    :param raw: 原始交易数据
    :type raw: DataFrame
    :param adjust_factor: 复权因子
    :type adjust_factor: DataFrame
    :param adjust_flag: 复权方式, defaults to 1
    :type adjust_flag: int, optional
    :param frequency: 频率, defaults to 'd'
    :type frequency: str, optional
    :return: 复权后的交易数据
    :rtype: DataFrame
    """
    # 没有复权因子
    if adjust_factor.shape[0] == 0:
        return raw

    # 有复权因子
    # TODO 按照截至日期复权
    adjust_columns = []
    if frequency == "d":
        adjust_columns = ["open", "high", "low", "close", "pre_close"]
    elif frequency == "5":
        adjust_columns = ["open", "high", "low", "close"]

    for i in adjust_columns:
        raw[i] = raw[i].astype(np.float)
    for i in ["adjust_factor", "back_adjust_factor", "fore_adjust_factor"]:
        adjust_factor[i] = adjust_factor[i].astype(np.float)
    fore = raw.copy(deep=True)
    back = raw.copy(deep=True)
    for i in range(adjust_factor.shape[0] + 1):
        if i == 0:
            condition = raw["date"] < adjust_factor.iloc[0].divid_operate_date
            condition2 = raw["date"] <= adjust_factor.iloc[0].divid_operate_date

            fore.loc[condition, adjust_columns] *= adjust_factor.iloc[
                0
            ].fore_adjust_factor
            back.loc[condition2, adjust_columns] *= adjust_factor.iloc[
                0
            ].back_adjust_factor

        elif i == len(adjust_factor):
            condition = raw["date"] >= adjust_factor.iloc[i - 1]["divid_operate_date"]
            condition2 = raw["date"] > adjust_factor.iloc[i - 1]["divid_operate_date"]
            fore.loc[condition, adjust_columns] *= adjust_factor.iloc[i - 1][
                "fore_adjust_factor"
            ]
            back.loc[condition2, adjust_columns] *= adjust_factor.iloc[i - 1][
                "back_adjust_factor"
            ]
        else:
            condition = (raw["date"] < adjust_factor.iloc[i]["divid_operate_date"]) & (
                raw["date"] >= adjust_factor.iloc[i - 1]["divid_operate_date"]
            )
            condition2 = (
                raw["date"] <= adjust_factor.iloc[i]["divid_operate_date"]
            ) & (raw["date"] > adjust_factor.iloc[i - 1]["divid_operate_date"])
            fore.loc[condition, adjust_columns] *= adjust_factor.iloc[i][
                "fore_adjust_factor"
            ]
            back.loc[condition2, adjust_columns] *= adjust_factor.iloc[i][
                "back_adjust_factor"
            ]

    if adjust_flag == 1:
        return fore
    elif adjust_flag == 2:
        return back
    else:
        return raw
