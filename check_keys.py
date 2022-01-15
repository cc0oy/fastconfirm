import os
import pickle

from coincurve import PrivateKey,PublicKey
from crypto.ecdsa import ecdsa

def load_key_pickle(id,N):
    pk=[]
    for i in range(N):
        with open(os.getcwd() + '/keys/' + 'sPK2-'+str(id)+'.key', 'rb') as fp:
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


def test_all_keys(N,msg):
    for i in range(N):
        sk,pks=load_key_pickle(i,N)
        sig=ecdsa.ecdsa_sign(sk,msg)
        if ecdsa.ecdsa_vrfy(pks[i],msg,sig):
            print("verify true")
        else:
            print("something wrong")


def test_certain_key(id,msg,pk,N=4):
    sk,_=load_key_pickle(id,N)
    sig=ecdsa.ecdsa_sign(sk,msg)
    if ecdsa.ecdsa_vrfy(pk,msg,sig):
        print("verify suecc")
    else:
        print("error")




if __name__=='__main__':
    test_keys(4,b'\x00')

