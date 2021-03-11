import 'package:ginkgo_client/src/utils/ginkgo_dio.dart';

String url_prefix = '/engine';

void engineBoost() {
  String url = '/boost';
  String tar_url = url_prefix + url;
  GinkgoDio.getInstance().post(tar_url);
}
