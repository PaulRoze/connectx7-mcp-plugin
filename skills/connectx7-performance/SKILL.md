---
name: connectx7-performance
description: "ConnectX-7 performance tuning and profiling. Use when optimizing latency, throughput, or debugging performance issues. Covers NUMA, IRQ affinity, ring buffers, PCIe settings, and profiling tools."
---

# ConnectX-7 Performance Tuning

## Performance Checklist

```
□ NUMA affinity configured (process on same node as NIC)
□ IRQ affinity set (interrupts on correct CPUs)
□ Huge pages enabled (2MB or 1GB)
□ memlock unlimited
□ Ring buffers maximized
□ MTU set to 9000 (jumbo frames)
□ PCIe settings optimized
□ Correct flow steering mode (dmfs vs smfs)
```

## NUMA Configuration (Critical)

```bash
# Find NIC NUMA node
cat /sys/class/net/eth0/device/numa_node

# Run app on same NUMA node
numactl --cpunodebind=0 --membind=0 ./your_app

# Verify NUMA topology
numactl --hardware
lstopo  # graphical
```

### In Code

```c
#define _GNU_SOURCE
#include <numa.h>
#include <sched.h>

void pin_to_nic_numa(const char *interface) {
    char path[256];
    snprintf(path, sizeof(path), "/sys/class/net/%s/device/numa_node", interface);

    FILE *f = fopen(path, "r");
    int numa_node = 0;
    fscanf(f, "%d", &numa_node);
    fclose(f);

    if (numa_node >= 0) {
        numa_run_on_node(numa_node);
        numa_set_preferred(numa_node);
    }
}
```

## IRQ Affinity

```bash
# Find NIC interrupts
grep eth0 /proc/interrupts
# or
cat /proc/interrupts | grep mlx5

# Set IRQ affinity manually
echo 2 > /proc/irq/123/smp_affinity  # CPU 1
echo 4 > /proc/irq/124/smp_affinity  # CPU 2

# Use MLNX script (recommended)
/usr/sbin/set_irq_affinity.sh eth0

# Or use irqbalance hints
service irqbalance stop
set_irq_affinity_bynode.sh 0 eth0  # NUMA node 0
```

## Ring Buffer Tuning

```bash
# View current settings
ethtool -g eth0

# Maximize ring buffers
ethtool -G eth0 rx 8192 tx 8192

# Verify
ethtool -g eth0
```

## Interrupt Coalescing

```bash
# View current
ethtool -c eth0

# For LATENCY (less coalescing)
ethtool -C eth0 rx-usecs 0 tx-usecs 0 rx-frames 1 tx-frames 1

# For THROUGHPUT (more coalescing)
ethtool -C eth0 rx-usecs 50 tx-usecs 50 adaptive-rx on
```

## MTU / Jumbo Frames

```bash
# Set MTU to 9000 (recommended for RDMA)
ip link set eth0 mtu 9000

# Verify
ip link show eth0

# For RoCE: ensure switch also supports jumbo frames
```

## Huge Pages

```bash
# Allocate huge pages
echo 4096 > /proc/sys/vm/nr_hugepages

# Verify
cat /proc/meminfo | grep Huge

# Persistent (add to /etc/sysctl.conf)
vm.nr_hugepages = 4096

# For 1GB pages (if supported)
echo 16 > /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages
```

## Memory Lock Limits

```bash
# /etc/security/limits.d/rdma.conf
* soft memlock unlimited
* hard memlock unlimited

# Verify (after re-login)
ulimit -l
```

## PCIe Optimization

```bash
# Check PCIe link
lspci -vvv -s $(lspci | grep Mellanox | awk '{print $1}') | grep -E "LnkCap|LnkSta"

# Expected for ConnectX-7:
# LnkCap: Speed 32GT/s, Width x16  (PCIe Gen5)
# LnkSta: Speed 32GT/s, Width x16

# If width is x8 instead of x16: check slot, reseat card

# Advanced PCIe settings
mlxconfig -d /dev/mst/mt4129_pciconf0 set ADVANCED_PCI_SETTINGS=1
mlxconfig -d /dev/mst/mt4129_pciconf0 set MAX_ACC_OUT_READ=44
# Reboot required
```

