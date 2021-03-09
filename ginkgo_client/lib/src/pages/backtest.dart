import 'package:flutter/material.dart';
import 'package:ginkgo_client/src/api/test.dart';
import 'package:ginkgo_client/src/utils/socket.dart';
import 'package:ginkgo_client/src/widget/line_chart.dart';


class BackTest extends StatelessWidget{
  @override
  Widget build(BuildContext context){
    return new Center(
      child: new Column(
        children: <Widget>[
          // RaisedButton(
          //   color: Colors.blue,
          //   highlightColor: Colors.blue[700],
          //   colorBrightness: Brightness.dark,
          //   splashColor: Colors.grey,
          //   child: Text("API Test"),
          //   shape:
          //       RoundedRectangleBorder(borderRadius: BorderRadius.circular(20.0)),
          //   onPressed: () {
          //     justForTest();
          //   }
          // ),
          // RaisedButton(
          //   color: Colors.blue,
          //   highlightColor: Colors.blue[700],
          //   colorBrightness: Brightness.dark,
          //   splashColor: Colors.grey,
          //   child: Text("Init Socket"),
          //   shape:
          //       RoundedRectangleBorder(borderRadius: BorderRadius.circular(20.0)),
          //   onPressed: () {
          //     WebSocketManager().initWebSocket();
          //   }
          // ),
          // RaisedButton(
          //   color: Colors.blue,
          //   highlightColor: Colors.blue[700],
          //   colorBrightness: Brightness.dark,
          //   splashColor: Colors.grey,
          //   child: Text("Send MSG"),
          //   shape:
          //       RoundedRectangleBorder(borderRadius: BorderRadius.circular(20.0)),
          //   onPressed: () {
          //     WebSocketManager().sendMSG('fuck me');
          //   }
          // ),
          // RaisedButton(
          //   color: Colors.blue,
          //   highlightColor: Colors.blue[700],
          //   colorBrightness: Brightness.dark,
          //   splashColor: Colors.grey,
          //   child: Text("Close Socket"),
          //   shape:
          //       RoundedRectangleBorder(borderRadius: BorderRadius.circular(20.0)),
          //   onPressed: () {
          //     WebSocketManager().closeSocket();
          //   }
          // ),
          LineChart()
        ]
        )
      
      
    );
  }
}