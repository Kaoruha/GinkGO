import 'package:flutter/material.dart';
import 'package:syncfusion_flutter_charts/charts.dart';


class LineChart extends StatefulWidget {
  @override
  _LineChartState createState() => new _LineChartState();
}

class _LineChartState extends State<LineChart> {
  @override
  Widget build(BuildContext context) {
    return new Container(
      height: 80,
      color: const Color(0xFF2DBD3A)
    );
  }
}

class SalesData {
  SalesData(this.year, this.sales);
  final String year;
  final double sales;
}
