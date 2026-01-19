---
name: connectx7-troubleshooting
description: "ConnectX-7 troubleshooting, error codes, and diagnostics. Use when debugging driver issues, firmware problems, link failures, performance issues, or VMA errors. Covers dmesg patterns, health monitoring, and common fixes."
---

# ConnectX-7 Troubleshooting Guide

## Quick Diagnostic Commands

```bash
# System info
ethtool -i eth0                    # Driver/firmware version
lspci | grep -i mellanox           # PCI device
mst start && mst status            # MST devices
mlxfwmanager --query               # Firmware details

# Link status
ibstat                             # IB port status
ethtool eth0                       # Ethernet link
ip link show eth0                  # Interface state

# Health check
devlink health show pci/0000:08:00.0
dmesg | grep -i "mlx5.*error\|mlx5.*fail"
```

## Error Code Reference

### Kernel (dmesg) Errors

| Pattern | Meaning | Fix |
|---------|---------|-----|
| `mlx5_core: firmware error` | Firmware crashed | Update FW, cold reboot |
| `mlx5_core: cmd timeout` | FW not responding | Check PCIe, power cycle |
| `mlx5_core: health error` | HW health failed | Run `devlink health diagnose` |
| `mlx5_core: out of resources` | HW resource exhausted | Reduce QPs/MRs/CQs |
| `mlx5_ib: CQ overrun` | CQ too small | Increase CQ size |
| `mlx5_core: command failed, status bad resource state` | Resource in wrong state | Check QP state transitions |
| `mlx5_core: exec cmd failed` | Generic command failure | Check dmesg for details |
| `mlx5_core: Port module event: Error` | Transceiver issue | Check cable/SFP |

### RDMA Work Completion Errors

| Status | Code | Meaning | Common Cause |
|--------|------|---------|--------------|
| `IBV_WC_LOC_LEN_ERR` | 1 | Local length error | SGE length mismatch |
| `IBV_WC_LOC_QP_OP_ERR` | 2 | Local QP operation error | Invalid opcode for QP type |
| `IBV_WC_LOC_PROT_ERR` | 4 | Local protection error | Wrong MR permissions/lkey |
| `IBV_WC_WR_FLUSH_ERR` | 5 | WR flushed | QP moved to error state |
| `IBV_WC_MW_BIND_ERR` | 6 | Memory window bind error | MW configuration issue |
| `IBV_WC_REM_ACCESS_ERR` | 10 | Remote access error | Wrong rkey or remote MR permissions |
| `IBV_WC_REM_INV_REQ_ERR` | 11 | Remote invalid request | Unsupported operation |
| `IBV_WC_REM_OP_ERR` | 12 | Remote operation error | Remote QP issue |
| `IBV_WC_RETRY_EXC_ERR` | 13 | Retry exceeded | Network timeout, path MTU |
| `IBV_WC_RNR_RETRY_EXC_ERR` | 14 | RNR retry exceeded | Receiver not ready (no recv posted) |
| `IBV_WC_RESP_TIMEOUT_ERR` | 17 | Response timeout | Remote not responding |

### VMA Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `VMA: No supported devices found` | mlx5 driver not loaded | Load `mlx5_core`, `mlx5_ib` |
| `VMA: Failed to allocate buffer pool` | memlock limit | Set unlimited in limits.conf |
| `VMA: Ring allocation failed` | Resources exhausted | Reduce `VMA_RX_BUFS` |
| `VMA: Cannot create socket` | Library not loaded | Check `LD_PRELOAD` path |
| `VMA: IGMP join failed` | Multicast issue | Set `VMA_IGMP_ENABLE=1` |

## Link Troubleshooting

### Physical State (ibstat)

```bash
ibstat
# Look for "Physical state" field
```

| State | Meaning | Action |
|-------|---------|--------|
| `LinkUp` | Good | - |
| `Polling` | Waiting for link partner | Check cable, switch port |
| `PortConfigurationTraining` | Speed negotiation | Check adapter/switch compatibility |
| `LinkErrorRecovery` | Link errors | Replace cable |
| `Disabled` | Port disabled | Enable port, check config |

### Ethernet Link (ethtool)

```bash
ethtool eth0
# Check "Link detected", "Speed", "Duplex"
```

| Issue | Check |
|-------|-------|
| No link | Cable, switch port, SFP |
| Wrong speed | Auto-negotiation, force speed settings |
| Link flapping | Cable quality, switch logs |

## Health Monitoring

```bash
# Check all health reporters
devlink health show pci/0000:08:00.0

# Diagnose specific reporter
devlink health diagnose pci/0000:08:00.0 reporter fw
devlink health diagnose pci/0000:08:00.0 reporter fw_fatal

# Dump health info (for NVIDIA support)
devlink health dump show pci/0000:08:00.0 reporter fw > health_dump.txt
```

