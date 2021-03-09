import 'package:flutter/material.dart';
import 'package:ginkgo_client/src/pages/market.dart' show Market;
import 'package:ginkgo_client/src/pages/portfolio.dart' show Portfolio;
import 'package:ginkgo_client/src/pages/strategy.dart' show Strategy;
import 'package:ginkgo_client/src/pages/backtest.dart' show BackTest;
import 'package:ginkgo_client/src/pages/user.dart' show User;

void main() => runApp(MyApp());

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Ginkgo',
      home: Homes(),
      theme: ThemeData(primaryColor: Colors.blue[800]),
    );
  }
}

class Homes extends StatefulWidget {
  @override
  State<StatefulWidget> createState() {
    return _HomesState();
  }
}

class _HomesState extends State<Homes> {
  int _currentIndex = 0;
  final List<Widget> _children = [
    Market(),
    Portfolio(),
    BackTest(),
    Strategy(),
    User()
  ];

  final List<BottomNavigationBarItem> _list = <BottomNavigationBarItem>[
    BottomNavigationBarItem(
      icon: Icon(Icons.show_chart),
      title: Text('Market'),
      // backgroundColor: Colors.orange
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.account_balance_wallet),
      title: Text('Portfolio'),
      //backgroundColor: Colors.orange
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.text_snippet),
      title: Text('Backtest'),
      //backgroundColor: Colors.orange
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.handyman),
      title: Text('Strategy'),
      //backgroundColor: Colors.orange
    ),
    BottomNavigationBarItem(
      icon: Icon(Icons.face),
      title: Text('User'),
      //backgroundColor: Colors.orange
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Center(child: Text('Ginkgo')),
      ),
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        onTap: onTabTapped,
        currentIndex: _currentIndex,
        items: _list,
      ),
      body: _children[_currentIndex],
    );
  }

  void onTabTapped(int index) {
    setState(() {
      _currentIndex = index;
    });
  }
}
