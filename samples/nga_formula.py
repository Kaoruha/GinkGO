'''
Author: your name
Date: 2021-12-08 14:01:38
LastEditTime: 2021-12-10 15:59:33
LastEditors: Please set LastEditors
Description: 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
FilePath: \GinkGO\examples\nga_formula.py
'''
import pandas as pd
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.util.stock_filter import remove_index
# 主板；
# 非ST；
# 今日最低价>5日均线；
# 今日涨停；
# 今日成交量/前10个交易日的日均成交量>0.7且<1.08；
# 5日均线价格/10日均线价格>1且<1.08；
# 非新股；

# 目前的行情，筛选出来之后别急着进，放2天，看节奏，看均线。
# 还有种玩法是等MA5下穿MA10之后回稳再入吃回弹甚至突破前高。这种比进节奏第二天就入更稳。

# stock_list = remove_index()[:1]
stock_list = remove_index()[:]
ma_list = [5,10]
result = pd.DataFrame()
for i,r in stock_list.iterrows():
    code = r['code']
    code_name  = r['code_name']
    df = gm.get_dayBar_by_mongo(code=code)
    print(code, code_name)
    length = df.shape[0]
    if length <= 30:
        continue

    pct_change = df.iloc[-1]['pct_change']

    if pct_change == '':
        continue
    if float(pct_change) <= 9.6:
        continue

    for ma in ma_list:
        ind = 'MA'+ str(ma)
        df[ind] = df['close'].rolling(ma, min_periods=1).mean()
    
    df['volume10'] = df['volume'].rolling(10, min_periods=1).mean()
    
    low = float(df.iloc[-1]['low'])
    ma5 = float(df.iloc[-1]['MA5'])
    ma10 = float(df.iloc[-1]['MA10'])
    volume = float(df.iloc[-1]['volume'])
    volume10 = float(df.iloc[-1]['volume10'])

    if low < ma5:
        continue

    if volume/volume10 < .7 or volume/volume10 > 1.08:
        continue

    if ma5/ma10 < 1 or ma5/ma10 > 1.08:
        continue

    result = result.join(df.iloc[-1])

# print(result)