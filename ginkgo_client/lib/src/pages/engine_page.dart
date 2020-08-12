import 'package:flutter/material.dart';
import '../api/stock.dart';
import '../api/engine.dart';

class EnginePage extends StatelessWidget {
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
                engineBoost();
              },
              child: Text('引擎开启'),
            ),
            RaisedButton(
              color: Colors.lightBlue[200],
              onPressed: () {
                engineSleep();
              },
              child: Text('引擎休眠'),
            ),
            RaisedButton(
              color: Colors.lightBlue[300],
              onPressed: () {
                infoInjection();
              },
              child: Text('喂数据'),
            ),
            RaisedButton(
              color: Colors.lightBlue[100],
              onPressed: () {
                stockDataUpdate();
              },
              child: Text('数据更新'),
            ),
          ],
        ),
      ),
    );
  }
}
