import 'package:ginkgo_client/src/utils/ginkgo_dio.dart';
import 'dart:convert';
import 'dart:io';

String url_prefix = '/stock';

getStockList() async {
  String url = '/get_stock_info';
  String tarUrl = url_prefix + url;

  var request = await GinkgoDio.getInstance().get(tarUrl);
  var data = jsonDecode(request.toString());
  return data;
}
