from ginkgo.data import get_stockinfos, get_bars
import pandas as pd
import datetime

infos = get_stockinfos()
now = datetime.datetime.today()
date_end = now + datetime.timedelta(days=-1)
last_n_days = 90
date_start = date_end + datetime.timedelta(days=-last_n_days)
result = pd.DataFrame()
for i, r in infos.iterrows():
    code = r["code"]
    name = r["code_name"]
    print(f"{i}/{infos.shape[0]}: {code} {name}")
    today_df = get_bars(code=code, start_date=now + datetime.timedelta(days=-1), end_date=now, as_dataframe=True)
    if today_df.shape[0] == 0:
        continue
    close = today_df["close"].values[0]
    open = today_df["open"].values[0]
    pct = close / open - 1
    if pct > 0.095:
        continue
    history_df = get_bars(code=code, start_date=date_start, end_date=date_end, as_dataframe=True)
    if history_df.shape[0] <= 0.5 * last_n_days:
        continue
    ma = history_df["volume"].mean()
    history_df['volume'] = history_df['volume'] / ma
    std = history_df['volume'].std()
    cv = std / ma
    cv_abs = abs(cv)
    ratio = 0
    today_volume = history_df.iloc[-1]["volume"]
    print(f"{code} Today Volume: {today_volume}")
    try:
        ratio = today_volume
    except Exception as e:
        print(e)
    finally:
        pass
    if cv > 1:
        continue
    alpha = 0.6
    beta = 0.4
    score = 1 / std * alpha + ratio * beta
    data = {"code": code, "name": name, "ma": ma, "today_volume": today_volume, "ratio": ratio, "std":std, "cv":cv_abs,"score":score}
    result = pd.concat([result, pd.DataFrame([data])], ignore_index=True)
    print(result)

result = result.sort_values(by="ratio", ascending=False)
result = result.reset_index(drop=True)
print(result.head(5))
