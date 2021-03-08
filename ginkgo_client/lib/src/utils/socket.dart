import 'dart:io';
import 'dart:async';

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

  WebSocket _webSocket;

  void initWebSocket(){
    String path = 'ws://127.0.0.1:8080/api/engine/sockets';
    print(path);
    Future<WebSocket> future = WebSocket.connect(path);
    future.then((webSocket){
      _webSocket = webSocket;
      webSocket.listen((onData) {
        print("Server:" + onData);
      },onError: (err){
        print("Server:Error " + err);
      },onDone: (){
        print("Server Disconnect");
      });
    });
  }

  void sendMSG(){
    _webSocket.add('hahahha');
  }

}
