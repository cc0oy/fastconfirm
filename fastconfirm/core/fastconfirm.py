from coincurve import PublicKey
from gevent import monkey;

# from check_keys import test_certain_key
from fastconfirm.core.blockproposal import blockproposal
from fastconfirm.core.commit import commit
from fastconfirm.core.memselect import memselection, vrifymember
from fastconfirm.core.precommit import precommit
from fastconfirm.core.roundkey import round_key_generation, sign, vrify, tx_generator
from fastconfirm.core.vote import vote

monkey.patch_all(thread=False)

import hashlib
import pickle
from crypto.ecdsa.ecdsa import ecdsa_vrfy

import json
import logging
import os
import traceback, time
import gevent
import numpy as np
from collections import namedtuple, defaultdict
from enum import Enum
from gevent import Greenlet
from gevent.queue import Queue
from honeybadgerbft.exceptions import UnknownTagError


def set_consensus_log(id: int):
    logger = logging.getLogger("consensus-node-" + str(id))
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(filename)s [line:%(lineno)d] %(funcName)s %(levelname)s %(message)s ')
    if 'log' not in os.listdir(os.getcwd()):
        os.mkdir(os.getcwd() + '/log')
    full_path = os.path.realpath(os.getcwd()) + '/log/' + "consensus-node-" + str(id) + ".log"
    file_handler = logging.FileHandler(full_path)
    file_handler.setFormatter(formatter)  # 可以通过setFormatter指定输出格式
    logger.addHandler(file_handler)
    return logger


def set_message_log(id: int):
    logger = logging.getLogger("consensusmsg-node-" + str(id))
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s %(filename)s [line:%(lineno)d] %(funcName)s %(levelname)s %(message)s ')
    if 'log' not in os.listdir(os.getcwd()):
        os.mkdir(os.getcwd() + '/log')
    full_path = os.path.realpath(os.getcwd()) + '/log/' + "consensusmsg-node-" + str(id) + ".log"
    file_handler = logging.FileHandler(full_path)
    file_handler.setFormatter(formatter)  # 可以通过setFormatter指定输出格式
    logger.addHandler(file_handler)
    return logger


def hash(x):
    return hashlib.sha256(pickle.dumps(x)).digest()


class BroadcastTag(Enum):
    F_BP = 'F_BP'
    F_VOTE = 'F_VOTE'
    F_PC = 'F_PC'
    F_COMMIT = 'F_COMMIT'


BroadcastReceiverQueues = namedtuple(
    'BroadcastReceiverQueues', ('F_BP', 'F_VOTE', 'F_PC', 'F_COMMIT'))


def broadcast_receiver_loop(recv_func, recv_queues):
    while True:
        sender, (tag, osender,msg) = recv_func()
        print("classify recv:", sender, tag)
        if tag not in BroadcastTag.__members__:
            # TODO Post python 3 port: Add exception chaining.
            # See https://www.python.org/dev/peps/pep-3134/
            raise UnknownTagError('Unknown tag: {}! Must be one of {}.'.format(
                tag, BroadcastTag.__members__.keys()))
        recv_queue = recv_queues._asdict()[tag]

        # if tag == BroadcastTag.X_NWABC.value:
        # recv_queue = recv_queue[r]
        try:
            recv_queue.put_nowait((sender, osender,msg))
            # print("receiver_loop:", sender, "->", pid, msg)
        except AttributeError as e:
            print("error", sender, (tag, osender,msg))
            traceback.print_exc(e)


