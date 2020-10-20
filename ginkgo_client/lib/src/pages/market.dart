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
    tabController = TabController(length: 7, vsync: this);
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
              text: "CN",
            ),
            Tab(
              text: "US",
            ),
            Tab(
              text: "Future",
            ),
            Tab(
              text: "SG",
            ),
            Tab(
              text: "JPN",
            ),
            Tab(
              text: "Others",
            ),
          ],
          controller: tabController,
          isScrollable:true,
          labelStyle:TextStyle(color: Colors.white),
          indicatorColor: Colors.white,
        ),
      ),
      body: TabBarView(
        children: [
          MarketGinkgo(),
          MarketCN(),
          MarketUS(),
          MarketFutures(),
          Center(child: Text('新加坡')),
          Center(child: Text('日本')),
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
