import socket
from time import ctime

class GinkgoTCPServer(object):
    """
    TCPSocket的简单封装

    :param object: [description]
    :type object: [object]
    """
    def __init__(self):
        self.host = '192.168.11.33'
        self.port = 8019
        self.buffsize = 1024
        self.address = (self.host, self.port)  # 这是个元组
        

    def start(self):
        # 创建Socket
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 绑定IP和PORT
        self.tcp_server.bind(('', self.port))  # ip不写表示本机的任意一个IP
        self.tcp_server.listen(5)  # 使Socket变为被动连接

    def handel(self):
        while True:
            print('Waiting for connection...')
            tcp_client_socket, addr = self.tcp_server.accept()  #  等待客户端连接
            print('...connnecting from:', addr)

            while True:
                data = tcp_client_socket.recv(self.buffsize)
                if not data or data.decode('utf-8') == 'exit':
                    break

                print(data.decode('utf-8')+' from '+addr[0]+':'+str(addr[1]))
                tcp_client_socket.send(('[%s] %s' % (ctime(), data)).encode('utf-8'))
        tcp_client_socket.close()


    def close_server(self):
        self.tcp_server.close()


class GinkgoTCPClient(object):
    """
    Socket的简单封装

    :param object: [description]
    :type object: [object]
    """
    def __init__(self):
        self.host = '192.168.1.1'
        self.port = 8020
        self.buffsize = 1024
        self.address = (self.host, self.port) # 这是个元组
        self.tcp_client_socket = None

    def send(self):
        self.tcp_client_socket = socket.socket(socket.AF_INET)
        self.tcp_client_socket.bind('', self.port)
        send_data = input('请输入要发送的数据：')
        self.tcp_client_socket.send(send_data.encode('utf-8'), self.address)
    
    def close(self):
        try:
            self.tcp_client_socket.close()
        except Exception as e:
            print(e)
        
class GinkgoUDPServer(object):
    def __init__(self):
        self.host = '192.168.11.33'
        self.port = 8019
        self.buffsize = 1024
        self.address = (self.host, self.port)  # 这是个元组
        

    def start(self):
        # 创建Socket
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 绑定IP和PORT
        self.udp_socket.bind(('', self.port))  # ip不写表示本机的任意一个IP
        # self.udp_socket.settimeout(10)  #设置一个时间提示，如果10秒钟没接到数据进行提示

    def handel(self):
        while True:
            print('Waiting for connection...')
            receive_data, client = self.udp_socket.recvfrom(self.buffsize)
            print("来自客户端%s,发送的%s\n" % (client, receive_data))
            # self.udp_socket.send(receive_data)

        self.udp_socket.close()


    def close_server(self):
        self.udp_socket.close()


t = GinkgoUDPServer()
t.start()
t.handel()