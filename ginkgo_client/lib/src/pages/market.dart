import 'package:flutter/material.dart';
import './market_ginkgo.dart' show MarketGinkgo;
import './market_cn.dart' show MarketCN;
import './market_us.dart' show MarketUS;
import './market_futures.dart' show MarketFutures;

class Market extends StatefulWidget {
  @override
  State<StatefulWidget> createState() => MarketState();
}

class MarketState extends State<Market> with SingleTickerProviderStateMixin {
  TabController tabController;

  @override
  void initState() {
    super.initState();
    tabController = TabController(length: 11, vsync: this);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TabBar(
          tabs: [
            Tab(
              text: "Ginkgo",
            ),
            Tab(
              text: "Future",
            ),
            Tab(
              text: "CN",
            ),
            Tab(
              text: "US",
            ),
            Tab(
              text: "SG",
            ),
            Tab(
              text: "JPN",
            ),
            Tab(
              text: "UK",
            ),
            Tab(
              text: "RUS",
            ),
            Tab(
              text: "IND",
            ),
            Tab(
              text: "AUS",
            ),
            Tab(
              text: "Others",
            ),
          ],
          controller: tabController,
          isScrollable:true,
          labelStyle:TextStyle(color: Colors.white),
          indicatorColor: Colors.white,
          indicatorSize: TabBarIndicatorSize.label,
        ),
      ),
      body: TabBarView(
        children: [
          MarketGinkgo(),
          MarketFutures(),
          MarketCN(),
          MarketUS(),
          Center(child: Text('新加坡')),
          Center(child: Text('日本')),
          Center(child: Text('英国')),
          Center(child: Text('俄罗斯')),
          Center(child: Text('印度')),
          Center(child: Text('澳大利亚')),
          Center(child: Text('其他')),
        ],
        controller: tabController,
      ),
    );
  }

  @override
  void dispose() {
    tabController.dispose();
    super.dispose();
  }
}
