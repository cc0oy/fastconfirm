# nodes = '''
# i-0514052d11d988a14	52.6.177.83	172.31.26.242
# i-0bca0103982b9e1f7	3.250.24.116	172.31.42.154
# i-0e81614cacd2994fb	3.25.169.231	172.31.6.209
# i-01e6c9a53e340c30f	18.181.253.121	172.31.15.54
#
# '''
nodes='''
i-0eb91c489565f8395	52.211.82.10	172.31.8.209
i-0380b92e1c6bad320	54.75.90.76	172.31.0.121
i-0311fe189f8a60820	34.255.97.61	172.31.0.106
i-034fe4304007793d1	54.171.162.71	172.31.14.61

'''

num_regions = 16
N = 10

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
