import datetime
import traceback

import gevent
from gevent import monkey

monkey.patch_all()

import hashlib
from collections import deque

from gevent.queue import Queue
from random import random
from argparse import ArgumentParser
import gevent
from flask import Flask, request, app
import json
import time
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from Client.Mempool import transaction
from Client.client import Client
from Client.make_random_tx import tx_generator
from multiprocessing import Value as mpValue, Queue as mpQueue

app.debug = False

app = Flask(__name__)
CORS(app)

N = 4

'''initialize a client send channel'''
client_channel_mpq = mpQueue()
client_from_bft = lambda: client_channel_mpq.get(timeout=0.00001)
client_to_bft=client_channel_mpq.put_nowait

# def put_txs(size, txs):
#     for i in range(size):
#         mempool.put_nowait(txs[i])


# TODO:put a certain transaction into mempool
def new_transaction(sender, receiver, tx_id, money, fee, localtime):
    pass


# class client:


# def __init__(self,send):
#     self.mempool = Queue()
#     self._send=send
#
#
# def broadcast(self, o):
#     '''
#
#     :param o: message we want broadcast
#     :param send: sending message
#     :param N: broadcast to N nodes
#     :return:
#     '''
#     for i in range(N):
#         self._send(i, o)


def broadcast(o):
    print("enter broadcast")
    print("broadcast {}".format(o))
    client_to_bft(o)


# def start_client(self, mem, p, id):
#     parser = ArgumentParser()
#     netclient = Client('127.0.0.1', addresses, client_to_bft, per_port)
#     netclient.start()
#     # print("start client test")
#     parser.add_argument('-p', '--port', default=p, type=int, help='port to listen on')
#     args = parser.parse_args()
#     port = args.port
#     print("node {} open port {}".format(id, p))
#     app.run(host='127.0.0.1', port=port, debug=True)


@app.route('/')
def index():
    return render_template('./index.html')


@app.route('/submit', methods=['GET', 'POST'])
def submit():
    if request.method == "POST":
        print("tets")
        # return render_template('./test.html')
        sender = request.form.get('sender')
        receiver = request.form.get('receiver')
        money = request.form.get('money')
        fee = request.form.get('txs_fee')
        seed = 1
        rnd = random()
        # tx_id_float = rnd.random()
        # tx_id = hashlib.sha512(str(tx_id_float))
        # tx_id = '000000'
        local_time = time.asctime(time.localtime(time.time()))
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(now_time)
        # mempool.put_nowait(a_transaction)
        # broadcast(a_transaction, send, N)
        tx_str=sender+receiver+money+fee+now_time
        print(type(tx_str))
        broadcast(tx_str)
        response = {
            'transaction time:': local_time,
            'sender': sender,
            'receiver': receiver,
            'money': money,
            'fee': fee
        }
        return jsonify(response), 200


def test_print():
    print("test flask print")


@app.route('/generate', methods=['GET', 'POST'])
def generate(size=100):
    if request.method == "POST":
        tx_list = []
        for _ in range(size):
            atx=tx_generator(250)
            # client_to_bft(atx)
            broadcast(atx)
            test_print()
            tx_list.append(atx)
        # broadcast(tx_list)
        response = {
            'transaction generation:': tx_list,
        }
        return jsonify(response), 200


if __name__ == '__main__':
    print("test1")
    addresses = [None] * N
    try:
        with open('host_client2.config', 'r') as hosts:
            print("open success")
            for line in hosts:
                params = line.split()
                pid = int(params[0])
                priv_ip = params[1]
                pub_ip = params[2]
                port = int(params[3])
                # print(pid, ip, port)
                if pid not in range(N):
                    continue
                addresses[pid] = (pub_ip, port)
        assert all([node is not None for node in addresses])
        print("hosts.config2 is correctly read")
    except Exception as e:
        print(str(e, traceback.print_exc()))
        print("read error")

    from argparse import ArgumentParser

    #
    parser = ArgumentParser()
    # TODO: check if should wait all bft nodes online
    netclient = Client('127.0.0.1', addresses, client_from_bft, 5)
    netclient.start()
    parser.add_argument('-p', '--port', default=8080, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port
    print("start")
    app.run(debug=False, host='127.0.0.1', port=port,use_reloader=False)
    print("exit")
