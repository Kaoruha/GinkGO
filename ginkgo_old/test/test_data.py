from ginkgo.data.data_portal import data_portal

def update_all_data():
    data_portal.get_stock_code()
    data_portal.update_adjust()
    data_portal.update_all_stock()
