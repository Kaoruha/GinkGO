import 'package:ginkgo_client/src/utils/dio.dart';

String url_prefix = '/stock';

void StockDataUpdate() {
  String url = '/all_stock';
  String tar_url = url_prefix + url;
  ginkgo_dio.post(tar_url);
}