import 'package:ginkgo_client/src/utils/ginkgo_dio.dart';

String url_prefix = '/test';

void justForTest() {
  String url = '/flutter';
  String tar_url = url_prefix + url;
  GinkgoDio.getInstance().get(tar_url);
}
