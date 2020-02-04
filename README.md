# BeuQuant
#### 1、 部署环境
```shell script
# 创建虚拟环境
python3 -m venv venv

# macOS下激活虚拟环境
source venv/bin/activate

# Windows运行activate.bat
venv\Scripts\activate  
```

#### 2、 安装依赖包
```shell script
# 按照Pipfile内的包信息安装
pip install -r Pipfile

# 如果速度慢可以换国内源  
pip install -r Pipfile -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 3、 YellowPrint与BluePrint
> libs下的yellowPrint实现了blueprint的衍生类，用于细分url，通过 yp_user.register(bp) 来挂载到Blueprint

### 4、 爬虫
> app/spider是基于Scrapy框架拓展的爬虫模块