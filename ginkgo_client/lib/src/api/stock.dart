import 'package:ginkgo_client/src/utils/dio.dart';

String url_prefix = '/stock';

void stockDataUpdate() {
  String url = '/all_stock';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}

void stockCodeUpdate() {
  String url = '/all_stock_code';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}

void stockAdjustUpdate() {
  String url = '/adjust_code';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}
