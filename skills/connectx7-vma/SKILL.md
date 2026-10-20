---
name: connectx7-vma
description: "VMA (libvma) socket acceleration: LD_PRELOAD usage, VMA_* environment variables, the vma_extra.h extra API (zero-copy receive, socketxtreme). Use when running or coding against libvma. For new projects consider XLIO; for ST 2110 see connectx7-development (Rivermax)."
---

# VMA Kernel Bypass API

> Written against VMA 9.8.84 (libvma). For anything version-specific (env variables, vma_extra.h API, supported NICs), WebFetch the primary source before answering. Ask the user for `ofed_info -s`, `ethtool -i <if>`, `uname -r`.
> Docs: https://networking-docs.nvidia.com/vmaswum/9884 , https://github.com/Mellanox/libvma . Full list: ../connectx7-development/references/sources.md

Status: latest libvma release is 9.8.84 (2026-01, bug fixes only). NVIDIA's newer socket-acceleration library is XLIO (https://github.com/Mellanox/libxlio, 3.71.2 latest stable); both ship as DOCA-Host profiles.
For SMPTE ST 2110 use Rivermax (https://developer.nvidia.com/networking/rivermax), NVIDIA's ST 2110 SDK with hardware packet pacing.

## Loading VMA

```bash
# LD_PRELOAD method (testing)
LD_PRELOAD=/usr/lib64/libvma.so ./your_app

# Environment variables
VMA_SPEC=latency           # Optimize for latency
VMA_TRACELEVEL=debug       # Log level (default info)
```

## VMA API Structure

Example wrapper struct (yours, not libvma's). The real extra API is `struct vma_api_t` in `<mellanox/vma_extra.h>`.

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
    int (*getsockopt)(int sockfd, int level, int optname, void *optval, socklen_t *optlen);
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
        *(void **)&pVma->getsockopt = dlsym(RTLD_DEFAULT, "getsockopt");
        // ... other functions
        pVma->SimulatedApi = true;
        return 0;
    }

    // Load VMA functions
    *(void **)&pVma->socket = dlsym(VmaHandle, "socket");
    *(void **)&pVma->bind = dlsym(VmaHandle, "bind");
    *(void **)&pVma->recv = dlsym(VmaHandle, "recv");
    *(void **)&pVma->getsockopt = dlsym(VmaHandle, "getsockopt");
    // ... other functions

    // Get VMA extended API
    socklen_t len = sizeof(pVma->api);
    pVma->api = NULL;
    if (pVma->getsockopt(-1, SOL_SOCKET, SO_VMA_GET_API, &pVma->api, &len) < 0)
        pVma->api = NULL;  // not running under VMA: no extra API, check api before use

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
    struct mmsghdr msgs[BATCH_SIZE] = {0};
    struct iovec iovecs[BATCH_SIZE];
    uint8_t buffers[BATCH_SIZE][1500];  // each buffer must be >= MTU (use 9000 for jumbo frames)

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
vma_api_t *api = NULL;
socklen_t len = sizeof(api);
if (getsockopt(-1, SOL_SOCKET, SO_VMA_GET_API, &api, &len) < 0 || api == NULL)
    return;  // not running under VMA

// Zero-copy receive (flags is int *, in/out)
int flags = 0;
api->recvfrom_zcopy(fd, buf, len, &flags, from, fromlen);
api->free_packets(fd, pkts, count);
```
