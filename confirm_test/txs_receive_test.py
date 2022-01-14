import time
from queue import Queue
from random import randint

import gevent
import random
from Client.make_random_tx import tx_generator
from crypto.ecdsa import ecdsa
from fastconfirm.core.fastconfirm import Fastconfirm

global tx_list
tx_list=[]

def assign_txs(q,N):
    while True:
        index = randint(0, N - 1)
        if len(tx_list)==0:
            break
        atx=tx_list.pop(0)
        q[index].put_nowait(atx)


def simple_router(N, maxdelay=0.01, seed=None):
    """Builds a set of connected channels, with random delay

    :return: (receives, sends)
    """
    rnd = random.Random(seed)

    queues = [Queue() for _ in range(N)]
    tx_queue = [Queue() for _ in range(N)]
    _threads = []

    assign_txs(tx_queue,N)
    # print("=======================")
    #
    # for i in range(N):
    #     print(tx_queue[i])
        # print("++++++++++++++++\ni:")
        # for j in range(tx_queue[i].qsize()):
        #
        # print("++++++++++++++++++:")


    def makeSend(i):
        def _send(j, o):
            delay = rnd.random() * maxdelay
            if not i % 3:
                delay *= 0
            gevent.spawn_later(delay, queues[j].put_nowait, (i, o))

        return _send

    def makeRecv(j):
        def _recv():
            (i, o) = queues[j].get()
            # print(j, (i, o))
            # print 'RECV %8s [%2d -> %2d]' % (o[0], i, j)
            return (i, o)

        return _recv

    def recv_transaction(j):
        def _recv_txs():
            try:
                atx = tx_queue[j].get()
                return atx
            except:
                pass

        return _recv_txs

    return ([makeSend(i) for i in range(N)],
            [makeRecv(j) for j in range(N)],
            [recv_transaction(j) for j in range(N)])



def _test_txs(N=4,f=1,seed=None):
    sid='sidA'
    pks,sk=ecdsa.pki(N)
    rnd=random.Random()
    rounter_seed=rnd.random()
    sends,recvs,recvs_txs=simple_router(N,seed=rounter_seed)

    fcs=[None]*N
    threads=[None]*N

    K = 10
    B = 5
    S = 10



    for i in range(N):
        fcs[i] = Fastconfirm(sid, i, S, B, N, f, pks, sk[i],
                             sends[i], recvs[i], recvs_txs[i],K)
        # print(sPK, sSKs[i], ePK, eSKs[i])

    for i in range(N):
        # if i == 1: continue
        fcs[i].round_key_gen(1024)

    for i in range(N):
        threads[i] = gevent.spawn(fcs[i].run_fast)

    print('start the test...')
    time_start = time.time()

    # gevent.killall(threads[N-f:])
    # gevent.sleep(3)
    # for i in range(N-f, N):
    #    inputs[i].put(0)
    try:
        outs = [threads[i].get() for i in range(N)]
        print(outs)
        # Consistency check
        assert len(set(outs)) == 1
    except KeyboardInterrupt:
        gevent.killall(threads)
        raise

    time_end = time.time()
    print('complete the test...')
    print('time cost: ', time_end - time_start, 's')


def test_dumbo():
    for _ in range(50):
        atx=tx_generator(250)
        tx_list.append(atx)
    print("=====================")
    print(tx_list)
    print("=====================")
    _test_txs()


if __name__ == '__main__':
    test_dumbo()
