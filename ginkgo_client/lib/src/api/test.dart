import 'package:ginkgo_client/src/utils/my_dio.dart';

String url_prefix = '/test';

void justForTest() {
  String url = '/flutter';
  String tar_url = url_prefix + url;
  ginkgo_dio.get(tar_url, (res) {}, (err) {});
}
