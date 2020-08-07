import 'package:ginkgo_client/src/utils/dio.dart';

String url_prefix = '/test';

void EngineRun(){
  String url = '/backtest';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}

void DataFeed(){
  String url = '/backtest_feed';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}
