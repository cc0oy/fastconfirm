import os
import pickle

from coincurve import PublicKey, PrivateKey

from crypto.VRF import VRF_prove, VRF_verifying
from crypto.ecdsa import ecdsa
# from fastconfirm.fc_node import load_key_pickle




def memselection(r, s, pk, sk, k=4, T=0.8):
    threshold = pow(2, (k - 1) * 8)*(1 - T)
    pi, h = VRF_prove(pk, sk,str(r)+str(s), k)
    if int.from_bytes(h, 'big') > threshold:
        # print("selected!")
        return 1, pi, h
    else:
        return 0, pi, h

def vrifymember(r, s, h, pi, pk, k=4, T=0.8):
    threshold = pow(2, (k - 1) * 8) * (1 - T)
    if VRF_verifying(pk, pi, h, str(r)+str(s), k):
        if int.from_bytes(h, 'big') > threshold:
            return True
        else:
            print("verify member bytes to int compare error")
            return False
    else:
        print("VRF verify error")
        return False


def load_key_pickle(id,N,path):
    pk=[]
    for i in range(N):
        with open(path + '/keys-1000/' + 'sPK2-'+str(i)+'.key', 'rb') as fp:
            # sPK = pickle.load(fp)
            pk.append(PublicKey(pickle.load(fp)))

    with open(path + '/keys-1000/' + 'ePK.key', 'rb') as fp:
        ePK = pickle.load(fp)

    with open(path + '/keys-1000/' + 'sSK2-' + str(id) + '.key', 'rb') as fp:
        sSK = PrivateKey(pickle.load(fp))

    with open(path + '/keys-1000/' + 'eSK-' + str(id) + '.key', 'rb') as fp:
        eSK = pickle.load(fp)
    # print("node",id,"read keys",type(pk[0]),type(sSK))
    return sSK,pk


if __name__ == "__main__":
    vrflist =[(0, 0, 0)] * 100
    N=100
    # pk, sk = ecdsa.pki(100)
    count = 0
    sks=[]
    path='/home/cc/program/myexp/fastconfirm'
    for i in range(N):
        sk,pks=load_key_pickle(i,N,path)
        sks.append(sk)
        public_key=pks[i]
        (t, pi, h) = memselection(1, 1, public_key, sk)
        vrflist[i] = (t, pi, h)
    # for i in range(100):
    #     public_key = pk[i]
    #     private_key = sk[i]
    #     (t, pi, h) = memselection(1, 1, public_key, private_key)
    #     vrflist[i] = (t, pi, h)
    i=0
    for i in range(N):
        print(vrflist[i])
    i = 0
    for i in range(N):
        public_key = pks[i]
        (t, pi, h) = vrflist[i]
        print(vrifymember(1, 1, h, pi, public_key))
