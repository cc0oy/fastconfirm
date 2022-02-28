# nodes = '''
# i-0514052d11d988a14	52.6.177.83	172.31.26.242
# i-0bca0103982b9e1f7	3.250.24.116	172.31.42.154
# i-0e81614cacd2994fb	3.25.169.231	172.31.6.209
# i-01e6c9a53e340c30f	18.181.253.121	172.31.15.54
#
# '''
nodes='''
i-08593f726bb1ee509	34.254.198.78	172.31.36.1
i-0eb70a95d7940b0cb	52.209.55.162	172.31.33.183
i-0779a5589a591f3eb	52.48.68.69	172.31.36.13
i-019ad47fc40bb4f2f	34.245.91.110	172.31.45.159
'''

num_regions = 1
N = 4

n = int(N / num_regions)
r = N - num_regions * n

each_region_n = []
for i in range(num_regions):
    if r > 0:
        each_region_n.append(n + 1)
        r -= 1
    else:
        each_region_n.append(n)
print(each_region_n)

public_ips = []
private_ips = []

for line in nodes.splitlines():
    try:
        _, public, private = line.split()
        public_ips.append(public)
        private_ips.append(private)
    except:
        pass

print(len(public_ips))

print("# public IPs")
print("pubIPsVar=(", end='')
for i in range(len(public_ips) - 1):
    print("[%d]=\'%s\'" % (i, public_ips[i]))
i = len(public_ips) - 1
print("[%d]=\'%s\')" % (i, public_ips[i]))

print("# private IPs")
print("priIPsVar=(", end='')
for i in range(len(private_ips) - 1):
    print("[%d]=\'%s\'" % (i, private_ips[i]))
i = len(private_ips) - 1
print("[%d]=\'%s\')" % (i, private_ips[i]))
