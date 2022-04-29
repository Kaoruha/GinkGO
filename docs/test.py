# from os import replace
# import pandas as pd

# column_name = ['rate', 'signal_day', 'signal_count', 'observe_1', 'profit_1','observe_', 'profit_2','observe_3', 'profit_3']
# locate = {
#     "rate" : 1,
#     "signal_day":2
# }


# locate2 = {
#     "rate" : 2,
#     "signal_day":2
# }
# for i in range(3):
#     locate['observe_' + str(i+1)] = i + 1
# df_raw = pd.DataFrame(columns=column_name)

# df_raw = df_raw.append(locate, ignore_index=True).fillna(0)
# df_raw = df_raw.append(locate, ignore_index=True).fillna(0)

# df_raw = df_raw.append(locate2, ignore_index=True).fillna(0)

# def ab(df):
#     return df.sum()

# df = pd.read_csv("./docs/volume_research.csv", index_col=0)
# print(df)

# column_name2 = []
# for i in range(1):
#     column_name2.append("observe_" + str(i+1))
#     column_name2.append("profit_" + str(i+1))
# df = df_raw.groupby(["rate","signal_day"])[column_name2].apply(ab)
# df = df.reset_index()
# print(df)

