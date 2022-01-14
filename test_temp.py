N=4
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
except:
    print("read error")
print("test1")