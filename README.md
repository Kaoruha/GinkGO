<!--
 * @Author: Kaoru
 * @Date: 2021-12-24 23:46:54
 * @LastEditTime: 2022-03-16 10:25:38
 * @LastEditors: Kaoru
 * @Description: Be stronger,be patient,be confident and never say die.
 * @FilePath: /Ginkgo/README.md
 * What goes around comes around.
-->
# 使用手册

### 1、 开发环境部署

需要提前安装Python，建议3.6以上版本
需要提前安装好Docker，以及Docker-compose

#### 1、创建虚拟环境

#### 1.1、Python命令创建虚拟环境

```shell script
cd <project path>
python -m venv venv
```

#### 1.2、激活虚拟环境

#### 1.2.1、windows平台 powershell

```shell
venv\Scripts\Activate.ps1
```

#### 1.2.2、windows平台 cmd

```shell
venv\Scripts\Activate.bat
```

#### 1.2.3、MacOS下

```shell
source venv/bin/activate
```

### 2、运行安装脚本

```shell
python ./install.py
```

### 3、如果顺利的话，会在dist目录下生成程序包，Docker会启动Mongo服务
需要手动安装一下Dist目录下的程序包，
```shell
pip install ./dist/ginkgo-x.xx.x
```

### 4、初步安装完成，可以书写自己的策略，利用策略引擎进行回测

如果安装了新的库，请更新依赖文件
```shell
pip freeze > requirements.yml
```


