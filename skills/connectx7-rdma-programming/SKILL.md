---
name: connectx7-rdma-programming
description: "RDMA/InfiniBand Verbs programming with libibverbs. Use when writing RDMA code, implementing ibv_post_send/ibv_poll_cq, creating QPs, registering memory regions, or building high-performance networking applications."
---

# RDMA Verbs Programming Guide

## Core Concepts

```
┌──────────────────────────────────────────────────────────┐
│                    Application                           │
├──────────────────────────────────────────────────────────┤
│  libibverbs API (control path + data path)              │
├──────────────────────────────────────────────────────────┤
│  libmlx5 (provider library)                             │
├──────────────────────────────────────────────────────────┤
│  Kernel: mlx5_ib driver                                 │
├──────────────────────────────────────────────────────────┤
│  Hardware: ConnectX-7                                   │
└──────────────────────────────────────────────────────────┘

Control Path: Create/Destroy/Modify/Query (context switch)
Data Path:    Post Send/Recv, Poll CQ (NO context switch - user space only)
```

## Headers

```c
#include <infiniband/verbs.h>      // Core verbs API
#include <rdma/rdma_cma.h>         // Connection Manager API
#include <infiniband/mlx5dv.h>     // mlx5-specific extensions (optional)
```

## Basic Flow

```c
// 1. Get device list
struct ibv_device **dev_list = ibv_get_device_list(NULL);

// 2. Open device
struct ibv_context *ctx = ibv_open_device(dev_list[0]);

// 3. Allocate Protection Domain
struct ibv_pd *pd = ibv_alloc_pd(ctx);

// 4. Create Completion Queue
struct ibv_cq *cq = ibv_create_cq(ctx, cq_size, NULL, NULL, 0);

// 5. Register Memory Region
struct ibv_mr *mr = ibv_reg_mr(pd, buffer, size,
    IBV_ACCESS_LOCAL_WRITE |
    IBV_ACCESS_REMOTE_WRITE |
    IBV_ACCESS_REMOTE_READ);

// 6. Create Queue Pair
struct ibv_qp_init_attr qp_init = {
    .send_cq = cq,
    .recv_cq = cq,
    .qp_type = IBV_QPT_RC,  // Reliable Connected
    .cap = {
        .max_send_wr = 128,
        .max_recv_wr = 128,
        .max_send_sge = 1,
        .max_recv_sge = 1,
        .max_inline_data = 64
    }
};
struct ibv_qp *qp = ibv_create_qp(pd, &qp_init);

// 7. Transition QP: RESET -> INIT -> RTR -> RTS
// (see QP State Transitions below)

// 8. Post operations and poll completions
// (see Data Path Operations below)

// 9. Cleanup (reverse order)
ibv_destroy_qp(qp);
ibv_dereg_mr(mr);
ibv_destroy_cq(cq);
ibv_dealloc_pd(pd);
ibv_close_device(ctx);
ibv_free_device_list(dev_list);
```

## QP State Transitions

```c
// RESET -> INIT
struct ibv_qp_attr attr = {
    .qp_state = IBV_QPS_INIT,
    .pkey_index = 0,
    .port_num = 1,
    .qp_access_flags = IBV_ACCESS_REMOTE_WRITE | IBV_ACCESS_REMOTE_READ
};
ibv_modify_qp(qp, &attr,
    IBV_QP_STATE | IBV_QP_PKEY_INDEX | IBV_QP_PORT | IBV_QP_ACCESS_FLAGS);

// INIT -> RTR (Ready to Receive)
attr.qp_state = IBV_QPS_RTR;
attr.path_mtu = IBV_MTU_4096;
attr.dest_qp_num = remote_qpn;      // From remote side
attr.rq_psn = 0;
attr.max_dest_rd_atomic = 1;
attr.min_rnr_timer = 12;
attr.ah_attr.dlid = remote_lid;     // For IB
attr.ah_attr.sl = 0;
attr.ah_attr.port_num = 1;
// For RoCE: set ah_attr.grh fields instead
ibv_modify_qp(qp, &attr,
    IBV_QP_STATE | IBV_QP_PATH_MTU | IBV_QP_DEST_QPN |
    IBV_QP_RQ_PSN | IBV_QP_MAX_DEST_RD_ATOMIC |
    IBV_QP_MIN_RNR_TIMER | IBV_QP_AV);

// RTR -> RTS (Ready to Send)
attr.qp_state = IBV_QPS_RTS;
attr.sq_psn = 0;
attr.timeout = 14;
attr.retry_cnt = 7;
attr.rnr_retry = 7;
attr.max_rd_atomic = 1;
ibv_modify_qp(qp, &attr,
    IBV_QP_STATE | IBV_QP_SQ_PSN | IBV_QP_TIMEOUT |
    IBV_QP_RETRY_CNT | IBV_QP_RNR_RETRY | IBV_QP_MAX_QP_RD_ATOMIC);
```

## Data Path Operations

### Post Send (RDMA Write)

