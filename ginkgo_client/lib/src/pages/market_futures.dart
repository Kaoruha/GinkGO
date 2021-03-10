import 'package:flutter/material.dart';
import 'package:ginkgo_client/src/widget/search.dart' show SearchBar;
import 'package:ginkgo_client/src/widget/stock_list.dart' show StockList;

class MarketFutures extends StatefulWidget {
  @override
  _MarketFuturesStates createState() => _MarketFuturesStates();
}

class _MarketFuturesStates extends State<MarketFutures> {
  String currentStock = '';
  String stockFilter = '';
  void onListClick(val) {
    setState(() {
      currentStock = val;
    });
    print(currentStock + ' clicked');
  }

  void onFilterChange(val) {
    setState(() {
      stockFilter = val;
    });
    print('Filter: ' + stockFilter);
  }

  @override
  Widget build(BuildContext context) {
    return new Container(
      margin: const EdgeInsets.all(4.0),
      child: new Row(
          mainAxisAlignment: MainAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Expanded(
              flex: 2,
              child: new Column(
                children: [
                  SearchBar(callback: (val) => onFilterChange(val)),
                  StockList(
                    callback: (val) => onListClick(val),
                    filter: stockFilter,
                  )
                ],
              ),
            ),
            Expanded(
                flex: 8,
                child: new Column(
                  children: [
                    Container(
                      height: 80,
                      color: const Color(0xFF2DBD3A),
                    )
                  ],
                )),
          ]),
    );
  }
}
