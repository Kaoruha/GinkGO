import 'package:flutter/material.dart';
import 'package:ginkgo_client/src/api/test.dart';
import 'package:ginkgo_client/src/utils/socket.dart';
import 'package:ginkgo_client/src/widget/line_chart.dart';

class BackTest extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return new Container(
        width: double.infinity,
        height: double.infinity,
        color: Colors.red,
        child: new Column(children: <Widget>[
          Container(
            height: 80,
            color: Colors.orange,
            child: Row(
              children: [
                Expanded(
                  flex: 3,
                  child: RaisedButton(
                      color: Colors.blue,
                      highlightColor: Colors.blue[700],
                      colorBrightness: Brightness.dark,
                      splashColor: Colors.grey,
                      child: Text("API Test"),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(4.0)),
                      onPressed: () {
                        justForTest();
                      }),
                ),
                Expanded(flex: 7, child: Container())
              ],
            ),
          ),
          LineChartSample2()
        ]));
  }
}
