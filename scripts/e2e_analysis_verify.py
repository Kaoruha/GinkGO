#!/usr/bin/env python3
"""
E2E 验证脚本 — 基于真实回测 task_id 验证分析模块全部功能

验证项:
1. AnalysisEngine.analyze() → SingleReport
2. AnalysisEngine.compare() → ComparisonReport
3. AnalysisEngine.rolling() → RollingReport
4. AnalysisEngine.time_segments() → SegmentReport
5. AnalysisReport 的 to_dict / to_dataframe / to_rich
6. RollingReport 的 to_dict / to_dataframe / to_rich
7. SegmentReport 的 to_dict / to_dataframe / to_rich
8. ComparisonReport 的 to_dict / to_dataframe / to_rich
9. analyzer_summary 包含正确的统计量
10. stability_analysis 和 ic_analysis 指标正确注册
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from ginkgo.libs import GLOG, GCONF
from ginkgo.data.crud.analyzer_record_crud import AnalyzerRecordCRUD
from ginkgo.data.services.analyzer_service import AnalyzerService
from ginkgo.data.services.result_service import ResultService

GCONF.set_debug(True)

# ============================================================
# 配置
# ============================================================

# 使用已知有数据的 task_id
RUN_ID = "e91da857bfea44d281e48782fcec58d3"

passed = 0
failed = 0
errors = []


def check(condition, msg):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {msg}")
    else:
        failed += 1
        errors.append(msg)
        print(f"  ❌ {msg}")


def main():
    print("=" * 60)
    print(f"E2E 分析模块验证 — task_id: {RUN_ID}")
    print("=" * 60)

    # ============================================================
    # 1. 构造 AnalysisEngine
    # ============================================================
    print("\n[1] 构造 AnalysisEngine")
    try:
        crud = AnalyzerRecordCRUD()
        analyzer_service = AnalyzerService(crud)
        result_service = ResultService(crud)
        from ginkgo.trading.analysis.engine import AnalysisEngine
        engine = AnalysisEngine(result_service, analyzer_service)
        check(True, "AnalysisEngine 构造成功")
    except Exception as e:
        check(False, f"AnalysisEngine 构造失败: {e}")
        return

    # ============================================================
    # 2. analyze() → SingleReport
    # ============================================================
    print("\n[2] analyze() → SingleReport")
    try:
        report = engine.analyze(RUN_ID)
        from ginkgo.trading.analysis.reports.single import SingleReport
        check(isinstance(report, SingleReport), "返回 SingleReport 实例")
        check(report.task_id == RUN_ID, f"task_id 正确: {report.task_id}")
    except Exception as e:
        check(False, f"analyze() 失败: {e}")
        report = None

    if report is None:
        print("\n❌ 无法继续，analyze() 失败")
        return

    # ============================================================
    # 3. analyzer_summary
    # ============================================================
    print("\n[3] analyzer_summary 验证")
    check(len(report.analyzer_summary) > 0, f"有 {len(report.analyzer_summary)} 个分析器: {list(report.analyzer_summary.keys())}")
    check("net_value" in report.analyzer_summary, "包含 net_value 分析器")

    nv_stats = report.analyzer_summary.get("net_value", {})
    check("final" in nv_stats, f"net_value.final = {nv_stats.get('final', 'N/A')}")
    check("mean" in nv_stats, f"net_value.mean = {nv_stats.get('mean', 'N/A')}")
    check("std" in nv_stats, f"net_value.std = {nv_stats.get('std', 'N/A')}")
    check("min" in nv_stats, f"net_value.min = {nv_stats.get('min', 'N/A')}")
    check("max" in nv_stats, f"net_value.max = {nv_stats.get('max', 'N/A')}")
    check(isinstance(nv_stats.get("final"), float), "final 值为 float 类型")
    check(nv_stats.get("final", 0) > 0, f"final 值 > 0: {nv_stats.get('final')}")

    # summary 别名
    check(report.summary is report.analyzer_summary, "summary 是 analyzer_summary 的别名")

    # ============================================================
    # 4. stability_analysis + ic_analysis
    # ============================================================
    print("\n[4] stability_analysis + ic_analysis 验证")
    check(len(report.stability_analysis) > 0, f"有 {len(report.stability_analysis)} 个稳定性指标")
    stability_names = list(report.stability_analysis.keys())[:5]
    check(any("rolling_mean" in n for n in stability_names), f"包含 rolling_mean 指标: {stability_names}")
    check(any("rolling_std" in n for n in stability_names), f"包含 rolling_std 指标")

    if len(report.analyzer_summary) > 1:
        non_nv = [n for n in report.analyzer_summary if n != "net_value"]
        if non_nv:
            check(len(report.ic_analysis) > 0, f"有 {len(report.ic_analysis)} 个 IC 指标")
            ic_names = list(report.ic_analysis.keys())[:3]
            check(any("ic." in n for n in ic_names), f"IC 指标格式正确: {ic_names}")
    else:
        print("  ⏭️  仅有 net_value 一个分析器，跳过 IC 验证")

    # ============================================================
    # 5. signal / order / position
    # ============================================================
    print("\n[5] signal / order / position 验证")
    check(isinstance(report.signal_analysis, dict), f"signal_analysis 是 dict: {report.signal_analysis}")
    check(isinstance(report.order_analysis, dict), f"order_analysis 是 dict: {report.order_analysis}")
    check(isinstance(report.position_analysis, dict), f"position_analysis 是 dict: {report.position_analysis}")

    # ============================================================
    # 6. SingleReport 输出
    # ============================================================
    print("\n[6] SingleReport 输出适配")

    d = report.to_dict()
    check(d["task_id"] == RUN_ID, "to_dict() 包含正确 task_id")
    check("analyzer_summary" in d, "to_dict() 包含 analyzer_summary")
    check("stability_analysis" in d, "to_dict() 包含 stability_analysis")
    check("ic_analysis" in d, "to_dict() 包含 ic_analysis")
    check("signal_analysis" in d, "to_dict() 包含 signal_analysis")
    check("time_series" in d, "to_dict() 包含 time_series")
    check(d.get("report_type") == "single", "to_dict() 包含 report_type=single")

    df = report.to_dataframe()
    check(not df.empty, f"to_dataframe() 非空: {df.shape}")
    check("section" in df.columns, "to_dataframe() 包含 section 列")
    check("value" in df.columns, "to_dataframe() 包含 value 列")

    table = report.to_rich()
    check(table.title is not None, "to_rich() 返回 Rich Table")
    print(f"  📋 Rich Table 标题: {table.title}")

    # ============================================================
    # 7. compare()
    # ============================================================
    print("\n[7] compare() → ComparisonReport")
    try:
        comp = engine.compare(task_ids=[RUN_ID])
        from ginkgo.trading.analysis.reports.comparison import ComparisonReport
        check(isinstance(comp, ComparisonReport), "返回 ComparisonReport 实例")
        check(len(comp.reports) == 1, "包含 1 个 report")

        comp_d = comp.to_dict()
        check(RUN_ID in comp_d, f"to_dict() 包含 task_id key: {RUN_ID}")
        check("analyzer_summary" in comp_d[RUN_ID], "对比报告包含 analyzer_summary")

        comp_df = comp.to_dataframe()
        check(not comp_df.empty, f"对比 DataFrame 非空: {comp_df.shape}")

        comp_table = comp.to_rich()
        check(comp_table is not None, "对比 Rich Table 正常生成")
    except Exception as e:
        check(False, f"compare() 失败: {e}")

    # ============================================================
    # 8. rolling()
    # ============================================================
    print("\n[8] rolling() → RollingReport")
    try:
        rolling = engine.rolling(RUN_ID, window=10, step=1)
        from ginkgo.trading.analysis.reports.rolling import RollingReport
        check(isinstance(rolling, RollingReport), "返回 RollingReport 实例")
        check(rolling.window == 10, f"window=10")
        check(rolling.step == 1, f"step=1")

        r_d = rolling.to_dict()
        check(len(r_d) > 0, f"有 {len(r_d)} 个滚动窗口")

        first_date = list(r_d.keys())[0]
        check("net_value" in r_d[first_date], f"第一个窗口包含 net_value: {first_date}")
        nv_window = r_d[first_date]["net_value"]
        check("mean" in nv_window, f"窗口统计包含 mean: {nv_window.get('mean', 'N/A')}")
        check("std" in nv_window, f"窗口统计包含 std: {nv_window.get('std', 'N/A')}")
        check("final" in nv_window, f"窗口统计包含 final: {nv_window.get('final', 'N/A')}")

        r_df = rolling.to_dataframe()
        check(not r_df.empty, f"滚动 DataFrame 非空: {r_df.shape}")
        check(r_df.index.name == "window_start", f"index name = window_start")
        check("net_value.mean" in r_df.columns, "包含 net_value.mean 列")

        r_table = rolling.to_rich()
        check(r_table is not None, "滚动 Rich Table 正常生成")

        # analyzers 过滤
        filtered = engine.rolling(RUN_ID, window=10, analyzers=["net_value"])
        f_d = filtered.to_dict()
        first_metrics = list(f_d.values())[0]
        check("net_value" in first_metrics, "analyzers 过滤后只包含指定分析器")
    except Exception as e:
        check(False, f"rolling() 失败: {e}")

    # ============================================================
    # 9. time_segments()
    # ============================================================
    print("\n[9] time_segments() → SegmentReport")
    try:
        seg = engine.time_segments(RUN_ID, freq="M")
        from ginkgo.trading.analysis.reports.segment import SegmentReport
        check(isinstance(seg, SegmentReport), "返回 SegmentReport 实例")
        check(seg.freq == "M", f"freq=M")

        s_d = seg.to_dict()
        check(len(s_d) > 0, f"有 {len(s_d)} 个时间段")

        first_seg = list(s_d.keys())[0]
        check("net_value" in s_d[first_seg], f"第一个分段包含 net_value: {first_seg}")
        nv_seg = s_d[first_seg]["net_value"]
        check("mean" in nv_seg, f"分段统计包含 mean: {nv_seg.get('mean', 'N/A')}")

        s_df = seg.to_dataframe()
        check(not s_df.empty, f"分段 DataFrame 非空: {s_df.shape}")
        check(s_df.index.name == "segment", f"index name = segment")
        check("net_value.mean" in s_df.columns, "包含 net_value.mean 列")

        s_table = seg.to_rich()
        check(s_table is not None, "分段 Rich Table 正常生成")

        # analyzers 过滤
        seg_filtered = engine.time_segments(RUN_ID, freq="M", analyzers=["net_value"])
        sf_d = seg_filtered.to_dict()
        first_metrics = list(sf_d.values())[0]
        check("net_value" in first_metrics, "analyzers 过滤后只包含指定分析器")
    except Exception as e:
        check(False, f"time_segments() 失败: {e}")

    # ============================================================
    # 10. 打印关键数据样例
    # ============================================================
    print("\n[10] 数据样例")
    print(f"  📊 分析器列表: {list(report.analyzer_summary.keys())}")
    print(f"  📊 net_value 统计: {report.analyzer_summary.get('net_value', {})}")
    if report.stability_analysis:
        print(f"  📊 稳定性指标数: {len(report.stability_analysis)}")
        for name in list(report.stability_analysis.keys())[:3]:
            print(f"    - {name}")
    if report.ic_analysis:
        print(f"  📊 IC 指标数: {len(report.ic_analysis)}")
        for name, val in list(report.ic_analysis.items())[:3]:
            print(f"    - {name}: {val}")

    r_d = rolling.to_dict()
    if r_d:
        last_date = list(r_d.keys())[-1]
        print(f"  📊 最后一个滚动窗口 ({last_date}): {r_d[last_date].get('net_value', {})}")

    s_d = seg.to_dict()
    if s_d:
        for seg_name, metrics in s_d.items():
            print(f"  📊 分段 [{seg_name}]: net_value mean={metrics.get('net_value', {}).get('mean', 'N/A')}")

    # ============================================================
    # 结果汇总
    # ============================================================
    print("\n" + "=" * 60)
    print(f"E2E 验证完成: ✅ {passed} passed, ❌ {failed} failed")
    if errors:
        print("\n失败项:")
        for e in errors:
            print(f"  ❌ {e}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
