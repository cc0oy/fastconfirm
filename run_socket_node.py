from gevent import monkey;

# from myexperiements.sockettest.nwabcs_k_node import NwAbcskNode
# from myexperiements.sockettest.x_d_node import XDNode
# from myexperiements.sockettest.x_k_node import XDKNode
# from myexperiements.sockettest.x_k_s_node import XDSNode
from Client.make_random_tx import tx_generator
from fastconfirm.fc_node import FastConfirmNode
from network.gossip_client import GossipClient
from network.gossip_server import GossipServer

monkey.patch_all(thread=False)

import time
import random
import traceback
from typing import List, Callable
from gevent import Greenlet
# from myexperiements.sockettest.dumbo_node import DumboBFTNode
# from myexperiements.sockettest.sdumbo_node import SDumboBFTNode
# from myexperiements.sockettest.mule_node import MuleBFTNode
# from myexperiements.sockettest.rbcmule_node import RbcMuleBFTNode
# from myexperiements.sockettest.hotstuff_node import HotstuffBFTNode
# from myexperiements.sockettest.nwabc_node import NwAbcNode
# from myexperiements.sockettest.nwabcs_node import NwAbcsNode
# from myexperiements.sockettest.xdumbo_node import XDumboNode
from network.socket_server import NetworkServer
from network.socket_client import NetworkClient
from multiprocessing import Value as mpValue, Queue as mpQueue
from ctypes import c_bool


def instantiate_bft_node(sid, i, S, B, N, f, K, T, bft_from_server: Callable, bft_to_client: Callable,
                         bft_from_app: Callable, ready: mpValue,
                         stop: mpValue, protocol="mule", mute=False, F=100, debug=False, omitfast=False):
    bft = None
    # if protocol == 'dumbo':
    #     bft = DumboBFTNode(sid, i, B, N, f, bft_from_server, bft_to_client, ready, stop, K, mute=mute, debug=debug)
    # elif protocol == 'sdumbo':
    #     bft = SDumboBFTNode(sid, i, B, N, f, bft_from_server, bft_to_client,  ready, stop, K, mute=mute, debug=debug)
    # elif protocol == "mule":
    #     bft = MuleBFTNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, K, mute=mute, omitfast=omitfast)
    # elif protocol == "rbcmule":
    #     bft = RbcMuleBFTNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, K, mute=mute, omitfast=omitfast)
    # elif protocol == 'hotstuff':
    #     bft = HotstuffBFTNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, 1, mute=mute)
    # elif protocol == 'nwabc':
    #     bft = NwAbcNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, 1, mute=mute)
    # elif protocol == 'abcs':
    #     bft = NwAbcsNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, 1, mute=mute)
    # elif protocol == 'abcsk':
    #     bft = NwAbcskNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, K, mute=mute)
    # elif protocol == 'xdumbo':
    #     bft = XDumboNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, 1, mute=mute)
    # elif protocol == 'xd':
    #     bft = XDNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, 1, mute=mute)
    # elif protocol == 'xk':
    #     bft = XDKNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, K, mute=mute)
    # elif protocol == 'xs':
    #     bft = XDSNode(sid, i, S, T, B, F, N, f, bft_from_server, bft_to_client, ready, stop, K, mute=mute)
    if protocol == 'fc':
        bft = FastConfirmNode(sid, i, T, S, B, N, f, bft_from_server, bft_to_client, bft_from_app, ready, stop, K,
                              mute)
    else:
        print("Only support dumbo or sdumbo or mule or hotstuff")
    return bft


