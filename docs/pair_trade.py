"""
基于统计套利的配对交易
"""
import contextlib
import matplotlib.pyplot as plt
from src.backtest.strategy.base_strategy import BaseStrategy
from src.data.ginkgo_mongo import ginkgo_mongo as gm
from src.util.stock_filter import remove_index
from scipy.stats import spearmanr


class PairTradeStrategy(BaseStrategy):
    def __init__(self, name="配对交易策略"):
        super().__init__(name=name)
        self.sample_start_date = '2021-01-01'
        self.sample_end_date = '2021-04-01'
        self.pair = []
        self.pair_count = 1
        self.relation_rate = 0.2
        self.p_standard = 0.05

    def get_high_relationship_codes(self):
        self.pair = []
        code_list = remove_index()
        total = len(code_list) * len(code_list)
        process = 0
        for code1 in code_list["code"]:
            for code2 in code_list["code"]:
                # print(f"{round((process/total*100),3)}%")
                process += 1
                if code1 == code2:
                    continue
                try:
                    df1 = gm.get_dayBar_by_mongo(code=code1, start_date=self.sample_start_date, end_date=self.sample_end_date)["close"]
                    df2 = gm.get_dayBar_by_mongo(code=code2, start_date=self.sample_start_date, end_date=self.sample_end_date)["close"]
                    correlation, p_value = spearmanr(a=df1, b=df2)
                except Exception as e:
                    print(e)
                    p_value = 0
                # if p_value <= self.p_standard:
                #     # print(f"{code1}与{code2}相关性不显著")
                #     continue
                print(correlation)
                if abs(correlation) >= self.relation_rate:
                    new_pair = (code1, code2)
                    self.pair.append(new_pair)
                    print(f'已经找到{len(self.pair)}对')
                    if len(self.pair) < self.pair_count:
                        continue
                    else:
                        break
                # print(f"{code1}与{code2}相关性不高")
            else:
                continue
            break

    def price_analyzation(self,df1,df2):
        plt.scatter(df1["date"],df1["close"])
        plt.scatter(df2["date"],df2["close"])
        plt.show()

    def gap_analyzation(self,df1,df2):
        # TODO 检验序列平稳性
        # TODO Learn about 协整关系
        df1['close'] = df1['close'].astype('float')
        df2['close'] = df2['close'].astype('float')
        df = df1["close"] - df2['close']
        mean = df.mean()
        std = df.std()
        plt.plot(df1["date"],df)
        plt.axhline(y=mean, c='g', ls='--', lw=2)
        plt.axhline(y=mean+std, c='b', ls='--', lw=2)
        plt.axhline(y=mean-std, c='r', ls='--', lw=2)
        plt.show()


if __name__ == "__main__":
    pt = PairTradeStrategy()
    pt.get_high_relationship_codes()
    print(pt.pair)
    for i in pt.pair:
        c1 = i[0]
        c2 = i[1]
        df1 = gm.get_dayBar_by_mongo(code=c1, start_date=pt.sample_start_date, end_date=pt.sample_end_date)
        df2 = gm.get_dayBar_by_mongo(code=c2, start_date=pt.sample_start_date, end_date=pt.sample_end_date)
        # pt.price_analyzation(df1,df2)
        pt.gap_analyzation(df1,df2)