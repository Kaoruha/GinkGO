import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:ginkgo_client/src/api/stock.dart';

GlobalKey<_StockListState> stock_list_key = GlobalKey();

class StockList extends StatefulWidget {
  StockList({Key key, this.callback}) : super(key: key);
  final callback;

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
  List stockData = [];
  void tellFatherWidget(String code) {
    widget.callback(code);
  }

  // 从服务端获取股票代码
  void getStockData() async {
    // todo 发起API请求，解析Json，存入rawData

    var stock_list = await getStockList();
    print('获取StockList');
    if (stock_list == null) {
      return;
    }
    setState(() {
      rawData.clear();
      stockData.clear();
      List list = stock_list['data'];
      list.forEach((element) {
        var stock = {};
        stock['code'] = element['code'];
        stock['name'] = element['name'];
        rawData.add(stock);
        stockData.add(stock);
      });
    });
  }

  // 根据filter字段筛选
  void stock_filter(String filter) {
    // 根据widget.filter 重新确定stockData里的数据
    stockData.clear();
    rawData.forEach((element) {
      bool in_code = element['code'].toString().contains(filter);
      bool in_name = element['name'].toString().contains(filter);
      // print('$in_code $in_name');
      if (in_code || in_name) {
        stockData.add(element);
      }
    });
    print('RAW: $rawData');
    print('SHOW: $stockData');
    setState(() {});
    // print('显示数据：$stockData');
  }

  // List<Widget> _StockList() {
  //   var list = stockData.map((value) {
  //     return ListTile(
  //       leading: Icon(Icons.poll),
  //       title: Text(value["code"]),
  //       subtitle: Text(value["name"]),
  //       trailing: Icon(Icons.keyboard_arrow_right),
  //       onTap: () => {tellFatherWidget(value["code"])},
  //     );
  //   });
  //   return list.toList();
  // }

  @override
  void initState() {
    super.initState();
    getStockData();
  }

  // ListItem 构建方法
  Widget _StockListItem(BuildContext context, int index) {
    Map item = stockData[index];
    return ListTile(
      leading: Icon(Icons.poll),
      title: Text(item["code"]),
      subtitle: Text(item["name"]),
      trailing: Icon(Icons.keyboard_arrow_right),
      onTap: () => {tellFatherWidget(item["code"])},
    );
  }

  // Widget build(BuildContext context) {
  //   return SizedBox(
  //     height: 500,
  //     child: ListView.builder(
  //       itemCount: stockData.length,
  //       itemBuilder: _StockListItem,
  //     ),
  //   );
  // }

  Widget build(BuildContext context) {
    return SizedBox(
        height: 800,
        child: Scrollbar(
          radius: Radius.circular(10),
          thickness: 10,
          child: ListView.builder(
            itemCount: stockData.length,
            itemBuilder: _StockListItem,
          ),
        ));
  }
}

class _StockItem {
  _StockItem(this.code, this.name);

  final String code;
  final String name;
}