def network_config(filename, N, i):
    addresses = [None] * N
    try:
        with open(filename, 'r') as hosts:
            for line in hosts:
                params = line.split()
                pid = int(params[0])
                priv_ip = params[1]
                pub_ip = params[2]
                port = int(params[3])
                # print(pid, ip, port)
                if pid not in range(N):
                    continue
                if pid == i:
                    my_address = (priv_ip, port)
                addresses[pid] = (pub_ip, port)
        assert all([node is not None for node in addresses])
        print(filename + " is correctly read and " + str(N) + "node initialize")
    except FileNotFoundError or AssertionError as e:
        traceback.print_exc()
    # print("node {} addresses {}".format(i, addresses))
    print("my {} address {}".format(i, my_address))
    return addresses, my_address


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--sid', metavar='sid', required=True,
                        help='identifier of node', type=str)
    parser.add_argument('--id', metavar='id', required=True,
                        help='identifier of node', type=int)
    parser.add_argument('--N', metavar='N', required=True,
                        help='number of parties', type=int)
    parser.add_argument('--f', metavar='f', required=True,
                        help='number of faulties', type=int)
    parser.add_argument('--B', metavar='B', required=True,
                        help='size of batch', type=int)
    parser.add_argument('--K', metavar='K', required=True,
                        help='rounds to execute', type=int)
    parser.add_argument('--S', metavar='S', required=False,
                        help='slots to execute', type=int, default=50)
    parser.add_argument('--T', metavar='T', required=False,
                        help='fast path timeout', type=float, default=1)
    parser.add_argument('--P', metavar='P', required=False,
                        help='protocol to execute', type=str, default="mule")
    parser.add_argument('--M', metavar='M', required=False,
                        help='whether to mute a third of nodes', type=bool, default=False)
    parser.add_argument('--F', metavar='F', required=False,
                        help='batch size of fallback path', type=int, default=100)
    parser.add_argument('--D', metavar='D', required=False,
                        help='whether to debug mode', type=bool, default=True)
    parser.add_argument('--O', metavar='O', required=False,
                        help='whether to omit the fast path', type=bool, default=False)
    args = parser.parse_args()

    # Some parameters
    sid = args.sid
    i = args.id
    N = args.N
    f = args.f
    B = args.B
    K = args.K
    S = args.S
    T = args.T
    P = args.P
    M = args.M
    F = args.F
    D = args.D
    O = args.O


    start_point = time.time()
    # print("execute script at {}".format(start_point))
    # Random generator
    rnd = random.Random(sid)

    # Nodes list
    addresses_node, my_address_node = network_config('hosts.config', N, i)

    # port communicated with client
    # addresses_client, my_address_client = network_config('host_client.config', N,i)

    # bft_from_server, server_to_bft = mpPipe(duplex=True)
    # client_from_bft, bft_to_client = mpPipe(duplex=True)

    client_bft_mpq = mpQueue()
    # client_from_bft = client_bft_mpq.get
    client_from_bft = lambda: client_bft_mpq.get(timeout=0.00001)

    bft_to_client = client_bft_mpq.put_nowait

    server_bft_mpq = mpQueue()
    # bft_from_server = server_bft_mpq.get
    bft_from_server = lambda: server_bft_mpq.get(timeout=0.00001)
    server_to_bft = server_bft_mpq.put_nowait

    '''collect transactions with client'''
    server_app_mpq = mpQueue()
    bft_from_app = lambda: server_app_mpq.get(timeout=0.0001)
    bft_to_app = server_app_mpq.put_nowait
    '''put some transactions initilly'''
    # print("put txs 250 initially")
    for _ in range(4000):
        atx = tx_generator(250)
        server_app_mpq.put_nowait(atx)
    print("have put {} txs at time {}".format(server_app_mpq.qsize(), time.time()))

    client_ready = mpValue(c_bool, False)
    server_ready = mpValue(c_bool, False)
    net_ready = mpValue(c_bool, False)
    stop = mpValue(c_bool, False)

    # start_sync = [False] * N
    # print("see sync {}".format(start_sync))
    # TODO: communication channel to change in some way
    # net_listen = NetworkServer(my_address_client[1], my_address_client[0], i, addresses_client, bft_to_app,
    #                            server_ready, stop)

    start = time.time()
    # net_listen.start()
    # while time.time()-start<0.1:
    #     continue
    # print("start consensus node")
    net_server = NetworkServer(my_address_node[1], my_address_node[0], i, addresses_node, server_to_bft, server_ready,
                               stop)
    net_client = NetworkClient(my_address_node[1], my_address_node[0], i, addresses_node, client_from_bft, client_ready,
                               stop)
    # net_server = GossipServer(10,my_address_node[1], my_address_node[0], i, addresses_node, server_to_bft, bft_to_client,
    #                           server_ready,
    #                           stop)
    # net_client = GossipClient(10,my_address_node[1], my_address_node[0], i, addresses_node, client_from_bft, client_ready,
    #                           stop)
    bft = instantiate_bft_node(sid, i, S, B, N, f, K, T, bft_from_server, bft_to_client, bft_from_app, net_ready, stop,
                               P, M, F, D, O)
    net_server.start()
    net_client.start()

    while True:
        if not client_ready.value and not server_ready.value:
            time.sleep(0.001)
        else:
            print("self connect over at {}".format(time.time()))
            break
        # print("waiting for network ready with {} {}...".format(client_ready.value, server_ready.value))


    with net_ready.get_lock():
        net_ready.value = True

    while time.time() < 1650703727.572:
        time.sleep(0.0001)

    print("see the bft start time {}".format(time.time()))
    bft_thread = Greenlet(bft.run)
    bft_thread.start()
    bft_thread.join()

    with stop.get_lock():
        stop.value = True

    net_client.terminate()
    net_client.join()
    time.sleep(1)
    net_server.terminate()
    net_server.join()