## Flow Steering Mode

```bash
# Check current mode
devlink dev param show pci/0000:08:00.0 name flow_steering_mode

# smfs is faster for high rule insertion rates
devlink dev param set pci/0000:08:00.0 name flow_steering_mode value smfs cmode runtime
```

## VMA-Specific Tuning

```bash
# Latency-optimized
export VMA_SPEC=latency
export VMA_RX_POLL=100000
export VMA_SELECT_POLL=100000
export VMA_THREAD_MODE=0
export VMA_RX_BUFS=200000
export VMA_TX_BUFS=200000
export VMA_MEM_ALLOC_TYPE=2  # Huge pages
export VMA_IGMP_ENABLE=1

# Run with VMA
LD_PRELOAD=/usr/lib64/libvma.so ./your_app
```

## Profiling Tools

### ethtool Statistics

```bash
# All statistics
ethtool -S eth0

# Key metrics to watch
ethtool -S eth0 | grep -E "rx_packets|tx_packets|rx_bytes|tx_bytes"
ethtool -S eth0 | grep -E "rx_dropped|tx_dropped|rx_errors|tx_errors"
ethtool -S eth0 | grep -E "rx_out_of_buffer"
```

### RDMA Counters

```bash
# Port counters
cat /sys/class/infiniband/mlx5_0/ports/1/counters/*

# Hardware counters
cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/*

# Using perfquery
perfquery -x  # Extended counters
```

### mlx5 Performance Counters

```bash
# PCIe counters
cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/pcie_*

# Congestion counters (RoCE)
cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/np_cnp_*
cat /sys/class/infiniband/mlx5_0/ports/1/hw_counters/rp_cnp_*
```

### VMA Statistics

```bash
# Enable VMA stats
export VMA_STATS_FILE=/tmp/vma_stats
export VMA_STATS_SHMEM_DIR=/tmp

# Run app
./your_app &

# View live stats
vma_stats -p $(pgrep your_app)
```

### perf for CPU Profiling

```bash
# Record CPU samples
perf record -g ./your_app

# Analyze
perf report

# Watch live
perf top -p $(pgrep your_app)
```

## Latency Benchmarks

```bash
# RDMA latency test
ib_write_lat -d mlx5_0

# With specific size
ib_write_lat -d mlx5_0 -s 64

# Expected ConnectX-7 latency: ~0.9 microseconds
```

## Throughput Benchmarks

```bash
# RDMA bandwidth test
ib_write_bw -d mlx5_0

# Bidirectional
ib_write_bw -d mlx5_0 -b

# Expected ConnectX-7: ~400 Gb/s (NDR InfiniBand)
```

## Quick Tuning Script

```bash
#!/bin/bash
# quick_tune.sh - Basic ConnectX-7 tuning

IFACE=${1:-eth0}
NUMA=$(cat /sys/class/net/$IFACE/device/numa_node)

echo "Tuning $IFACE (NUMA node $NUMA)"

# Ring buffers
ethtool -G $IFACE rx 8192 tx 8192 2>/dev/null

# MTU
ip link set $IFACE mtu 9000

# IRQ affinity
/usr/sbin/set_irq_affinity.sh $IFACE 2>/dev/null || echo "set_irq_affinity.sh not found"

# Huge pages
echo 4096 > /proc/sys/vm/nr_hugepages

echo "Done. Run your app with: numactl --cpunodebind=$NUMA --membind=$NUMA ./app"
```

## Official Resources

- [MLNX_OFED Performance Tuning](https://docs.nvidia.com/networking/display/MLNXOFEDv583070LTS/Performance+Tuning)
- [ConnectX-7 User Manual](https://docs.nvidia.com/networking/display/connectx7vpi)