### Health Reporter States

| Reporter | State | Action |
|----------|-------|--------|
| `fw` healthy | Good | - |
| `fw` error | FW issue | Check dmesg, update FW |
| `fw_fatal` error | Critical | Cold reboot, contact support |
| `vnic` error | VF issue | Check SR-IOV config |

## Firmware Troubleshooting

```bash
# Check version
mlxfwmanager --query

# Update
mlxfwmanager --update

# Manual update
mst start
flint -d /dev/mst/mt4129_pciconf0 -i firmware.bin burn

# ALWAYS reboot after firmware update
reboot
```

### Firmware Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Card not detected after update | Bad FW flash | Cold reboot (power off) |
| FW version mismatch | Partial update | Re-burn firmware |
| "PSID mismatch" error | Wrong FW image | Get correct image for your card |

## Performance Issues

### Check NUMA First

```bash
# NIC NUMA node
cat /sys/class/net/eth0/device/numa_node

# Process NUMA
numactl --show

# Fix: run on same NUMA node
numactl --cpunodebind=0 --membind=0 ./your_app
```

### Check PCIe Link

```bash
lspci -vvv -s $(lspci | grep Mellanox | awk '{print $1}') | grep -E "LnkCap|LnkSta"

# Should see:
# LnkCap: Speed 32GT/s, Width x16
# LnkSta: Speed 32GT/s, Width x16

# If Width is x8: reseat card, try different slot
```

### Check for Drops

```bash
ethtool -S eth0 | grep -E "drop|error|overflow"
cat /sys/class/infiniband/mlx5_0/ports/1/counters/port_rcv_errors
```

## VMA Troubleshooting

### Verify VMA is Loaded

```bash
# Check if VMA is intercepting
lsof -p $(pgrep your_app) | grep libvma

# Enable VMA debug
export VMA_TRACELEVEL=3
export VMA_LOG_FILE=/tmp/vma.log
LD_PRELOAD=/usr/lib64/libvma.so ./your_app

# Check log
cat /tmp/vma.log
```

### VMA Statistics

```bash
export VMA_STATS_FILE=/tmp/vma_stats
export VMA_STATS_SHMEM_DIR=/tmp
./your_app &

# View stats
vma_stats -p $(pgrep your_app)
```

## Collecting Debug Info for Support

```bash
#!/bin/bash
# collect_debug.sh

OUTPUT_DIR=/tmp/mlx5_debug_$(date +%Y%m%d_%H%M%S)
mkdir -p $OUTPUT_DIR

echo "Collecting debug info to $OUTPUT_DIR"

# System info
uname -a > $OUTPUT_DIR/uname.txt
cat /etc/os-release > $OUTPUT_DIR/os-release.txt

# Driver info
lspci -vvv | grep -A50 Mellanox > $OUTPUT_DIR/lspci.txt
ethtool -i eth0 > $OUTPUT_DIR/ethtool_i.txt
mlxfwmanager --query > $OUTPUT_DIR/firmware.txt 2>&1

# Status
ibstat > $OUTPUT_DIR/ibstat.txt 2>&1
ethtool eth0 > $OUTPUT_DIR/ethtool.txt
devlink health show > $OUTPUT_DIR/devlink_health.txt 2>&1

# Logs
dmesg | grep -i mlx5 > $OUTPUT_DIR/dmesg_mlx5.txt
journalctl -k | grep -i mlx5 > $OUTPUT_DIR/journal_mlx5.txt 2>&1

# Counters
ethtool -S eth0 > $OUTPUT_DIR/ethtool_stats.txt
cat /sys/class/infiniband/mlx5_0/ports/1/counters/* > $OUTPUT_DIR/ib_counters.txt 2>&1

# Config
mst start
mlxconfig -d /dev/mst/mt4129_pciconf0 query > $OUTPUT_DIR/mlxconfig.txt 2>&1
mstdump /dev/mst/mt4129_pciconf0 > $OUTPUT_DIR/mstdump.txt 2>&1

echo "Debug info collected in $OUTPUT_DIR"
tar -czvf ${OUTPUT_DIR}.tar.gz -C /tmp $(basename $OUTPUT_DIR)
echo "Archive: ${OUTPUT_DIR}.tar.gz"
```

## Official Resources

- [ConnectX-7 Troubleshooting](https://docs.nvidia.com/networking/display/connectx7vpi/troubleshooting)
- [NVIDIA Networking Forums](https://forums.developer.nvidia.com/c/networking/)
- [mlx5 Kernel Docs](https://www.kernel.org/doc/html/latest/networking/device_drivers/ethernet/mellanox/mlx5/)
