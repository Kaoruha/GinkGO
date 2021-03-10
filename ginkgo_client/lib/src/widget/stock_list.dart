import 'package:flutter/material.dart';
import 'package:ginkgo_client/src/api/stock.dart';

class StockList extends StatefulWidget {
  StockList({Key key, this.callback, this.filter}) : super(key: key);
  final callback;
  String filter;

  @override
  State<StatefulWidget> createState() => new _StockListState();
}

class _StockListState extends State<StockList> {
  List rawData = [
    {
      "code": "sh.000001",
      "name": "name1",
    },
    {
      "code": "sh.000002",
      "name": "name12",
    },
    {
      "code": "sh.000003",
      "name": "name13",
    },
    {
      "code": "sh.000001",
      "name": "name1",
    },
    {
      "code": "sh.000002",
      "name": "name12",
    },
    {
      "code": "sh.000003",
      "name": "name13",
    },
    {
      "code": "sh.000001",
      "name": "name1",
    },
    {
      "code": "sh.000002",
      "name": "name12",
    },
    {
      "code": "sh.000003",
      "name": "name13",
    },
    {
      "code": "sh.000001",
      "name": "name1",
    },
    {
      "code": "sh.000002",
      "name": "name12",
    },
    {
      "code": "sh.000003",
      "name": "name13",
    },
    {
      "code": "sh.000001",
      "name": "name1",
    },
    {
      "code": "sh.000002",
      "name": "name12",
    },
    {
      "code": "sh.000003",
      "name": "name13",
    },
    {
      "code": "sh.000001",
      "name": "name1",
    },
    {
      "code": "sh.000002",
      "name": "name12",
    },
    {
      "code": "sh.000003",
      "name": "name13",
    },
    {
      "code": "sh.000001",
      "name": "name1",
    },
    {
      "code": "sh.000002",
      "name": "name12",
    },
    {
      "code": "sh.000003",
      "name": "name13",
    },
  ];

  void tellFatherWidget(String code) {
    widget.callback(code);
    getStockData();
  }

  void getStockData() {
    // todo 发起API请求，解析Json，存入rawData
    print('假装获取了StockInfoList');
    getStockList();
    print('假装存入了rawData');
  }

  List<Widget> _StockList() {
    var list = rawData.map((value) {
      return ListTile(
        leading: Icon(Icons.poll),
        title: Text(value["code"]),
        subtitle: Text(value["name"]),
        trailing: Icon(Icons.keyboard_arrow_right),
        onTap: () => {tellFatherWidget(value["code"])},
      );
    });
    return list.toList();
  }

  @override
  void initState() {
    super.initState();
    getStockData();
  }

  Widget build(BuildContext context) {
    ScrollController controller = new ScrollController();

    return SizedBox(
      height: 500,
      child: ListView(
        children: this._StockList(),
      ),
    );
  }
}

class _StockItem {
  _StockItem(this.code, this.name);

  final String code;
  final String name;
}
