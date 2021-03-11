import 'package:dio/dio.dart';
import 'package:dio_cookie_manager/dio_cookie_manager.dart';
import 'package:cookie_jar/cookie_jar.dart';

class GinkgoDio {
  // 基础配置
  final String _BASEURL = 'http://127.0.0.1:8080/api/';
  final int _CONNECTTIMEOUT = 5000;
  final int _RECEIVETIMEOUT = 3000;

  //单例模式
  static GinkgoDio _instance;
  Dio _dio;
  BaseOptions _options;

  // 单例模式，只创建一次实例
  static GinkgoDio getInstance() {
    if (_instance == null) {
      _instance = new GinkgoDio();
    }
    return _instance;
  }

  // 构造函数
  GinkgoDio() {
    _options = new BaseOptions(
        baseUrl: _BASEURL,
        //连接时间为5秒
        connectTimeout: _CONNECTTIMEOUT,
        //响应时间为3秒
        receiveTimeout: _RECEIVETIMEOUT,
        //设置请求头
        // headers: {"resource": "android"},
        //默认值是"application/json; charset=utf-8",Headers.formUrlEncodedContentType会自动编码请求体.
        contentType: Headers.formUrlEncodedContentType,
        //共有三种方式json,bytes(响应字节),stream（响应流）,plain
        responseType: ResponseType.json);
    _dio = new Dio(_options);
    //设置Cookie
    _dio.interceptors.add(CookieManager(CookieJar()));

    //添加拦截器
    _dio.interceptors
        .add(InterceptorsWrapper(onRequest: (RequestOptions options) {
      print("请求拦截");
      return options;
    }, onResponse: (Response response) {
      print("响应拦截");
      return response;
    }, onError: (DioError e) {
      print("错误拦截");
      return e;
    }));
  }

  // GET
  get(url, {data, options, cancelToken}) async {
    Response response;
    try {
      response = await _dio.get(url,
          queryParameters: data, options: options, cancelToken: cancelToken);
      // print('getHttp response: $response');
    } on DioError catch (e) {
      // print('getHttp exception: $e');
      formatError(e);
    }
    return response;
  }

  // POST
  post(url, {params, options, cancelToken}) async {
    Response response;
    try {
      response = await _dio.post(url,
          queryParameters: params, options: options, cancelToken: cancelToken);
      print('postHttp response: $response');
    } on DioError catch (e) {
      print('postHttp exception: $e');
      formatError(e);
    }
    return response;
  }

  // POST FORM
  postForm(url, {data, options, cancelToken}) async {
    Response response;
    try {
      response = await _dio.post(url,
          options: options, cancelToken: cancelToken, data: data);
      print('postHttp response: $response');
    } on DioError catch (e) {
      print('postHttp exception: $e');
      formatError(e);
    }
    return response;
  }

  // DOWNLOAD
  downLoadFile(urlPath, savePath) async {
    Response response;
    try {
      response = await _dio.download(urlPath, savePath,
          onReceiveProgress: (int count, int total) {
        print('$count $total');
      });
      print('downLoadFile response: $response');
    } on DioError catch (e) {
      print('downLoadFile exception: $e');
      formatError(e);
    }
    return response;
  }

  // 异常处理
  void formatError(DioError e) {
    if (e.type == DioErrorType.CONNECT_TIMEOUT) {
      print("连接超时");
    } else if (e.type == DioErrorType.SEND_TIMEOUT) {
      print("请求超时");
    } else if (e.type == DioErrorType.RECEIVE_TIMEOUT) {
      print("响应超时");
    } else if (e.type == DioErrorType.RESPONSE) {
      print("出现异常");
    } else if (e.type == DioErrorType.CANCEL) {
      print("请求取消");
    } else {
      print("未知错误");
    }
  }
}
