from src.data.ginkgo_mongo import ginkgo_mongo as gm


def remove_index():
    ban_str = [
        "指数",
        "上证",
        "等权",
        "基本",
        "债",
        "全指",
        "周期",
        "消费",
        "分层",
        "投资品",
        "产业",
        "成长",
        "可选",
        "沪财",
        "全R价值",
        "高端装备",
        "资源50",
        "国证大宗商品",
        "中正",
        "800",
        "380",
        "300",
        "500",
        "180",
        "主题",
        "A股",
        "食品饮料",
        "医药生物",
        "细分医药",
        "细分地产",
        "有色金属",
        "智能资产",
        "380",
        "有色金属",
        "大宗商品",
        "资源优势",
        "银河99",
    ]
    filter_list = []
    stock_list = gm.get_all_stockcode_by_mongo()
    for i, r in stock_list.iterrows():
        for s in ban_str:
            if s in r["code_name"]:
                if r["code_name"] not in filter_list:
                    filter_list.append(r["code"])

    df2 = stock_list[~stock_list["code"].isin(filter_list)]

    return df2
