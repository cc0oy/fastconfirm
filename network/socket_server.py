from gevent import monkey; monkey.patch_all(thread=False)

from gevent.server import StreamServer
import pickle
from typing import Callable
import os
import logging
import traceback
from multiprocessing import Value as mpValue, Process



# Network node class: deal with socket communications
class NetworkServer (Process):

    SEP = '\r\nSEP\r\nSEP\r\nSEP\r\n'.encode('utf-8')

    def __init__(self, port: int, my_ip: str, id: int, addresses_list: list, server_to_bft: Callable, server_ready: mpValue, stop: mpValue):

        self.server_to_bft = server_to_bft
        self.ready = server_ready
        self.stop = stop
        self.ip = my_ip
        self.port = port
        self.id = id
        self.addresses_list = addresses_list
        self.N = len(self.addresses_list)
        self.is_in_sock_connected = [False] * self.N
        self.socks = [None for _ in self.addresses_list]
        super().__init__()

    def _listen_and_recv_forever(self):
        print("listen and receive loop")
        pid = os.getpid()
        self.logger.info('node %d\'s socket server starts to listen ingoing connections on process id %d' % (self.id, pid))
        self.logger.info("my IP is " + self.ip+":"+str(self.port))

        def _handler(sock, address):
            jid = self._address_to_id(address)
            buf = b''
            self.logger.debug("handle enter")
            try:
                self.logger.debug("handle enter and stopvalue is {}".format(self.stop.value))
                while not self.stop.value:
                    buf += sock.recv(9000)
                    tmp = buf.split(self.SEP, 1)
                    while len(tmp) == 2:
                        buf = tmp[1]
                        data = tmp[0]
                        if data != '' and data:
                            (j, o) = (jid, pickle.loads(data))
                            # assert j in range(self.N)
                            self.server_to_bft((j, o))
                            self.logger.info('recv' + str((j, o)))
                            # print('recv' + str((j, o)))
                        else:
                            self.logger.error('syntax error messages')
                            raise ValueError
                        tmp = buf.split(self.SEP, 1)
                    #gevent.sleep(0)
            except Exception as e:
                self.logger.error(str((e, traceback.print_exc())))

        try:
            self.logger.debug("stream server1")
            self.streamServer = StreamServer((self.ip, self.port), _handler)
            self.logger.debug("stream server2")
            self.streamServer.serve_forever()
            self.logger.debug("stream server3")
        except Exception as e1:
            self.logger.error(str((e1, traceback.print_exc())))


    def run(self):
        print("socket server run")
        pid = os.getpid()
        self.logger = self._set_server_logger(self.id)
        self.logger.info('node id %d is running on pid %d' % (self.id, pid))
        with self.ready.get_lock():
            self.ready.value = False
        self.ready.value=True
        self._listen_and_recv_forever()

    def _address_to_id(self, address: tuple):
        self.logger.info("socket server add2id start")
        for i in range(self.N):
            self.logger.debug("loop enter")
            if address[0] != '127.0.0.1' and address[0] == self.addresses_list[i][0]:
                self.logger.debug("if enter")
                return i
        return int((address[1] - 10000) / 200)

    def _set_server_logger(self, id: int):
        logger = logging.getLogger("node-net-server" + str(id))
        logger.setLevel(logging.DEBUG)
        # logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s %(filename)s [line:%(lineno)d] %(funcName)s %(levelname)s %(message)s ')
        if 'log' not in os.listdir(os.getcwd()):
            os.mkdir(os.getcwd() + '/log')
        full_path = os.path.realpath(os.getcwd()) + '/log/' + "node-net-server-" + str(id) + ".log"
        file_handler = logging.FileHandler(full_path)
        file_handler.setFormatter(formatter)  # 可以通过setFormatter指定输出格式
        logger.addHandler(file_handler)
        return logger
