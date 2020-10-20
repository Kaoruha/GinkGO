import 'package:flutter/material.dart';
// import 'asset.dart';


class SearchBarDemo extends StatefulWidget {
  _SearchBarDemoState createState() => _SearchBarDemoState();
}

class _SearchBarDemoState extends State<SearchBarDemo> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar:AppBar(
        title:Text('SearchBarDemo'),
        actions:<Widget>[
          IconButton(
            icon:Icon(Icons.search),
            onPressed: (){
               print('开始搜索');
            }
          ),
        ]
      )
    );
  }
}