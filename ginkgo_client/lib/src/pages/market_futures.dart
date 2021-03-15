import 'package:flutter/material.dart';
import 'package:ginkgo_client/src/widget/search.dart' show SearchBar;
import 'package:ginkgo_client/src/widget/stock_list.dart';
import 'package:ginkgo_client/src/widget/k_chart.dart';

class MarketFutures extends StatefulWidget {
  @override
  _MarketFuturesStates createState() => _MarketFuturesStates();
}

class _MarketFuturesStates extends State<MarketFutures> {
  String currentStock = '';
  String stockFilter = '';
  int stockNum = 0;
  void onListClick(val) {
    setState(() {
      currentStock = val;
    });
    print(currentStock + ' clicked');
  }

  void onListChange(int count) {
    setState(() {
      stockNum = count;
    });
  }

  void onFilterChange(val) {
    setState(() {
      stockFilter = val;
    });
    print('Future: ' + stockFilter);
    stockListKey.currentState.stock_filter(stockFilter);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      height: double.infinity,
      color: Color.fromARGB(255, 243, 243, 243),
      margin: const EdgeInsets.all(4.0),
      child: Row(
          mainAxisAlignment: MainAxisAlignment.start,
          mainAxisSize: MainAxisSize.max,
          children: <Widget>[
            Expanded(
              flex: 2,
              child: Column(
                children: [
                  SearchBar(callback: (val) => onFilterChange(val)),
                  Container(
                    width: double.infinity,
                    padding: EdgeInsets.only(left: 19),
                    child: Text(
                      '$stockNum ',
                      textAlign: TextAlign.left,
                      style: TextStyle(color: Colors.grey[400]),
                    ),
                  ),
                  StockList(
                    key: stockListKey,
                    list_item_click: (val) => onListClick(val),
                    list_change: (val) => onListChange(val),
                  )
                ],
              ),
            ),
            Expanded(flex: 8, child: KChart()),
          ]),
    );
  }
}
