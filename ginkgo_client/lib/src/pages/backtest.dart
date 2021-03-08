import 'package:flutter/material.dart';
import 'package:ginkgo_client/src/api/test.dart';
import 'package:ginkgo_client/src/utils/socket.dart';

import '../utils/socket.dart';


class BackTest extends StatelessWidget{
  @override
  Widget build(BuildContext context){
    return new Center(
      child: RaisedButton(
        color: Colors.blue,
        highlightColor: Colors.blue[700],
        colorBrightness: Brightness.dark,
        splashColor: Colors.grey,
        child: Text("Connect Test"),
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(20.0)),
        onPressed: () {
          WebSocketManager().initWebSocket();
          WebSocketManager().sendMSG();
          },
      ),
      
    );
  }
}