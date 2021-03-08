import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:fluttertoast/fluttertoast.dart';

enum Method {
  GET,
  POST,
  // PUT,
  // DELETE,
}

class GinkgoDio {
  //工厂单例
  factory GinkgoDio() => _getInstance();
  static GinkgoDio get instance => _getInstance();
  static GinkgoDio _instance;
  GinkgoDio._internal() {
    // 初始化
  }
  static GinkgoDio _getInstance() {
    if (_instance == null) {
      _instance = new GinkgoDio._internal();
    }
    return _instance;
  }

  static Dio dio = Dio(
    BaseOptions(
      baseUrl: 'http://127.0.0.1:8080/api',
      connectTimeout: 60000, // 连接服务器超时时间，单位是毫秒.
      receiveTimeout: 10000, // 响应流上前后两次接受到数据的间隔，单位为毫秒, 这并不是接收数据的总时限.
    ),
  );

  get(String url,
      {Map<String, dynamic> data, Function success, Function failure}) {
    _doRequest(url, data, Method.GET, success, failure);
  }

  post(String url,
      {Map<String, dynamic> data, Function success, Function failure}) {
    _doRequest(url, data, Method.POST, success, failure);
  }

  // TOOD 加拦截器 设置Token 。。。。
  void _doRequest(String url, Map<String, dynamic> data, Method method,
      Function successCallBack, Function failureCallBack) async {
    try {
      /// 可以添加header
      //  dio.options.headers.addAll({'token':xxx});
      Response response;
      switch (method) {
        case Method.GET:
          if (data != null && data.isNotEmpty) {
            response = await dio.get(url, queryParameters: data);
          } else {
            response = await dio.get(url);
          }
          break;
        case Method.POST:
          if (data != null && data.isNotEmpty) {
            response = await dio.post(url, queryParameters: data);
          } else {
            response = await dio.post(url);
          }
          break;
      }
      Map<String, dynamic> result = json.decode(response.toString());
      // 打印信息
      print('''api: $url\nparams: $data\nresult: $result''');
      // 转化为model
      // BaseModel model = BaseModel.fromJson(result);
      // if (model.code == 200) {
      //   // 200 请求成功
      //   if (successCallBack != null) {
      //     //返回请求数据
      //     successCallBack(model.data);
      //   }
      // } else {
      //   //TODO
      //   //直接使用Toast弹出错误信息
      //   //返回失败信息
      //   if (failureCallBack != null) {
      //     failureCallBack(model.error);
      //   }
      // }
    } catch (exception) {
      print('错误：${exception.toString()}');
      // Fluttertoast.showToast(msg: "请求失败，请稍后再试");
      if (failureCallBack != null) {
        failureCallBack(exception.toString());
      }
    }
  }
}

final GinkgoDio ginkgo_dio = new GinkgoDio();
