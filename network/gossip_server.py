import logging
import math
import os
import pickle
import traceback
from collections import Callable
from multiprocessing import Value as mpValue, Process
from random import randint

import numpy as np
from crypto.ecdsa.ecdsa import hash

import numpy
import numpy as np
from gevent.server import StreamServer


class GossipServer(Process):
    SEP = '\r\nSEP\r\nSEP\r\nSEP\r\n'.encode('utf-8')

    def __init__(self, link_size: int, port: int, my_ip: str, id: int, addresses_list: list, server_to_bft: Callable,
                 send: Callable, server_ready: mpValue, stop: mpValue):

        self.server_to_bft = server_to_bft
        self.ready = server_ready
        self.stop = stop
        self.ip = my_ip
        self.port = port
        self.id = id
        self.addresses_list = addresses_list
        self.N = len(self.addresses_list)

        self.link_size = link_size
        self.link = []

        sum = 0
        base = 1
        self.tdeep = 0
        # self.tdeep = math.ceil(np.log(self.N)/np.log(self.link_size))
        # if self.id!=0:
        #     self.deep=math.ceil(np.log(self.id)/np.log(self.link_size))
        # else:
        #     self.deep=0
        # current=pow(self.link_size,self.deep)
        # ind=current-self.id+
        while sum < self.N:
            current = pow(self.link_size, self.tdeep)
            if sum <= self.id:
                self.deep = self.tdeep
                ind = self.id - sum + 1
                cur = current
            sum = sum + current
            self.tdeep += 1
            # if current * self.link_size + sum > self.N:
            #     break
            # base *= self.link_size

        print("tdeep",self.tdeep)
        self.tdeep-=1
        if self.deep == 0:
            i = 1
        elif self.deep != self.tdeep:
            i = self.id + self.link_size * (ind - 1) + (cur - ind) + 1
        else:
            i = 0

        flag=0
        lower = i
        if i >= self.N:
            lower = 0
            upper = 1
            flag=-1
        elif i + self.link_size > self.N:
            flag=1
            upper = self.N
        else:
            flag=0
            upper = i + self.link_size

        for j in range(lower, upper):
            self.link.append(addresses_list[j])


        if flag==-1:
            i = 0
            for i in range(self.link_size-len(self.link)):
                index=randint(1,self.N-1)
                self.link.append(addresses_list[index])
        elif flag==1:
            # add=self.N-i-self.link_size
            i = 0
            for i in range(self.link_size-len(self.link)):
                index = randint(1, self.N - 1)
                self.link.append(addresses_list[index])

        self.socks = [None for _ in self.link]
        self.is_in_sock_connected = [False] * self.link_size
        print("node ", self.id, "link:", self.link, " with height", self.deep)

        self.s = send
        self._sent = []
        self._received=[]
        self._send = lambda j, o: self.s((j, o))
        super().__init__()

    def _listen_and_recv_forever(self):
        # print("listen and receive loop")
        pid = os.getpid()
        self.logger.info(
            'node %d\'s socket server starts to listen ingoing connections on process id %d' % (self.id, pid))
        # print("my IP is " + self.ip + ":" + str(self.port))

        def _handler(sock, address):
            # print(self.id, "handle enter")
            jid = self._address_to_id(address)
            buf = b''
            # self.logger.debug("handle enter")
            try:
                # print("node ", self.id, " handle enter")
                # self.logger.debug("handle enter and stopvalue is {}".format(self.stop.value))
                while not self.stop.value:
                    buf += sock.recv(9000)
                    tmp = buf.split(self.SEP, 1)
                    # print("not stop node ",self.id," with len ",len(tmp))
                    while len(tmp) == 2:
                        buf = tmp[1]
                        data = tmp[0]
                        if data != '' and data:
                            (j, o) = (jid, pickle.loads(data))
                            recv_hash = hash(str(o))
                            # assert j in range(self.N)
                            if recv_hash not in self._received:
                                self.server_to_bft((j, o))
                                self._received.append(recv_hash)

                            # print('node ' + str(self.id) + ' recv' + str((j, o)))

                            # print("node ", self.id, "recv hash:", recv_hash, " and hash list:", self._sent)
                            if recv_hash not in self._sent:
                                # print(self.id, " dont recv such hash and try to forward")
                                self._sent.append(hash(str(o)))
                                # print('node ' + str(self.id) + ' recv list'+str(len(self._sent))+' '+str(o)+''+ ''+str(recv_hash))
                                for l in self.link:
                                    l_id = self._address_to_id(l)
                                    # print("node {} try forward to {}".format(self.id, l_id))
                                    self._send(l_id, o)
                            # print('recv' + str((j, o)))
                        else:
                            self.logger.error('syntax error messages')
                            raise ValueError
                        tmp = buf.split(self.SEP, 1)
                    # gevent.sleep(0)
            except Exception as e:
                self.logger.error(str((e, traceback.print_exc())))

        self.streamServer = StreamServer((self.ip, self.port), _handler)
        # print("node", self.id, " out handle with (", self.ip, ",", self.port, ")")
        # self.logger.info("invoke streamServer with ({},{}) start? {} object {}".format(self.ip,self.port,self.streamServer.started,type(self.streamServer)))

        try:
            # print("{} streamserver state:{}".format(self.id,self.streamServer.started))
            self.streamServer.serve_forever()
        except Exception as e1:
            print("streamsever error:" + str((e1, traceback.print_exc())))

    def run(self):
        # print("socket sever run")
        pid = os.getpid()
        self.logger = self._set_server_logger(self.id)
        self.logger.info('node id %d is running on pid %d' % (self.id, pid))
        with self.ready.get_lock():
            self.ready.value = False
        # self.ready.value=True
        self._listen_and_recv_forever()

    def _address_to_id(self, address: tuple):
        # self.logger.info("socket server add2id start")
        for i in range(self.N):
            # self.logger.debug("loop enter")
            if address[0] != '127.0.0.1' and address[0] == self.addresses_list[i][0]:
                # self.logger.debug("if enter")
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
