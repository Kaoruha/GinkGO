from ginkgo.data.stock.baostock import bao_instance

if __name__ == '__main__':
    bao_instance.get_all_stock_code()
    bao_instance.all_adjust_factor_up_to_date()
    bao_instance.update_all_stock()