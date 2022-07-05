# README

### 1.Requiments

- Python 3.6 ++
- Docker
- Docker-compose

#### 1.Create Virtual Enviroment

#### 1.1.Create your own enviroment

```shell script
cd <project path>
python -m venv venv
```

#### 1.2、Activate the enviroment you created

```shell
# Windows && Powershell
venv\Scripts\Activate.ps1

# Windows && CMD Tool
venv\Scripts\Activate.bat

# Linux && MacOS
source venv/bin/activate
```

### 2.Run script to install everything
```shell
python ./install.py
```

### 3.If it goes well, you will have docker running called ginkgo-mongo

### 4.You could update data by script.
```shell
python ./examples/data_update_async.py
```
The script will auto download China's Stock info. Contains min5data and daybar.
The data.py also have the code for downloading crypto data, but the code may be deperated. You should find apis or create your own spider.

### 5.Run Examples\Simple_demo.py

This is a demo for the Engine.
You could edit your own strategy and set indexes to confirm your idea.


#### Update the requirements.
```shell
pip freeze > requirements.yml
```


