import 'package:flutter/material.dart';

class MarketFutures extends StatelessWidget{
  @override
  Widget build(BuildContext context){
    return new Container(
      margin:const EdgeInsets.all(4.0),
      child: new Row(
        mainAxisAlignment: MainAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Expanded(
            flex: 2,
            child: new Column(
              children: [
                Container(
                  height: 200,
                  color: const Color(0xAA2DBD3A),
                )
              ],
            )
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
            )
          ),
        ]
      ),
    );
  }
}