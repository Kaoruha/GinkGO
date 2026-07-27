# Upstream: 因子存储行(MFactor dict,来自 FundamentalFactorMaterializer 或 factor_crud 查询)
# Downstream: ExpressionEngine / FactorEngine(宽表 DataFrame 喂给 FieldNode 取列)
# Role: 因子存储行 → 表达式引擎可消费的宽表(列=因子名小写,按公告日 forward-fill 到交易日轴)

import pandas as pd


def assemble_factor_dataframe(factor_records, date_index):
    """
    把因子存储行组装成表达式引擎可消费的宽表 DataFrame (#6795 L3)。

    列名 = 因子名小写(对齐 FieldNode 的 `.lstrip('$').lower()` 标准化:
    表达式 $EPS / $eps 都会查 'eps' 列);行 = 交易日轴;值按公告日 forward-fill
    (交易日 ≥ 公告日起生效,公告日前 NaN,避免 PIT 前瞻)。

    这是 #6795 acceptance 第3条"基本面因子定义库可计算产出非零值"的数据胶水层:
    物化进因子存储的基本面因子(EPS/ROE/...)经此组装后,ExpressionEngine 的
    FieldNode($eps/$roe)即能取到非零列值,含基本面变量的表达式可计算。

    Args:
        factor_records: 因子行列表,每行含 factor_name / factor_value / timestamp
                        (timestamp = 公告日 ann_date,如 "20240430";
                        FundamentalFactorMaterializer 已保证取 ann_date 而非报告期)。
        date_index: 交易日轴(YYYYMMDD 字符串列表),作为宽表行索引。

    Returns:
        pd.DataFrame: index=date_index(原字符串格式),列=因子名小写,
                      值按报告期 forward-fill。无因子行时返回空宽表(仅 index)。
    """
    idx = pd.to_datetime(pd.Index(date_index))

    if not factor_records:
        return pd.DataFrame(index=pd.Index(date_index))

    df = pd.DataFrame(factor_records)
    if "factor_name" not in df.columns:
        return pd.DataFrame(index=pd.Index(date_index))

    df = df[["factor_name", "factor_value", "timestamp"]].copy()
    df["factor_value"] = pd.to_numeric(df["factor_value"], errors="coerce")
    df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["_col"] = df["factor_name"].astype(str).str.lower()
    df = df.dropna(subset=["_ts"])

    wide = pd.DataFrame(index=idx)
    for col, grp in df.groupby("_col"):
        series = grp.set_index("_ts")["factor_value"]
        # 同一公告日多次记录(重复物化 / 财报重述)取最后一条。materialize 非幂等、
        # MFactor 无唯一约束,存储层会有重复行,此处 keep="last" 做读侧兜底去重。
        series = series[~series.index.duplicated(keep="last")].sort_index()
        wide[col] = series.reindex(idx, method="ffill")

    wide.index = pd.Index(date_index)
    return wide
