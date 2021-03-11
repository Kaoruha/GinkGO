import 'package:flutter/material.dart';
import '../api/stock.dart';
import '../api/engine.dart';

class TestPage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Hello_Flutter',
      home: Scaffold(
        appBar: AppBar(title: Text('Ginkgo Test')),
        body: card,
      ),
    );
  }

  var card = new Card(
      child: Column(
    children: <Widget>[
      ListTile(
        title: Text(
          'Ginkgo Engine',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text('回测引擎相关控制'),
        leading: Icon(
          Icons.perm_camera_mic,
          color: Colors.lightBlue,
        ),
      ),
      Row(
        children: [
          RaisedButton(
            color: Colors.lightBlue[200],
            onPressed: () {
              engineBoost();
            },
            child: Text('引擎启动'),
          ),
        ],
      ),
      Divider()
    ],
  ));
}
