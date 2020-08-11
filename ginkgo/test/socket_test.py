import socket # 导入 socket 模块 
import time
s = socket.socket()         # 创建 socket 对象
host = 'localhost' # 获取本地主机名
port = 5102  # 设置端口号
s.connect((host, port))
i = 0
while True:
    i +=1
    # addr = client.accept()
    # print '连接地址：', addr
    msg = f'Today is a good {i}day!'  #strip默认取出字符串的头尾空格
    s.send(msg.encode('utf-8'))  #发送一条信息 python3 只接收btye流
    data = s.recv(1024) #接收一个信息，并指定接收的大小 为1024字节
    print('recv:',data.decode()) #输出我接收的信息
    time.sleep(1)
s.close() #关闭这个链接