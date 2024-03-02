from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs.ginkgo_conf import GCONF
import pandas as pd
import os

count = 3


def get_dayly_limit(dataframe):
    rs = []
    global count
    limit_count = 0
    for i, r in dataframe.iterrows():
        print(f"{r['code']}  {r['timestamp']}   {limit_count}")
        close = r["close"]
        open = r["open"]
        if (close - open) / open > 0.095:
            limit_count += 1
        else:
            limit_count = 0
        if limit_count >= count:
            rs.append(r["timestamp"])
            limit_count = 0
    return rs


code_list_df = GDATA.get_stock_info_df_cached()
for i, r in code_list_df.iterrows():
    code = r["code"]
    daybar = GDATA.get_daybar_df_cached(code)
    rs = get_dayly_limit(daybar)
    rs = daybar[daybar["timestamp"].isin(rs)]
    rs.to_csv(
        f"{GCONF.LOGGING_PATH}/endless_dayly_limit.csv",
        mode="a",
        header=False,
        index=False,
    )
