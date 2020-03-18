"""
代理校验，先通过百度进行初级校验，在通过httpbin进行ip校验，都通过返回Ture
"""
import urllib.request


class ProxyCheck(object):
    target_url = 'http://www.baidu.com'
    target_url2 = 'http://httpbin.org/ip'

    @classmethod
    def ip_check(cls, schema='http', ip='112.84.99.214', port='8264'):
        schema = schema
        ip = ip
        port = port
        proxy = schema + '://' + ip + ':' + port
        proxy_handler = urllib.request.ProxyHandler({
            schema: proxy
        })
        opener = urllib.request.build_opener(proxy_handler)
        # 1、连百度
        # 2、如果可以连百度，再连httpbin校验ip
        try:
            response = opener.open(cls.target_url, timeout=10)
            print(response.read())
            try:
                response = opener.open(cls.target_url2, timeout=10)
                print(response.read())
                print('Access to Baidu and httpbin.')
                return True
            except Exception as e:
                print('Access to Baidu, but failed to httpbin.')
                # raise e
                return False
        except Exception as e:
            print('Failed to Baidu.')
            # raise e
            return False


s = ProxyCheck.ip_check(schema='http', ip='182.105.235.133', port='3000')
print(s)