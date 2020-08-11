import socket
import threading
import time
import sys
import queue
from ginkgo.libs.thread_manager import thread_manager


class SocketServer(object):
    socket_pool = {}

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            if not hasattr(cls, '_instance'):
                SocketServer._instance = super().__new__(cls)
            return SocketServer._instance

    def create_socket(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 防止socket server重启后端口被占用（socket.error: [Errno 98] Address already in use）
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', 5102))
            s.listen(5)
        except socket.error as msg:
            print(msg)
            sys.exit(1)
        print('Waiting Connection...')

        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=deal_data, name=f'socket{addr}', args=(conn, addr))
            socket_pool_key = addr[0] + ':' + str(addr[1])
            self.socket_pool[socket_pool_key] = s
            thread_manager.thread_register(t)
            for i in self.socket_pool:
                print(i)

    def kill_all_sockets(self):
        for i in self.socket_pool:
            self.socket_pool[i].close()

def deal_data(connection, addr):
    print(f'Accept new connection from {format(addr)}')
    connection.send(('Hi, Welcome to the Server!').encode())
    while True:
        # 处理返回信息
        data = connection.recv(1024)
        print(
            f'{addr} client send data is {data.decode()}')
        time.sleep(1)
        if data == 'exit' or not data:
            print(f'{format(addr)} connection close')
            connection.send(bytes('Connection closed!'), 'utf-8')
            break
        connection.send(bytes(f'Hello, {format(data)}', "utf-8"))  # TypeError: a bytes-like object is required, not 'str'
    connection.close()


socket_server = SocketServer()


def socket_run_thread():
    socket_server.create_socket()


def socket_boost():
    t = threading.Thread(target=socket_run_thread, name='socket_server')
    thread_manager.thread_register(t)
