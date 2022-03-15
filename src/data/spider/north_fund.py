import requests
from lxml import etree

headers = {
    'content-type': 'application/json',
    "Accept": "*/*", 
    "Accept-Encoding": "gzip, deflate", 
    "User-Agent": "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50", 
    }
params = {}
url = 'http://data.eastmoney.com/hsgt/'
time_out = 10

r = requests.get(url=url, params=params, headers=headers, timeout=time_out)
result_xpath = etree.HTML(r.text)
# selector = result_xpath.xpath('//div[@id="content"]/ul[@id="ul"]/li/text()//body/div[@class="main"]/div[@class="main-content"]/div[@class="framecontent"]/div[@id="main_content"]/div[@id="lssj"]/div[@id="dataview_lssj"]/div[@class="dataview-center"]/div[@class="dataview-body"]/table/tbody/tr')
selector = result_xpath.xpath('//*[@id="dataview_lssj"]/div[2]/div[2]/table/tbody/tr[1]/td[1]')

print(selector)