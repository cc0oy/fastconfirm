import os
import pickle
import time

from coincurve import PrivateKey, PublicKey

from fastconfirm.core.fastconfirm import Fastconfirm


def load_key_pickle(id,N):
    pk=[]
    for i in range(N):
        with open(os.getcwd() + '/keys/' + 'sPK2-'+str(i)+'.key', 'rb') as fp:
            # sPK = pickle.load(fp)
            pk.append(PublicKey(pickle.load(fp)))

    with open(os.getcwd() + '/keys/' + 'ePK.key', 'rb') as fp:
        ePK = pickle.load(fp)

    with open(os.getcwd() + '/keys/' + 'sSK2-' + str(id) + '.key', 'rb') as fp:
        sSK = PrivateKey(pickle.load(fp))

    with open(os.getcwd() + '/keys/' + 'eSK-' + str(id) + '.key', 'rb') as fp:
        eSK = pickle.load(fp)
    print("node",id,"read keys",type(pk[0]),type(sSK))
    return sSK,pk


def load_key(filepath, id, N):
    pks = []
    with open(filepath + 'sk-' + str(id) + '.der', 'rb') as fp:
        sk = PrivateKey().from_der(fp.read())
        fp.close()
    for i in range(N):
        with open(filepath + 'pks-' + str(i) + '.key', 'rb') as fp:
            apk = PublicKey(fp.read())
            pks.append(apk)
            fp.close()

    return sk, pks


class FastConfirmNode(Fastconfirm):

    def __init__(self, sid, pid, S, B, N, f, bft_from_server, bft_to_client, bft_from_app, ready, stop, K, mute=False,
                 debug=True):
        # self.sk, self.pks = load_key(os.getcwd() + '/keys_4test/', pid, N)
        self.sk, self.pks = load_key_pickle(pid, N)
        print("test pk",self.pks[0]==self.pks[1])
        self.bft_from_server = bft_from_server
        self.bft_to_client = bft_to_client
        # self.bft_from_app=bft_from_app
        self.ready = ready
        self.stop = stop
        self.debug = debug
        self.mempool = bft_from_app
        Fastconfirm.__init__(self, sid, pid, S, B, N, f, self.pks, self.sk, send=None, recv=None, recv_txs=None, K=3,
                             mute=False,
                             debug=False)


    def get_txs(self, size: int):
        txs_list = []
        for _ in range(size):
            txs_list.append(self.mempool)
        return txs_list

    def prepare_bootstrap(self):
        self.logger.info('node id %d is inserting dummy payload TXs' % (self.id))
        # print("node {} prepare".format(self.id))
        if self.debug == True:  # K * max(Bfast * S, Bacs)
            tx = self.get_txs(self.B * self.K)
            Fastconfirm.submit_tx(self, tx)
            # print("submit to buffer: ", tx[:-len(suffix)] + suffix)

    def run(self):
        # print("enter run")
        pid = os.getpid()
        self.logger.info('node %d\'s starts to run consensus on process id %d' % (self.id, pid))

        self._send = lambda j, o: self.bft_to_client((j, o))
        self._recv = lambda: self.bft_from_server()
        self._recv_txs = lambda: self.mempool()
        self.round_key_gen(1024)
        # print("node {} run".format(self.id))

        self.prepare_bootstrap()

        while not self.ready.value:
            print("self ready value wait")
            time.sleep(1)
            # gevent.sleep(1)

        self.run_fast()

        self.stop.value = True
