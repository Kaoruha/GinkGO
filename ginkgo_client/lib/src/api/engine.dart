import 'package:ginkgo_client/src/utils/dio.dart';

String url_prefix = '/engine';

void EngineRun(){
  String url = '/start';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}

void EngineSleep(){
  String url = '/sleep';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}
