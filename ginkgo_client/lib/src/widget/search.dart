import 'package:flutter/material.dart';
import 'dart:ui';

class SearchBar extends StatefulWidget {
  SearchBar({Key key, this.callback}) : super(key: key);
  final callback;
  @override
  State<StatefulWidget> createState() => new _SearchBarState();
}

class _SearchBarState extends State<SearchBar> {
  final controller = TextEditingController();

  @override
  void initState() {
    super.initState();
  }

  void tellFatherWidget(String filter) {
    widget.callback(filter);
  }

  Widget build(BuildContext context) {
    return Container(
      child: Padding(
        padding: EdgeInsets.only(
          top: MediaQueryData.fromWindow(window).padding.top,
        ),
        child: Container(
          height: 52.0,
          child: new Padding(
              padding: const EdgeInsets.all(0.0),
              child: new Card(
                  child: new Container(
                child: new Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: <Widget>[
                    SizedBox(
                      width: 5.0,
                    ),
                    Icon(
                      Icons.search,
                      color: Colors.grey,
                    ),
                    Expanded(
                      child: Container(
                        height: 52.0,
                        alignment: Alignment.center,
                        child: TextField(
                          controller: controller,
                          onChanged: (value) {
                            tellFatherWidget(value);
                          },
                          decoration: InputDecoration(
                              contentPadding: EdgeInsets.only(top: 0.0),
                              hintText: 'Search',
                              focusColor: Color.fromARGB(255, 0, 0, 245),
                              hoverColor: Color.fromARGB(255, 0, 0, 245),
                              border: InputBorder.none),
                          style: TextStyle(
                            fontSize: 16,
                          ),
                          // onChanged: onSearchTextChanged,
                        ),
                      ),
                    ),
                    new IconButton(
                      icon: new Icon(Icons.cancel),
                      color: Colors.grey,
                      iconSize: 18.0,
                      onPressed: () {
                        controller.clear();
                        // onSearchTextChanged('');
                      },
                    ),
                  ],
                ),
              ))),
        ),
      ),
    );
  }
}
