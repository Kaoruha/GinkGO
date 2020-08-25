from ginkgo.data.data_portal import data_portal

if __name__ == "__main__":
    df = data_portal.query_stock(code='sh.600522',
                                 start_date='2020-02-25',
                                 end_date='2020-02-25',
                                 frequency='d',
                                 adjust_flag=1)

    # print(df['open'])
    # print(df['close'])
    # print(df['close']/df['open']*100)
    print(df.columns)
    print(df['turn'].values)