import 'package:flutter/material.dart';
import '../api/stock.dart';
// import '../api/test.dart';
import '../api/engine.dart';

class TestPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hello_Flutter',
      home: Scaffold(
        appBar: AppBar(title: Text('Ginkgo Test')),
        body: Row(
          children: <Widget>[
            RaisedButton(
              color: Colors.lightBlue[200],
              onPressed: () {
                EngineRun();
              },
              child: Text('引擎开启'),
            ),
            RaisedButton(
              color: Colors.lightBlue[200],
              onPressed: () {
                EngineSleep();
              },
              child: Text('引擎休眠'),
            ),
            RaisedButton(
              color: Colors.lightBlue[300],
              onPressed: () {
                // DataFeed();
              },
              child: Text('喂数据'),
            ),
            RaisedButton(
              color: Colors.lightBlue[100],
              onPressed: () {
                StockDataUpdate();
              },
              child: Text('数据更新'),
            ),
          ],
        ),
      ),
    );
  }
}