```c
struct ibv_sge sge = {
    .addr = (uint64_t)local_buffer,
    .length = data_size,
    .lkey = mr->lkey
};

struct ibv_send_wr wr = {
    .wr_id = unique_id,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_RDMA_WRITE,
    .send_flags = IBV_SEND_SIGNALED,  // Generate CQE
    .wr.rdma = {
        .remote_addr = remote_addr,   // From remote side
        .rkey = remote_rkey           // From remote side
    }
};

struct ibv_send_wr *bad_wr;
int ret = ibv_post_send(qp, &wr, &bad_wr);
if (ret) {
    fprintf(stderr, "ibv_post_send failed: %d\n", ret);
}
```

### Post Send (Send with Immediate)

```c
struct ibv_send_wr wr = {
    .wr_id = unique_id,
    .sg_list = &sge,
    .num_sge = 1,
    .opcode = IBV_WR_SEND_WITH_IMM,
    .send_flags = IBV_SEND_SIGNALED,
    .imm_data = htonl(my_immediate_data)  // 32-bit value
};
ibv_post_send(qp, &wr, &bad_wr);
```

### Post Receive

```c
struct ibv_sge sge = {
    .addr = (uint64_t)recv_buffer,
    .length = buffer_size,
    .lkey = mr->lkey
};

struct ibv_recv_wr wr = {
    .wr_id = unique_id,
    .sg_list = &sge,
    .num_sge = 1
};

struct ibv_recv_wr *bad_wr;
ibv_post_recv(qp, &wr, &bad_wr);
```

### Poll Completion Queue

```c
struct ibv_wc wc;

// Busy polling (lowest latency)
while (ibv_poll_cq(cq, 1, &wc) == 0) {
    // Spin
}

if (wc.status != IBV_WC_SUCCESS) {
    fprintf(stderr, "Work completion error: %s (%d)\n",
            ibv_wc_status_str(wc.status), wc.status);
}

// For receives, check:
// wc.byte_len    - Received data size
// wc.imm_data    - Immediate data (if IBV_WC_WITH_IMM)
// wc.wr_id       - Your identifier
```

### Batch Polling

```c
#define BATCH_SIZE 16
struct ibv_wc wc[BATCH_SIZE];

int n = ibv_poll_cq(cq, BATCH_SIZE, wc);
for (int i = 0; i < n; i++) {
    if (wc[i].status == IBV_WC_SUCCESS) {
        process_completion(&wc[i]);
    }
}
```

## Work Completion Status Codes

| Status | Meaning |
|--------|---------|
| `IBV_WC_SUCCESS` | Completed successfully |
| `IBV_WC_LOC_LEN_ERR` | Local length error |
| `IBV_WC_LOC_PROT_ERR` | Local protection error (MR issue) |
| `IBV_WC_WR_FLUSH_ERR` | QP in error state, WRs flushed |
| `IBV_WC_REM_ACCESS_ERR` | Remote access error (wrong rkey/permissions) |
| `IBV_WC_RNR_RETRY_EXC_ERR` | RNR retry exceeded (receiver not ready) |
| `IBV_WC_RETRY_EXC_ERR` | Transport retry exceeded (timeout) |

## Using RDMA-CM (Simplified Connection)

```c
#include <rdma/rdma_cma.h>

// Client side
struct rdma_event_channel *ec = rdma_create_event_channel();
struct rdma_cm_id *cm_id;
rdma_create_id(ec, &cm_id, NULL, RDMA_PS_TCP);

struct sockaddr_in addr = {
    .sin_family = AF_INET,
    .sin_port = htons(port),
    .sin_addr.s_addr = inet_addr(server_ip)
};
rdma_resolve_addr(cm_id, NULL, (struct sockaddr*)&addr, 2000);
// Wait for RDMA_CM_EVENT_ADDR_RESOLVED

rdma_resolve_route(cm_id, 2000);
// Wait for RDMA_CM_EVENT_ROUTE_RESOLVED

// Create QP using cm_id->verbs, cm_id->pd
struct ibv_qp_init_attr qp_attr = { /* ... */ };
rdma_create_qp(cm_id, pd, &qp_attr);

// Connect
struct rdma_conn_param conn_param = {
    .initiator_depth = 1,
    .responder_resources = 1,
    .retry_count = 7
};
rdma_connect(cm_id, &conn_param);
// Wait for RDMA_CM_EVENT_ESTABLISHED
```

## Compilation

```bash
# Install rdma-core
dnf install rdma-core-devel  # RHEL/Rocky
apt install libibverbs-dev librdmacm-dev  # Ubuntu

# Compile
gcc -o rdma_app rdma_app.c -libverbs -lrdmacm

# With mlx5-specific features
gcc -o rdma_app rdma_app.c -libverbs -lrdmacm -lmlx5
```

## Official Resources

- [NVIDIA RDMA Programming Guide](https://docs.nvidia.com/networking/display/RDMAAwareProgrammingv17/)
- [RDMAmojo Tutorial](https://www.rdmamojo.com/)
- [rdma-core GitHub](https://github.com/linux-rdma/rdma-core)
