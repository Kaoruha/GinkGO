import 'package:ginkgo_client/src/utils/dio.dart';

String url_prefix = '/engine';

void engineBoost() {
  String url = '/boost';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url, {}, (res) {}, (err) {});
}

void engineSleep() {
  String url = '/sleep';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url, {}, (res) {}, (err) {});
}

void engineResume() {
  String url = '/resume';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url, {}, (res) {}, (err) {});
}

void infoInjection() {
  String url = '/info_injection';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url, {}, (res) {}, (err) {});
}
