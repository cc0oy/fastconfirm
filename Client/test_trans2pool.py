import hashlib
from queue import Queue
from random import random

import gevent
from flask import Flask, request, app
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from gevent import Greenlet

import Mempool.transaction
from Client.start_client import start_client

sender=""
receiver=""
app = Flask(__name__)
CORS(app)


def simple_router(N,maxdelay,seed=None):
    '''
    build a set of connected channels, with random delay but <delta
    :param N: node number
    :param maxdelay: network delay < delta
    :param seed:
    :return: (receives, sends)
    '''

    #rnd=random.Random(seed)
    queues=[Queue() for _ in range(N)]  #channels as list


    def make_send(i):
        '''

        :param i: the node send messages
        :return: a send channel
        '''
        def _send(j,o):
            '''
            j send messages to i
            :param j:
            :param o:
            :return:
            '''
            #delay=rnd.random()*maxdelay
            delay=0
            gevent.spawn_later(delay,queues[j].put,(i,o))
        return _send


    def make_recv(j):
        def _recv():
            (i,o)=queues[j].get()
            return (i,o)
        return _recv

    return ([make_send(i) for i in range(N)],[make_recv(j) for j in range(N)])


def _test_mempool(N=4,seed=None):
    sends,recvs=simple_router(N,0,seed=seed)
    threads=[None]*N
    for i in range (N):
        print("start test")
        j=(i+1)*1000
        threads[i]=gevent.spawn(start_client,j,recvs,sends)
    try:
        outs=[threads[i].get() for i in range(N)]
        print(outs)
        assert len(set(outs))==1
    except KeyboardInterrupt:
        gevent.killall(threads)
        raise



if __name__ == '__main__':
    _test_mempool()