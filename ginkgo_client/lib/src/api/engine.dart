import 'package:ginkgo_client/src/utils/dio.dart';

String url_prefix = '/engine';

void EngineBoost(){
  String url = '/boost';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}

void EngineSleep(){
  String url = '/sleep';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}

void EngineResume(){
  String url = '/resume';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}

void InfoInjection(){
  String url = '/info_injection';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}

