import sys
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.backtest.plots import CandlePlot

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(
            "\033[94m"
            + "Usage: python ./daybar_candle.py 000021.SZ 20200101 20200201"
            + "\033[0m"
        )
        sys.exit()

    code = sys.argv[1]
    date_start = sys.argv[2]
    date_end = sys.argv[3]
    info = GDATA.get_stock_info(code)
    code_name = info.code_name
    industry = info.industry
    df = GDATA.get_daybar_df(code, date_start, date_end)
    plt = CandlePlot(f"[{industry}] {code} {code_name}")
    plt.figure_init()
    plt.update_data(df)
    plt.show()
