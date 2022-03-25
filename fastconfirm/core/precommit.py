import hashlib
import pickle

from fastconfirm.core.memselect import memselection
from fastconfirm.core.roundkey import sign


def hash(x):
    return hashlib.sha256(pickle.dumps(x)).digest()

def queue2list(fromq):
    num=fromq.qsize()
    tol=[]
    for i in range(num):
        element=fromq.get()
        tol.append(element)
        fromq.put_nowait(element)
    return tol




def precommit(pid, sid, N, PK2s, SK2, rpk, rsk, rmt, round, t, pi, h, c, pc_hB, voteset,send, logger=None):
    # lB means the block on the self.height

    def pre_broadcast(o):
        """SPBC send operation.
        :param o: Value to send.
        """
        # print("node", pid, "is sending", o[0], "to node", k, "with the leader", j)
        # print("send is:{}".format(send))
        for i in range(N):
            # print("precommit: send {} a message {} ".format(i,o))
            send(i, o)

    # print("--", pid, h, pi)
    if t == 1:
        # print(pid, "is select in commit!")
        votelist=[]
        if c > 0:
            position = ((round - 1) * 4) + 2
            votelist=queue2list(voteset)
            # votelist=str(voteset)
            sig = sign(rsk[position], str(pc_hB), rmt, position)
            msg = (1, h, pi, pc_hB,votelist, sig)
            print("precommits sends in round c>0 ", round)

        if c == 0:
            # not a valid C
            position = ((round - 1) * 4) + 2
            sig = sign(rsk[position], "null", rmt, position)
            msg = (0, h, pi, None, votelist,sig)
            print("precommits sends in round c=0 ", round)

        pre_broadcast(msg)
        # print("precommits sends in round", round)
        return 1
    else:
        # print(pid, "is not selected as a committee member")
        return 0
