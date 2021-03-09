import 'dart:io';
import 'dart:io';
import 'dart:async';
import 'package:web_socket_channel/html.dart';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/status.dart' as status;

class WebSocketManager{
  //私有
  WebSocketManager._();
  //静态
  static WebSocketManager _manager;
  //提供访问
  factory WebSocketManager(){
    if (_manager==null){
      _manager = new WebSocketManager._();
    }
    return _manager;
  }

  var channel;

  void initWebSocket(){
    String url = 'ws://127.0.0.1:8080/api/engine/sockets';
    print(url);
    
    // TODO 需要根据平台切换
    // if (Platform.isAndroid) {
    //   channel = IOWebSocketChannel.connect(url);
    // } else {
    //   channel = HtmlWebSocketChannel.connect(url);
    // }
    channel = HtmlWebSocketChannel.connect(url);
    channel.stream.listen((message) {
      handleMSG(message);
    });
  }

  void handleMSG(message){
    // TODO 处理 Message
    print(message);
  }

  void sendMSG(message){
      channel.sink.add(message);
  }

  void closeSocket(){
    channel.sink.close(status.normalClosure); 
  }

  void heartBeat(){
    // TODO 心跳回忆
  }

}
