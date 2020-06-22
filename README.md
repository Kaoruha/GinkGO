# BeuQuant
#### 1、 开发环境部署
```shell script
# 1、创建虚拟环境
python3 -m venv venv

# 2.1、macOS下激活虚拟环境
source venv/bin/activate

# 2.2、Windows运行activate.bat
# 在BeuQuant目录下
venv\Scripts\activate

# 3 安装依赖包
# 3.1、按照Pipfile内的包信息安装
pip install -r Pipfile

# 3.2、如果速度慢可以换国内源  
pip install -r Pipfile -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3.3、有新的包在安装完成后，需要更新Pipfile
pip freeze >Pipfile
```

#### 2、 生产环境部署
nginx+gunicorn
```shell script
# 通过gunicorn启动flask
gunicorn -w 4 -b 127.0.0.1:5000 -D --access-logfile ./static/logs/server_log quant:app

# -w 线程数
# -b 绑定IP与端口
# -D 后台运行
# --access-logfile 设定日志文件地址
# quant：app   主入口文件：flask对象
```

```shell script
# 停止gunicorn服务
gunicorn -w 4 -b 127.0.0.1:5000 -D --access-logfile ./static/logs/server_log quant:app

# 1 查询gunicorn的执行线程
ps aux | grep gunicorn

# 2 杀掉gunicorn线程
kill -9 <线程id>
```

#### 3、 YellowPrint与BluePrint
> libs下的yellowPrint实现了blueprint的衍生类，用于细分url，通过 yp_user.register(bp) 来挂载到Blueprint

#### 4、 爬虫
> app/spider是基于Scrapy框架拓展的爬虫模块