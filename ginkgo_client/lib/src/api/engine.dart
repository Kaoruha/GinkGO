import 'package:ginkgo_client/src/utils/ginkgo_dio.dart';

String urlPrefix = '/engine';

void engineBoost() {
  String url = '/boost';
  String tarURL = urlPrefix + url;
  GinkgoDio.getInstance().post(tarURL);
}
