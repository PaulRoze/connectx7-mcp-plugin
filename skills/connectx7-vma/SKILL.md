---
name: connectx7-vma
description: "VMA (Messaging Accelerator) kernel bypass API reference. Use when implementing VMA in code, loading libvma dynamically, or configuring VMA environment variables for high-performance networking."
---

# VMA Kernel Bypass API

## Loading VMA

```bash
# LD_PRELOAD method (testing)
LD_PRELOAD=/usr/lib64/libvma.so ./your_app

# Environment variables
VMA_SPEC=latency           # Optimize for latency
VMA_RX_POLL=100000         # Polling cycles before blocking
VMA_RX_BUFS=200000         # Receive buffers
VMA_MEM_ALLOC_TYPE=2       # Huge pages (0=anon, 1=contig, 2=huge)
VMA_IGMP_ENABLE=1          # Required for multicast
VMA_TRACELEVEL=3           # Debug (0-5)
```

## VMA API Structure

```c
typedef struct {
    vma_api_t *api;                    // VMA extended API
    int (*recvmmsg)(int, void*, int, int, void*);
    int (*recv)(int, void*, int, int);
    int (*recvfrom)(int, void*, int, int, struct sockaddr*, socklen_t*);
    int (*send)(int, void*, int, int);
    int (*sendto)(int, void*, int, int, struct sockaddr_in*, socklen_t);
    int (*socket)(int, int, int);
    int (*bind)(int, sockaddr*, int);
    int (*setsockopt)(int, int, int, void*, int);
    int (*close)(int);
    int (*epoll_create)(int);
    int (*epoll_ctl)(int, int, int, struct epoll_event*);
    int (*epoll_wait)(int, struct epoll_event*, int, int);
    bool SimulatedApi;  // true = fallback to standard sockets
} vma_t;
```

## Dynamic Loading Pattern

```c
#include <dlfcn.h>

int LoadVmaSharedLibrary(vma_t *pVma, bool use_simulation)
{
    void *VmaHandle = NULL;
    memset(pVma, 0, sizeof(*pVma));

    if (!use_simulation && DetectMellanoxDriver()) {
        VmaHandle = dlopen("/usr/lib64/libvma.so", RTLD_NOW | RTLD_GLOBAL);
    }

    if (!VmaHandle) {
        // Fallback to standard sockets
        *(void **)&pVma->socket = dlsym(RTLD_DEFAULT, "socket");
        *(void **)&pVma->bind = dlsym(RTLD_DEFAULT, "bind");
        *(void **)&pVma->recv = dlsym(RTLD_DEFAULT, "recv");
        // ... other functions
        pVma->SimulatedApi = true;
        return 0;
    }

    // Load VMA functions
    *(void **)&pVma->socket = dlsym(VmaHandle, "socket");
    *(void **)&pVma->bind = dlsym(VmaHandle, "bind");
    *(void **)&pVma->recv = dlsym(VmaHandle, "recv");
    // ... other functions

    // Get VMA extended API
    socklen_t len = sizeof(pVma->api);
    pVma->getsockopt(-1, SOL_SOCKET, SO_VMA_GET_API, &pVma->api, &len);

    pVma->SimulatedApi = false;
    return 0;
}
```

## Detecting Mellanox Driver

```c
int DetectMellanoxDriver(void)
{
    struct if_nameindex *iface_list = if_nameindex();
    int sock = socket(AF_INET, SOCK_DGRAM, 0);

    for (struct if_nameindex *iface = iface_list; iface->if_name; iface++) {
        struct ethtool_drvinfo drvinfo = {.cmd = ETHTOOL_GDRVINFO};
        struct ifreq ifr = {0};
        strncpy(ifr.ifr_name, iface->if_name, IFNAMSIZ - 1);
        ifr.ifr_data = (void*)&drvinfo;

        if (ioctl(sock, SIOCETHTOOL, &ifr) == 0) {
            if (strncmp(drvinfo.driver, "mlx5", 4) == 0) {
                close(sock);
                if_freenameindex(iface_list);
                return 1;  // Found
            }
        }
    }
    close(sock);
    if_freenameindex(iface_list);
    return 0;  // Not found
}
```

## Multicast Join with VMA

```c
int JoinMulticast(vma_t *vma, const char *mcast_ip, uint16_t port, const char *iface)
{
    int fd = vma->socket(AF_INET, SOCK_DGRAM, 0);

    int reuse = 1;
    vma->setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port = htons(port),
        .sin_addr.s_addr = htonl(INADDR_ANY)
    };
    vma->bind(fd, (struct sockaddr*)&addr, sizeof(addr));

    struct ip_mreqn mreq = {
        .imr_multiaddr.s_addr = inet_addr(mcast_ip),
        .imr_ifindex = if_nametoindex(iface)
    };
    vma->setsockopt(fd, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof(mreq));

    return fd;
}
```

## High-Performance Receive Loop

```c
#define BATCH_SIZE 64

void ReceiveLoop(vma_t *vma, int fd, volatile bool *running)
{
    struct mmsghdr msgs[BATCH_SIZE];
    struct iovec iovecs[BATCH_SIZE];
    uint8_t buffers[BATCH_SIZE][1500];

    for (int i = 0; i < BATCH_SIZE; i++) {
        iovecs[i].iov_base = buffers[i];
        iovecs[i].iov_len = 1500;
        msgs[i].msg_hdr.msg_iov = &iovecs[i];
        msgs[i].msg_hdr.msg_iovlen = 1;
    }

    while (*running) {
        int n = vma->recvmmsg(fd, msgs, BATCH_SIZE, MSG_DONTWAIT, NULL);
        if (n > 0) {
            for (int i = 0; i < n; i++) {
                ProcessPacket(buffers[i], msgs[i].msg_len);
            }
        }
    }
}
```

## VMA Extended API

```c
// Get extended API after creating socket
vma_api_t *api;
socklen_t len = sizeof(api);
getsockopt(-1, SOL_SOCKET, SO_VMA_GET_API, &api, &len);

// Zero-copy receive
api->recvfrom_zcopy(fd, buf, len, flags, from, fromlen);
api->free_packets(fd, pkts, count);
```
