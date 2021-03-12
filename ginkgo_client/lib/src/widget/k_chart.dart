import 'package:flutter/material.dart';
import 'dart:ui';

class KChart extends StatefulWidget {
  KChart({Key key, this.callback}) : super(key: key);
  final callback;
  @override
  State<StatefulWidget> createState() => new _KChartState();
}

class _KChartState extends State<KChart> {
  String code = '';
  @override
  void initState() {
    super.initState();
  }

  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          height: 180,
          width: double.infinity,
          color: Colors.red,
        ),
        Container(
          width: double.infinity,
          color: Colors.orange,
        ),
      ],
    );
  }
}
