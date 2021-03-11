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
          ],
        ),
      ),
    );
  }
}
