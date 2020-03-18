from flask import json
from app.data_acquisition.setting import DATA_URL
from app.models.stock import Stock


def json_read(file_name):
    records = []
    file_url = DATA_URL + file_name + '.json'
    with open(file_url, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            temp = json.loads(line)
            record = Stock.generate_record(
                code=file_name,
                timestamp=temp['timestamp'],
                mkt_value=temp['mkt_value'],
                value_change=temp['value_change'],
                volume=int(temp['volume'].replace(',', '')),
                amount=int(temp['amount'].replace(',', '')),
                buy_or_sale=temp['buy_or_sale']
            )
            records.append(record)
        Stock.add_records(records)
        # TODO 数据插入前需要查重

def test():
    json_read('sz000001')
