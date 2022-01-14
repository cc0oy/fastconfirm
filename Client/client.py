from random import randint

from gevent import monkey;

monkey.patch_all(thread=False)

import time
import pickle
from typing import List, Callable
import gevent
import os
from multiprocessing import Value as mpValue, Process
from gevent import socket, lock
from gevent.queue import Queue
import logging
import traceback


# Network node class: deal with socket communications
class Client(Process):
    SEP = '\r\nSEP\r\nSEP\r\nSEP\r\n'.encode('utf-8')

    def __init__(self, my_ip, addresses_list, send_2_bftnode: Callable, port_num=5):

        self.send_to_bft = send_2_bftnode
        # self.ready = client_ready
        # self.stop = stop

        self.ip = my_ip
        self.port_base = 50000

        self.addresses_list = addresses_list
        self.N = len(self.addresses_list)
        self.per_port_num = port_num
        self.total_port_num = self.per_port_num * self.N

        self.is_out_sock_connected = [False] * self.total_port_num

        self.socks = [None for _ in range(self.total_port_num)]
        self.sock_queues = [Queue() for _ in range(self.total_port_num)]  # sent messages channels
        self.sock_locks = [lock.Semaphore() for _ in range(self.total_port_num)]

        super().__init__()

    def _connect_and_send_forever(self):
        pid = os.getpid()
        # print("N: {}, total link: {}, per link: {}".format(self.N, self.total_port_num, self.per_port_num))
        self.logger.info('client starts to make outgoing connections on process id %d' % (pid))
        while True:
            try:
                for j in range(self.N):
                    for i in range(self.per_port_num):
                        # print("double for j={}, i={}, self.N={}, self.perportnum={}".format(j,i,self.N,self.per_port_num))
                        if not self.is_out_sock_connected[j * self.per_port_num + i]:
                            self.is_out_sock_connected[j * self.per_port_num + i] = self._connect(j, self.per_port_num,
                                                                                                  i)
                if all(self.is_out_sock_connected):
                    # with self.ready.get_lock():
                    #     self.ready.value = True
                    print("all connect")
                    break
            except Exception as e:
                print("while error")
                self.logger.info(str((e, traceback.print_exc())) + "    connect {}".format(j))
        send_threads = [gevent.spawn(self._send, j) for j in range(self.total_port_num)]
        self._handle_send_loop()
        # gevent.joinall(send_threads)

    def _connect(self, j: int, perport: int, ith):
        # for i in range(perport):
        print("enter connect")
        sock = socket.socket()
        if self.ip == '127.0.0.1':
            print("the {}-th port to bft {} try to bind port {}".format(ith, j, self.port_base + j * perport + ith))
            try:
                sock.bind((self.ip, self.port_base + j * perport + ith))
            except Exception as e:
                print("bind particular error")
        try:
            # print("check {} sock: {}".format(j, self.addresses_list[j]))
            sock.connect(self.addresses_list[j])
            # print("connect finish")
            self.socks[j * perport + ith] = sock
        except Exception as e1:
            # print(self.ip + ":" + str(self.port_base + j * perport + i) + "  " + str(
            # (e1, traceback.print_exc())) + "  ")
            # self.logger.critical("node {} try to connect {} fails".format(self.ip+":"+str(self.port_base+j*perport+i),self.addresses_list[j]))
            self.logger.critical(self.ip + ":" + str(self.port_base + j * perport + ith) + "  " + str(
                (e1, traceback.print_exc())) + "  ")
            print("Failure: the {}-th port{} of {} bft node connect {} fails".format(ith, sock.getsockname(), j,
                                                                              self.addresses_list[j]))
            return False

        print("the {}-th port{} of {} bft node connect {} success".format(ith, sock.getsockname(), j,
                                                                          self.addresses_list[j]))
        # print("connect will return True")
        return True

    def _send(self, j: int):
        # while not self.stop.value:
        while True:
            # gevent.sleep(0)
            # self.sock_locks[j].acquire()
            o = self.sock_queues[j].get()
            try:
                print("node {} really send {}".format(j, o))
                self.socks[j].sendall(pickle.dumps(o) + self.SEP)
            except:
                self.logger.error("fail to send msg")
                # self.logger.error(str((e1, traceback.print_exc())))
                self.socks[j].close()
                break
            # self.sock_locks[j].release()

    ##
    def _handle_send_loop(self):
        # while not self.stop.value:
        while True:
            try:
                o = self.send_to_bft()
                # o = self.send_queue[j].get_nowait()
                # self.logger.info('send' + str((j, o)))
                try:
                    '''choose a socket randomly to send the transaction'''
                    seed = randint(0, self.total_port_num - 1)
                    print("handle process choose port {} node {} to send {}".format(seed, seed / self.per_port_num, o))
                    self.sock_queues[seed].put_nowait(o)
                except Exception as e:
                    self.logger.error(str(("problem objective when sending", o)))
                    traceback.print_exc()
                # try:
                #     #self._send(j, pickle.dumps(o))
                #     if j == -1: # -1 means broadcast
                #         for i in range(self.N):
                #             self.sock_queues[i].put_nowait(o)
                #     elif j == -2: # -2 means broadcast except myself
                #         for i in range(self.N):
                #             if i != self.pid:
                #                 self.sock_queues[i].put_nowait(o)
                #     else:
                #         self.sock_queues[j].put_nowait(o)
                # except Exception as e:
                #     self.logger.error(str(("problem objective when sending", o)))
                #     traceback.print_exc()
            except:
                pass

        # print("sending loop quits ...")

    def run(self):
        self.logger = self._set_client_logger()
        pid = os.getpid()
        self.logger.info('client is running on pid %d and trying to transform messages' % (pid))
        # with self.ready.get_lock():
        #     self.ready.value = False
        self._connect_and_send_forever()

    # def stop_service(self):
    #     with self.stop.get_lock():
    #         self.stop.value = True

    def _set_client_logger(self):
        logger = logging.getLogger("node-client-host")
        logger.setLevel(logging.DEBUG)
        # logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s %(filename)s [line:%(lineno)d] %(funcName)s %(levelname)s %(message)s ')
        if 'log' not in os.listdir(os.getcwd()):
            os.mkdir(os.getcwd() + '/log')
        full_path = os.path.realpath(os.getcwd()) + '/log/' + "node-net-client-client.log"
        file_handler = logging.FileHandler(full_path)
        file_handler.setFormatter(formatter)  # 可以通过setFormatter指定输出格式
        logger.addHandler(file_handler)
        return logger
