from ginkgo.data.ginkgo_data import GDATA
import pandas as pd
import numpy as np

day_count_long = 30
day_count_short = 5

stock_infos = GDATA.get_stock_info_df()

# stock_infos = stock_infos[:1]

rs = pd.DataFrame()

for i, r in stock_infos.iterrows():
    code = r.code
    name = r.code_name
    print(f"{code} : {name}")

    try:
        raw = GDATA.get_daybar_df(code)
    except Exception as e:
        continue
    if raw.shape[0] == 0:
        continue

    # long
    daybar = raw.tail(day_count_long).copy()
    avg = np.average(daybar["volume"].values)
    daybar["volume"] = daybar["volume"] / avg
    volumes = daybar["volume"].values
    std_long = np.std(volumes)

    # short
    daybar2 = raw.tail(day_count_short).copy()
    avg2 = np.average(daybar2["volume"].values)
    daybar2["volume"] = daybar2["volume"] / avg2
    volumes2 = daybar2["volume"].values
    std_short = np.std(volumes2)

    title_long = f"{day_count_long} std"
    title_short = f"{day_count_short} std"
    std_avg = (std_long * 0.3 + std_short * 0.7) / 2
    item = pd.DataFrame(
        {
            "code": [code],
            "name": name,
            "std_score": std_avg,
            title_long: [std_long],
            title_short: [std_short],
        }
    )
    rs = pd.concat([rs, item])
    rs = rs.sort_values("std_score", ascending=True)
    rs = rs.reset_index(drop=True)
    print(rs)