class Fastconfirm:
    def __init__(self, sid, pid, T,S, B, N, f, sPK2s, sSK2, recv, send,recv_txs,K, mute=False,
                 debug=True):
        '''

        :param sid:
        :param pid:
        :param S:
        :param B:
        :param N:
        :param f:
        :param sPK2s: public key of every one
        :param sSK2: secert key of self
        :param send:
        :param recv:
        :param recv_txs:
        :param K:
        :param mute:
        :param debug:
        '''
        # print("enter fastconfirm.py init function")
        self._send_mode='broadcast'
        self.sid = sid
        self.id = pid
        self.SLOTS_NUM = S
        self.N = N
        self.f = f*0.4
        self.sPK2s = sPK2s
        self.sSK2 = sSK2
        self._send = send
        self._recv = recv
        self._recv_txs=recv_txs
        self.logger = set_consensus_log(pid)
        self.msglog=set_message_log(pid)
        self.transaction_buffer = Queue()
        # self.output_list = defaultdict(lambda: Queue())

        self.K = K
        self.T=T
        self.B=B
        self.debug = debug

        self.s_time = 0
        self.e_time = 0
        self.tx_cnt = 0
        self.txcnt = 0
        self.txdelay = 0

        self.mute = mute
        self.threads = []
        self.round = 1
        self._tobe_commit = Queue()
        self.state = (0, 0, 0)  # b, r, g
        self.lastcommit = 0
        self.height = 0
        self.lB = None
        self.hconfirm = hash(self.lB)
        # self.T = 1
        self.input = Queue(1)

        self.rpk = [] * 1024
        self.rsk = [] * 1024
        self.pk_root = 0
        self.rmt = None
        # self.step='F_BP'

        self._per_round_recv = {}
        self._per_bp={}
        self._per_vote = {}
        self._per_pc = {}
        self._per_commit = {}
        '''put 25 transactions initially'''
        for _ in range(4000):
            atx = tx_generator(25)
            self.transaction_buffer.put_nowait(atx)
        # print("have put {} txs".format(server_app_mpq.qsize()))


    def submit_tx(self,tx):
        self.transaction_buffer.append(tx)

    def takeout_tx(self):
        '''take transactions(s string) from transaction_buffer'''
        transaction_list = []
        for _ in range(self.B):
            atx = self.transaction_buffer.get()
            transaction_list.append(atx)
        return transaction_list

    # generate round keys
    def round_key_gen(self, key_num):
        self.rpk, self.rsk, self.rmt = round_key_generation(key_num)

    def fastconfirm_round(self):
        print("start consensus")
        # bp_recvs = Queue()
        # vote_recvs = Queue()
        # pc_recvs = Queue()
        # commit_recvs = Queue()

        # recv_queues = BroadcastReceiverQueues(
        #     F_BP=bp_recvs,
        #     F_VOTE=vote_recvs,
        #     F_PC=pc_recvs,
        #     F_COMMIT=commit_recvs
        # )
        # recv_loop_thred = Greenlet(broadcast_receiver_loop, self._per_round_recv[self.round].get, recv_queues)
        # recv_loop_thred.start()

        while self.input.empty() is not True:
            self.input.get()
        self.input.put("this is a tx batch in round " + str(self.round))

        def make_bp_send(original_sender,r):  # this make will automatically deep copy the enclosed send func
            def bp_send(k, o):
                """CBC send operation.
                :param k: Node to send.
                :param o: Value to send.
                """
                # print("node", self.id, "is sending", o[0], "to node", k, "with the round", r)
                if self._send_mode is 'gossip':
                    self._send(k, ('F_BP', original_sender,r, o))
                else:
                    self._send(k, ('F_BP',  r, o))
            return bp_send

        # generate round keys
        # rpk, rsk, rmt = round_key_generation(1024)

        # print("rsk check before entering proposal {}".format(len(self.rsk)))
        blockproposal(self.id, self.sid + 'BP', self.N, self.sPK2s, self.sSK2, self.rpk, self.rsk, self.rmt, self.round,
                      self.state, self.height, self.lB, self.hconfirm, self.takeout_tx,
                      make_bp_send(self.id,self.round))

        def make_vote_send(original_sender,r):  # this make will automatically deep copy the enclosed send func
            def vote_send(k, o):
                """CBC send operation.
                :param k: Node to send.
                :param o: Value to send.
                """
                # print("node", self.id, "is sending", o[0], "to node", k, "with the round", r)
                if self._send_mode is 'gossip':
                    self._send(k, ('F_VOTE', original_sender,r, o))
                else:
                    self._send(k, ('F_VOTE',r, o))

            return vote_send

        delta = self.T
        # self.step='F_BP'
        start = time.time()
        self.logger.info("enter recv block proposal phase at {}".format(start))
        t, my_pi, my_h = memselection(self.round, 2, self.sPK2s[self.id], self.sSK2)
        B=None
        block_dic = {}
        if t == 1:
            # wait for bp finish
            print("{} is selected in vote".format(self.id))
            (b, r, lg) = self.state
            maxh = 0
            leader = 0
            leader_msg = None
            while time.time() - start < delta:
                gevent.sleep(0.09)
            # self.step='F_VOTE'
            # print("bp size test",bp_recvs.qsize())
            # self.logger.info("node {} receive {} proposals".format(self.id, bp_recvs.qsize()))
            # while bp_recvs.qsize() > 0:
            print("node {} receive {} proposals".format(self.id, self._per_bp[self.round].qsize()))
            while self._per_bp[self.round].qsize()>0:
                gevent.sleep(0)
                # sender, osender,(g, h, pi, B, hB, height, sig) = bp_recvs.get()
                sender, osender, (g, h, pi, B, hB, height, sig) = self._per_bp[self.round].get()
                block_dic[hB] = (g, h, pi, B, hB, height, sig)
                # print(sender, " ",osender,(g, h, pi, B, hB, height, sig))
                if lg == 2 or (lg == 1 and self.lastcommit == 1):
                    if g == 0:
                        continue
                # self.logger.debug("maxh={},h={},test maxh < h:{}".format(maxh, int.from_bytes(h, 'big'),maxh < int.from_bytes(h, 'big')))
                if maxh < int.from_bytes(h, 'big'):
                    maxh = int.from_bytes(h, 'big')
                    leader = osender
                    # print(pid, "change:", leader)
                    leader_msg = (g, h, pi, B, hB, height, sig)
            self.logger.info("get the leader: {} chosen {} block is {}".format(leader, leader_msg[4],leader_msg))
            # print(self.id, "get the leader:", leader, "chosen block is:", leader_msg)
            vote(self.id, self.sid, self.N, self.sPK2s, self.sSK2, self.rpk, self.rsk, self.rmt,
                 self.round, t, my_pi, my_h, leader_msg, make_vote_send(self.id,self.round))
        else:
            print(self.id,"does not committee in vote")
            (b, r, lg) = self.state
            maxh = 0
            while time.time() - start < delta:
                gevent.sleep(0.09)
            # self.step = 'F_VOTE'
            # self.logger.info("node {} receive {} proposals".format(self.id, bp_recvs.qsize()))
            print("node {} receive {} proposals".format(self.id, self._per_bp[self.round].qsize()))
            # while bp_recvs.qsize()>0:
            #     sender, osender,(g, h, pi, B, hB, height, sig) = bp_recvs.get()
            while self._per_bp[self.round].qsize()>0:
                gevent.sleep(0)
                sender, osender, (g, h, pi, B, hB, height, sig) = self._per_bp[self.round].get()
                block_dic[hB]=(g, h, pi, B, hB, height, sig)
                if lg == 2 or (lg == 1 and self.lastcommit == 1):
                    if g == 0:
                        continue
                if maxh < int.from_bytes(h, 'big'):
                    maxh = int.from_bytes(h, 'big')
                    leader = osender
                    # print(pid, "change:", leader)
                    leader_msg = (g, h, pi, B, hB, height, sig)
                    # print(pid, "change:", leader)
            print("get the leader: {} chosen {} block is {}".format(leader, leader_msg[4], leader_msg))
            # print(self.id, "get the leader:", leader, "chosen block is:", leader_msg)

            vote(self.id, self.sid, self.N, self.sPK2s, self.sSK2, self.rpk, self.rsk, self.rmt,
                 self.round, t, my_pi, my_h, None, make_vote_send(self.id,self.round))

        def make_pc_send(original_sender,r):  # this make will automatically deep copy the enclosed send func
            def pc_send(k, o):
                """CBC send operation.
                :param k: Node to send.
                :param o: Value to send.
                """
                # print("node", self.id, " is sending ", o[0], " to node ", k, " with the round ", r)
                if self._send_mode is 'gossip':
                    self._send(k, ('F_PC',original_sender, r, o))
                else:
                    self._send(k, ('F_PC',r, o))

            return pc_send

        # wait for vote msg
        t, my_pi, my_h = memselection(self.round, 3, self.sPK2s[self.id], self.sSK2)
        start = time.time()
        self.logger.info("enter recv vote phase at {}".format(start))
        while time.time() - start < delta:
            gevent.sleep(0.09)
        # self.logger.info("node {} receive {} votes".format(self.id, vote_recvs.qsize()))
        print("node {} receive {} votes".format(self.id, self._per_vote[self.round].qsize()))
        # self.step='F_PC'

        vote_tag=0
        pc_hB = 0
        if t == 1:
            print("{} is selected in precommit".format(self.id))
            voteset = defaultdict(lambda: Queue())
            c = 0
            count = 0
            # while vote_recvs.qsize() > 0:
            while self._per_vote[self.round].qsize()>0:
                # print("node", self.id, "vote_recv queue size", vote_recvs.qsize(),"in round",self.round)
                gevent.sleep(0)
                # sender, osender,(g, h, pi, hB, height, sig) = vote_recvs.get()
                sender, osender, (g, h, pi, hB, height, sig) = self._per_vote[self.round].get()
                # test_certain_key(sender,"test",self.sPK2s[sender])
                # print("node",self.id,"recv from",sender,pi,h,str(self.sPK2s[sender]))
                # print("node {} verify vote member {} from {}".format(self.id,vrifymember(self.round, 2, h, pi, self.sPK2s[osender]),osender))
                if vrifymember(self.round, 2, h, pi, self.sPK2s[osender]):
                    (s, b) = sig
                    # assert vrify(s, b, hB, sPK2s[sender], rmt, ((round - 1) * 4) + 1, 1024)
                    voteset[hB].put(sig)
                    # print("round",self.round,"node",self.id,"votesize:",voteset[hB].qsize())
                    if voteset[hB].qsize() >= (2 * self.f + 1):
                        # print("node {} in round {} get {} votes with hB{}".format(self.id,self.round,voteset[hB].qsize(),hB))
                        pc_hB = hB
                        vote_tag=1
                        c = 1
            print("see vote list: {}".format(voteset.keys()))
            print("voteset length {}".format(len(voteset)))
            if c == 1:
                print("node {} in round {} get a valid vote set".format(self.id,self.round))
            else:
                print("node {} in round {} not valid vote set".format(self.id,self.round))
            precommit(self.id, self.sid, self.N, self.sPK2s, self.sSK2, self.rpk, self.rsk, self.rmt,
                      self.round, t, my_pi, my_h, c, pc_hB,voteset[pc_hB],
                      make_pc_send(self.id,self.round))
        else:
            voteset = defaultdict(lambda: Queue())
            c = 0
            count = 0
            # while vote_recvs.qsize() > 0:
            while self._per_vote[self.round].qsize() > 0:
                # print("node", self.id, "vote_recv queue size", vote_recvs.qsize(),"in round",self.round)
                gevent.sleep(0)
                # sender, osender,(g, h, pi, hB, height, sig) = vote_recvs.get()
                sender, osender, (g, h, pi, hB, height, sig) = self._per_vote[self.round].get()
                # test_certain_key(sender,"test",self.sPK2s[sender])
                # print("node",self.id,"recv from",sender,pi,h,str(self.sPK2s[sender]))
                # print("node {} verify vote member {} from {}".format(self.id,vrifymember(self.round, 2, h, pi, self.sPK2s[osender]),osender))
                if vrifymember(self.round, 2, h, pi, self.sPK2s[osender]):
                    (s, b) = sig
                    # assert vrify(s, b, hB, sPK2s[sender], rmt, ((round - 1) * 4) + 1, 1024)
                    voteset[hB].put(sig)
                    # print("round",self.round,"node",self.id,"votesize:",voteset[hB].qsize())
                    if voteset[hB].qsize() >= (2 * self.f + 1):
                        # print("node {} in round {} get {} votes with hB{}".format(self.id,self.round,voteset[hB].qsize(),hB))
                        pc_hB = hB
                        vote_tag = 1
                        c = 1
            print("see vote list: {}".format(voteset.keys()))
            print("voteset length {}".format(len(voteset)))
            if c == 1:
                print("node {} in round {} get a valid vote set".format(self.id, self.round))
            else:
                print("node {} in round {} not valid vote set".format(self.id, self.round))
            precommit(self.id, self.sid, self.N, self.sPK2s, self.sSK2, self.rpk, self.rsk, self.rmt,
                      self.round, t, my_pi, my_h, 0, None,None,
                      make_pc_send(self.id,self.round))

        # self.step = 'F_PC'

        def make_commit_send(original_sender,r):  # this make will automatically deep copy the enclosed send func
            def commit_send(k, o):
                """CBC send operation.
                :param k: Node to send.
                :param o: Value to send.
                """
                # print("node", pid, "is sending", o[0], "to node", k, "with the round", r)
                if self._send_mode is 'gossip':
                    self._send(k, ('F_COMMIT', original_sender,r, o))
                else:
                    self._send(k, ('F_COMMIT', r, o))

            return commit_send

        # wait for pre-commit finish
        preset = defaultdict(lambda: Queue())
        o = 0
        count = 0

        start = time.time()
        self.logger.info("enter recv precommit phase at {}".format(start))
        c_hB = 0
        c = 0
        while time.time() - start < delta:
            gevent.sleep(0.09)

        # self.step = 'F_COMMIT'

        # self.logger.info("node {} receive {} pc".format(self.id, pc_recvs.qsize()))
        print("node {} receive {} pc".format(self.id, self._per_pc[self.round].qsize()))
        # while pc_recvs.qsize() > 0:
        while self._per_pc[self.round].qsize()>0:
            gevent.sleep(0)
            # sender, osender,(g, h, pi, pc_hB, vote_set,sig) = pc_recvs.get()
            sender, osender, (g, h, pi, pc_hB, vote_set, sig) = self._per_pc[self.round].get()
            # print("node {} in round {} pc set verify vote_set len: {}".format(self.id,self.round,len(vote_set)))
            # print("node {} in round {} 3 verify member {} from {}".format(self.id,self.round,vrifymember(self.round, 3, h, pi, self.sPK2s[osender]),sender))
            if vrifymember(self.round, 3, h, pi, self.sPK2s[osender]) and len(vote_set)>=2*self.f+1:
                # self.logger.info("pc set: enter vrify member condition")
                (s, b) = sig
                # assert vrify(s, b, hB, sPK2s[sender], rmt, ((round - 1) * 4) + 1, 1024)
                preset[pc_hB].put((osender, h, pi, sig))
                if preset[pc_hB].qsize() >= (2 * self.f + 1):   #find a 2f+1 precommit set
                    # print("{} pc in round {} with pc_hB {}".format(preset[pc_hB].qsize(),self.round,pc_hB))
                    c_hB = pc_hB
                    o = 1
        print("pcset length {}".format(len(preset)))
        if o == 1:
            print("node {} in round {} get a valid omega set".format(self.id,self.round))
        else:
            print("node {} in round {} not a valid omega set".format(self.id,self.round))

        commit(self.id, self.sid, self.N, self.sPK2s, self.sSK2, self.rpk, self.rsk, self.rmt,
               self.round, o, preset[c_hB], c_hB, make_commit_send(self.id,self.round),self.logger)

        # wait for commit finish
        omegaset = defaultdict(lambda: Queue())
        pc = 0
        count = 0

        start = time.time()
        self.logger.info("enter recv commit phase at {}".format(start))
        g_hB = -1
        while time.time() - start < delta:
            try:
                gevent.sleep(0)
                sender,osender ,(o_j, h, pi, c_hB_j, omega_str, sig, rpk_j_byte, rmt_j) = self._per_commit[self.round].get_nowait()
                # sender, osender, (o_j, h, pi, c_hB_j, omega_str, sig, rpk_j_byte, rmt_j) = commit_recvs.get_nowait()
                # print("see sender {} and osender {}: {}".format(sender,osender,sender==osender))
                count += 1
            except:
                continue


            # print("node {} in round {} 4 verify member {} from {}".format(self.id,self.round,vrifymember(self.round, 4, h, pi, self.sPK2s[osender]),sender))
            if vrifymember(self.round, 4, h, pi, self.sPK2s[osender]):
                # self.logger.info("omega set: enter vrify member condition")
                (s, b) = sig
                rpk_j=PublicKey(rpk_j_byte)
                # self.logger.debug("see omega_str {} and {}".format(omega_str,str(c_hB_j)))
                if vrify(s, b, omega_str + str(c_hB_j), rpk_j, rmt_j, ((self.round - 1) * 4) + 3, 1024):
                    # self.logger.info("omega set: enter vrify condition {}".format(omega_str+"!!!!!"+str(c_hB_j)))

                    omegaset[c_hB_j].put((osender, h, pi, omega_str, sig))
                    if omegaset[c_hB_j].qsize() >= (2*self.f+1) :    #precommit set set
                        # print("PC set: g_hB=c_hB")
                        # print("{} commit in round {} with c_hB {}".format(omegaset[c_hB].qsize(), self.round,c_hB))
                        g_hB = c_hB_j
                        pc = 1

        print("node {} receive {} commit".format(self.id,count))
        print("commit set length {} and key is {}".format(len(omegaset),omegaset.keys()))
        if pc == 1:
            print("node {} get a valid PC set".format(self.id))
        else:
            # print("round {} node {}: dict size{}, omegaset[c_hb]{}".format(self.round,self.id, len(omegaset), omegaset[c_hB].qsize()))
            print("node {} not a valid PC set".format(self.id))

        # self.logger.info("{} judge c_hB=g_hB {}={}?".format(c_hB==g_hB,c_hB,g_hB))
        if c_hB == g_hB:
            self.state = (g_hB, self.round, 2)
        elif (c_hB != g_hB and pc == 1) or (o == 0 and pc == 1):
            self.state = (g_hB, self.round, 1)
        elif o == 0 and pc == 0:
            self.state = (c_hB, self.round, 0)
        # print(self.state)

        if self.round == 1:
            '''round1 block directly committed'''
            if vote_tag==1:
                self.logger.info("commit {} with {}".format(pc_hB,block_dic[pc_hB]))
                # print("output in round 1",B)
                self.lB=B
            else:
                self.logger.info("round does not collects enough votes")
        else:
            (h_s, round_s, g_s) = self.state
            print("round {} state info g_s={}".format(self.round,g_s))
            if g_s == 2:
                if hash(self.lB) == B[0]:
                    self.height += 1
                    # print("output in round ", self.round, B)
                    self.logger.info("commit: {} by hash(lB)=B".format(B))
                    # print("commit in round {}: {} by hash(lB)=B".format(self.round, B))
                    self.lastcommit = 1
                    self.lB = B
                else:
                    while self._tobe_commit.empty() is not True:
                        tB = self._tobe_commit.get()
                        self.height += 1
                        # print("output in round ", self.round, tB)
                        self.logger.info("commit: {} by to commit".format(tB))
                        # print("commit in round {}: {} by to commit".format(self.round, tB))
                    self.height += 1
                    # print("output in round ", self.round, B)
                    # print("commit in round {}: {} just =2".format(self.round, B))
                    self.logger.info("commit: {} just =2".format(B))
                    self.lastcommit = 1
                    self.lB = B
            else:
                # print("do not have commited block in round ", self.round)
                self.logger.info("do not have committed block in round {}".format(self.round))
                self.lastcommit = 0
                self._tobe_commit.put(B)
        self.round += 1

    def run_fast(self):
        def _recv_loop():
            """Receive messages."""
            #print("start recv loop...")
            while True:
                # gevent.sleep(0)
                # atx=self._recv_txs()
                # print("receive transaction".format(atx))
                # print(atx)
                # self.transaction_buffer.put_nowait(atx)
                try:
                    '''
                    if self._send_mode is 'gossip':
                        sender, (tag,osender, r, msg) = self._recv()
                        # self.msglog.info("(gossip) round {} recv {} origin sender {} from {} msg is {}".format(r, tag, osender, sender, msg))
                        # if tag is not self.step:
                        #     continue
                        if r not in self._per_round_recv:
                            self._per_round_recv[r] = Queue()
                        # Buffer this message
                        self._per_round_recv[r].put_nowait((sender, (tag, osender, msg)))
                    else:'''
                    sender, (tag, r, msg) = self._recv()
                    self.msglog.info("recv loop: sender {} {}".format(sender,tag))
                    # if tag is not self.step:
                    #     continue
                    # self.msglog.info("(broadcast)recv {} from {}".format(tag,sender))
                    # if r not in self._per_round_recv:
                    #     self._per_round_recv[r] = Queue()
                    #     # Buffer this message
                    # self._per_round_recv[r].put_nowait((sender, (tag, sender, msg)))
                    if tag == 'F_BP':
                        if r not in self._per_bp:
                            self._per_bp[r]=Queue()
                        self._per_bp[r].put_nowait((sender,sender,msg))
                    elif tag == 'F_VOTE':
                        if r not in self._per_vote:
                            self._per_vote[r]=Queue()
                        self._per_vote[r].put_nowait((sender,sender,msg))
                    elif tag == 'F_PC':
                        if r not in self._per_pc:
                            self._per_pc[r]=Queue()
                        self._per_pc[r].put_nowait((sender,sender,msg))
                    elif tag == 'F_COMMIT':
                        if r not in self._per_commit:
                            self._per_commit[r]=Queue()
                        self._per_commit[r].put_nowait((sender,sender,msg))
                    else:
                        print("tag error with value {}".format(tag))
                    # print('recv '+tag+str((sender, r, msg)))

                    # Maintain an *unbounded* recv queue for each epoch

                except:
                    # print("receive consensus message error")
                    continue
        self._recv_thread = Greenlet(_recv_loop)
        self._recv_thread.start()


        '''
        def _txs_loop():
            # receive transactions
            # print("node {} start to receive transactions".format(self.id))
            while True:
                # print("node {} enter receive transactions loop".format(self.id))
                try:

                    atx = self._recv_txs()
                    # print("node {} receive transaction {}".format(self.id,atx))
                    self.transaction_buffer.put_nowait(atx)
                    # print("now transaction buffer size {}".format(self.transaction_buffer.qsize()))
                except Exception as e:
                    # print(str(self.id)+":"+str((e,traceback.print_exc())))
                    # print("node {} receive txs message error".format(self.id))
                    continue

        self._recv_txs_thread=Greenlet(_txs_loop)
        self._recv_txs_thread.start()
        '''

        # print(self.id,"start consensus with txs:",self.transaction_buffer.qsize())
        while self.round <= self.SLOTS_NUM:
            self.logger.info("****************************\n{} start consensus round: {}".format(self.id,self.round))
            print("****************************\n{} start consensus round: {}".format(self.id, self.round))
            # print(self.id,str(self.sPK2s[0].format()),str(self.sPK2s[1].format()),str(self.sPK2s[2].format()),str(self.sPK2s[3].format()))
            if self.round not in self._per_round_recv:
                self._per_round_recv[self.round] = Queue()
                self._per_bp[self.round]=Queue()
                self._per_vote[self.round] = Queue()
                self._per_pc[self.round] = Queue()
                self._per_commit[self.round] = Queue()
            st = time.time()
            self.fastconfirm_round()
            print("finish round {} with in {} seconds".format(self.round - 1, time.time() - st))
            self.logger.info("finish a round with in {} seconds".format(time.time()-st))
            time.sleep(0.1)
        print("end normal")
        # self.logger.debug("---------------------------------------------")
